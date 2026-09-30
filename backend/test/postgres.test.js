import assert from "node:assert/strict";
import { after, before, describe, it } from "node:test";

import bcrypt from "bcryptjs";
import express from "express";
import request from "supertest";

import { setupEnv, teardown } from "./helpers.js";

const PDF = Buffer.from("%PDF-1.4\nTSH 5.8 mIU/L\n%%EOF");

/** Fake Supabase Storage: records bucket creation, uploads and deletes. */
function startFakeStorage() {
    const app = express();
    const state = { buckets: [], objects: new Map(), auth: [] };
    app.use((req, res, next) => {
        state.auth.push([req.headers.apikey, req.headers.authorization]);
        next();
    });
    app.post("/storage/v1/bucket", express.json(), (req, res) => {
        if (state.buckets.includes(req.body.id)) return res.status(400).json({ message: "The resource already exists" });
        state.buckets.push(req.body.id);
        res.json({ name: req.body.id });
    });
    app.post(/^\/storage\/v1\/object\/([^/]+)\/(.+)$/, express.raw({ type: "*/*", limit: "20mb" }), (req, res) => {
        state.objects.set(`${req.params[0]}/${req.params[1]}`, { type: req.headers["content-type"], size: req.body.length });
        res.json({ Key: req.params[1] });
    });
    app.delete("/storage/v1/object/:bucket", express.json(), (req, res) => {
        for (const prefix of req.body.prefixes) state.objects.delete(`${req.params.bucket}/${prefix}`);
        res.json([]);
    });
    return new Promise((resolve) => {
        const server = app.listen(0, () => resolve({ server, state, url: `http://127.0.0.1:${server.address().port}` }));
    });
}

let app;
let fake;
let storage;
let db;

async function signup(email) {
    const res = await request(app).post("/api/auth/register").send({ name: "Pat", email, password: "password123" });
    assert.equal(res.status, 201, res.text);
    return res.body;
}

async function clinicianToken(email) {
    const { default: User } = await import("../src/models/User.js");
    await User.create({ name: "Dr", email, password: await bcrypt.hash("password123", 10), role: "clinician" });
    return (await request(app).post("/api/auth/login").send({ email, password: "password123" })).body.token;
}

async function uploadAndWait(token) {
    const up = await request(app).post("/api/reports").set("Authorization", `Bearer ${token}`)
        .attach("file", PDF, { filename: "labs.pdf", contentType: "application/pdf" });
    assert.equal(up.status, 202, up.text);
    for (let i = 0; i < 10; i += 1) {
        const res = await request(app).get(`/api/reports/${up.body.report_id}/status`).set("Authorization", `Bearer ${token}`);
        if (res.body.report.status === "pending_clinician_review") return up.body.report_id;
    }
    throw new Error("report never became reviewable");
}

before(async () => {
    storage = await startFakeStorage();
    ({ app, fake } = await setupEnv({ supabaseUrl: storage.url }));
    db = await import("../src/config/db.js");
    const { ensureBucket } = await import("../src/services/storageService.js");
    assert.equal(await ensureBucket(), true);
    assert.equal(await ensureBucket(), false, "second call finds the existing bucket");
});

after(async () => {
    await teardown(fake);
    storage.server.close();
});

describe("Supabase Storage + Postgres", () => {
    it("stores uploads in the private bucket and removes them with the report", async () => {
        const patient = await signup("store@example.com");
        const up = await request(app).post("/api/reports").set("Authorization", `Bearer ${patient.token}`)
            .attach("file", PDF, { filename: "labs.pdf", contentType: "application/pdf" });
        assert.equal(up.status, 202, up.text);

        const keys = [...storage.state.objects.keys()];
        assert.equal(keys.length, 1);
        assert.match(keys[0], new RegExp(`^lab-reports/reports/${patient.user.id}/.+\\.pdf$`));
        assert.equal(storage.state.objects.get(keys[0]).size, PDF.length);
        assert.deepEqual(storage.state.auth.at(-1), ["test-service-key", "Bearer test-service-key"]);
        // The ai-service still receives the bytes directly.
        assert.equal(fake.state.enqueued.at(-1).size, PDF.length);

        const del = await request(app).delete(`/api/reports/${up.body.report_id}`).set("Authorization", `Bearer ${patient.token}`);
        assert.equal(del.status, 200);
        assert.equal(storage.state.objects.size, 0);
        const gone = await request(app).get(`/api/reports/${up.body.report_id}`).set("Authorization", `Bearer ${patient.token}`);
        assert.equal(gone.status, 404);
    });

    it("lets only one of two concurrent reviews win", async () => {
        const patient = await signup("race@example.com");
        const [a, b] = [await clinicianToken("ra@example.com"), await clinicianToken("rb@example.com")];
        const id = await uploadAndWait(patient.token);
        const results = await Promise.all([
            request(app).post(`/api/reviews/${id}`).set("Authorization", `Bearer ${a}`).send({ decision: "approve" }),
            request(app).post(`/api/reviews/${id}`).set("Authorization", `Bearer ${b}`).send({ decision: "reject", comment: "no" }),
        ]);
        assert.deepEqual(results.map((r) => r.status).sort(), [200, 409]);
        const { rows } = await db.query("SELECT status, audit_trail FROM reports WHERE id = $1", [id]);
        const reviews = rows[0].audit_trail.filter((e) => e.action.startsWith("review_"));
        assert.equal(reviews.length, 1, "exactly one review recorded");
    });

    it("applies the job-completion transition once under concurrent polling", async () => {
        const patient = await signup("poll@example.com");
        const up = await request(app).post("/api/reports").set("Authorization", `Bearer ${patient.token}`)
            .attach("file", PDF, { filename: "labs.pdf", contentType: "application/pdf" });
        const auth = { Authorization: `Bearer ${patient.token}` };
        await request(app).get(`/api/reports/${up.body.report_id}/status`).set(auth);
        await Promise.all([1, 2, 3].map(() => request(app).get(`/api/reports/${up.body.report_id}/status`).set(auth)));
        const { rows } = await db.query("SELECT status, audit_trail FROM reports WHERE id = $1", [up.body.report_id]);
        assert.equal(rows[0].status, "pending_clinician_review");
        assert.equal(rows[0].audit_trail.filter((e) => e.action === "interpretation_ready").length, 1);
    });

    it("returns messages with ids and rejects malformed ids as not found", async () => {
        const patient = await signup("chat@example.com");
        const auth = { Authorization: `Bearer ${patient.token}` };
        const conv = await request(app).post("/api/conversations").set(auth);
        await request(app).post("/api/ai/chat").set(auth).send({ message: "Hello there", conversationId: conv.body.conversation.id });
        const msgs = await request(app).get(`/api/conversations/${conv.body.conversation.id}/messages`).set(auth);
        assert.deepEqual(msgs.body.messages.map((m) => m.role), ["user", "assistant"]);
        assert.ok(msgs.body.messages.every((m) => /^[0-9a-f]{24}$/.test(m.id)));
        const list = await request(app).get("/api/conversations").set(auth);
        assert.equal(list.body.conversations[0].title, "Hello there");

        for (const bad of ["nope", "1' OR '1'='1", "0".repeat(24)]) {
            const res = await request(app).get(`/api/reports/${encodeURIComponent(bad)}`).set(auth);
            assert.equal(res.status, 404);
        }
    });

    it("never returns password hashes and keeps RLS on every table", async () => {
        const patient = await signup("hash@example.com");
        const me = await request(app).get("/api/users/profile").set("Authorization", `Bearer ${patient.token}`);
        assert.equal(me.status, 200, me.text);
        assert.equal(JSON.stringify(me.body).includes("password"), false);
        const patch = await request(app).patch("/api/users/profile").set("Authorization", `Bearer ${patient.token}`)
            .send({ sex: "M", birthYear: 1990 });
        assert.equal(patch.status, 200, patch.text);
        assert.deepEqual([patch.body.user.sex, patch.body.user.birthYear], ["M", 1990]);
        assert.equal(JSON.stringify(patch.body).includes("password"), false);

        const { rows } = await db.query(
            "SELECT relname FROM pg_class WHERE relkind = 'r' AND relnamespace = 'public'::regnamespace AND NOT relrowsecurity"
        );
        assert.deepEqual(rows, [], "tables without row level security");
    });
});
