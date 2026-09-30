import assert from "node:assert/strict";
import { after, before, describe, it } from "node:test";

import bcrypt from "bcryptjs";
import request from "supertest";

import { setupEnv, teardown } from "./helpers.js";

let app;
let fake;
let User;
let Admin;

const PDF = Buffer.from("%PDF-1.4\nTSH 5.8 mIU/L\n%%EOF");

async function signup(email, extra = {}) {
    const res = await request(app).post("/api/auth/register").send({ name: "Pat", email, password: "password123", ...extra });
    assert.equal(res.status, 201, res.text);
    return res.body;
}

async function makeClinician(email = "doc@example.com") {
    await User.create({ name: "Dr Who", email, password: await bcrypt.hash("password123", 10), role: "clinician" });
    const res = await request(app).post("/api/auth/login").send({ email, password: "password123" });
    return res.body.token;
}

async function pollUntil(token, id, status) {
    for (let i = 0; i < 10; i += 1) {
        const res = await request(app).get(`/api/reports/${id}/status`).set("Authorization", `Bearer ${token}`);
        if (res.body.report.status === status) return res.body.report;
    }
    throw new Error(`report never reached ${status}`);
}

before(async () => {
    ({ app, fake } = await setupEnv());
    ({ default: User } = await import("../src/models/User.js"));
    ({ default: Admin } = await import("../src/models/Admin.js"));
});

after(async () => {
    await teardown(fake);
});

describe("auth and roles", () => {
    it("registers patients only, ignoring a requested role", async () => {
        const body = await signup("p1@example.com", { role: "clinician", sex: "F", birthYear: 1985 });
        assert.equal(body.user.role, "patient");
        assert.equal(body.user.sex, "F");
    });

    it("has no public admin self-registration", async () => {
        const res = await request(app).post("/api/auth/admin/register").send({ name: "x", email: "a@x.io", password: "password123" });
        assert.equal(res.status, 404);
    });

    it("rejects bad credentials without leaking which part was wrong", async () => {
        const res = await request(app).post("/api/auth/login").send({ email: "p1@example.com", password: "nope" });
        assert.equal(res.status, 401);
        assert.equal(res.body.message, "Invalid credentials");
    });

    it("lets an admin create clinicians, and only an admin", async () => {
        await Admin.create({ name: "Root", email: "root@example.com", password: await bcrypt.hash("password123", 10) });
        const login = await request(app).post("/api/auth/admin/login").send({ email: "root@example.com", password: "password123" });
        const adminToken = login.body.token;
        const created = await request(app).post("/api/admin/clinicians").set("Authorization", `Bearer ${adminToken}`)
            .send({ name: "Dr A", email: "dra@example.com", password: "password123" });
        assert.equal(created.status, 201);
        assert.equal(created.body.clinician.role, "clinician");

        const patient = await signup("p2@example.com");
        const denied = await request(app).post("/api/admin/clinicians").set("Authorization", `Bearer ${patient.token}`)
            .send({ name: "x", email: "x@example.com", password: "password123" });
        assert.equal(denied.status, 403);
    });

    it("enforces role boundaries on reports and reviews", async () => {
        const patient = await signup("p3@example.com");
        const clinicianToken = await makeClinician("doc3@example.com");
        const r1 = await request(app).get("/api/reviews").set("Authorization", `Bearer ${patient.token}`);
        assert.equal(r1.status, 403);
        const r2 = await request(app).post("/api/reports").set("Authorization", `Bearer ${clinicianToken}`)
            .attach("file", PDF, { filename: "r.pdf", contentType: "application/pdf" });
        assert.equal(r2.status, 403);
        const r3 = await request(app).get("/api/reports");
        assert.equal(r3.status, 401);
    });
});

describe("upload -> clinician review -> patient view", () => {
    it("runs the full approval gate", async () => {
        const patient = await signup("flow@example.com", { sex: "F", birthYear: 1985 });
        const token = patient.token;
        const clinicianToken = await makeClinician("flowdoc@example.com");

        const symptoms = await request(app).post("/api/symptoms").set("Authorization", `Bearer ${token}`)
            .send({ fatigueSeverity: 8, brainFogFrequency: "often", hairLoss: "mild" });
        assert.equal(symptoms.status, 201);

        const upload = await request(app).post("/api/reports").set("Authorization", `Bearer ${token}`)
            .attach("file", PDF, { filename: "labs.pdf", contentType: "application/pdf" });
        assert.equal(upload.status, 202, upload.text);
        assert.ok(upload.body.report_id && upload.body.job_id);

        const sent = fake.state.enqueued.at(-1);
        assert.equal(sent.patient_id, patient.user.id);
        assert.deepEqual(JSON.parse(sent.proms), { fatigue_severity: 8, brain_fog_frequency: "often", hair_loss: "mild" });
        assert.equal(sent.sex, "F");
        assert.ok(fake.state.headers.includes("test-internal-key"));

        await pollUntil(token, upload.body.report_id, "pending_clinician_review");

        const beforeReview = await request(app).get(`/api/reports/${upload.body.report_id}`).set("Authorization", `Bearer ${token}`);
        assert.equal(beforeReview.body.report.interpretation, null, "interpretation must not be visible before sign-off");

        const queue = await request(app).get("/api/reviews").set("Authorization", `Bearer ${clinicianToken}`);
        const item = queue.body.reviews.find((r) => r.id === upload.body.report_id);
        assert.ok(item);
        assert.equal(item.markersFound, 2);

        const detail = await request(app).get(`/api/reviews/${item.id}`).set("Authorization", `Bearer ${clinicianToken}`);
        assert.equal(detail.body.report.interpretation.summary.text, "Generated summary.");

        const approve = await request(app).post(`/api/reviews/${item.id}`).set("Authorization", `Bearer ${clinicianToken}`)
            .send({ decision: "edit", comment: "Clarified wording", editedSummary: "Clinician-edited summary." });
        assert.equal(approve.status, 200);
        assert.equal(approve.body.report.status, "approved");
        const actions = approve.body.report.auditTrail.map((a) => a.action);
        for (const a of ["uploaded", "enqueued", "interpretation_ready", "viewed_by_reviewer", "review_edit"]) {
            assert.ok(actions.includes(a), `audit trail missing ${a}`);
        }

        const again = await request(app).post(`/api/reviews/${item.id}`).set("Authorization", `Bearer ${clinicianToken}`)
            .send({ decision: "approve" });
        assert.equal(again.status, 409);

        const after = await request(app).get(`/api/reports/${upload.body.report_id}`).set("Authorization", `Bearer ${token}`);
        const interp = after.body.report.interpretation;
        assert.equal(interp.summary.text, "Clinician-edited summary.");
        assert.equal(interp.summary.editedByClinician, true);
        assert.match(after.body.report.syntheticDataLabel, /synthetic data/);
        assert.equal(after.body.report.clinicianComment, "Clarified wording");

        // Chat now receives the approved results as context.
        const conv = await request(app).post("/api/conversations").set("Authorization", `Bearer ${token}`);
        const chat = await request(app).post("/api/ai/chat").set("Authorization", `Bearer ${token}`)
            .send({ message: "What does my ferritin mean?", conversationId: conv.body.conversation.id });
        assert.equal(chat.status, 200);
        assert.deepEqual(fake.state.chats.at(-1).patient_context.markers, { FERRITIN: 12, TSH: 5.8 });
    });

    it("sorts the queue by escalation and requires a comment to reject", async () => {
        const patient = await signup("esc@example.com");
        const clinicianToken = await makeClinician("escdoc@example.com");
        const ids = [];
        for (let i = 0; i < 4; i += 1) {
            const up = await request(app).post("/api/reports").set("Authorization", `Bearer ${patient.token}`)
                .attach("file", PDF, { filename: `r${i}.pdf`, contentType: "application/pdf" });
            ids.push(up.body.report_id);
            await pollUntil(patient.token, up.body.report_id, "pending_clinician_review");
        }
        const queue = await request(app).get("/api/reviews").set("Authorization", `Bearer ${clinicianToken}`);
        const levels = queue.body.reviews.map((r) => r.escalationLevel);
        const order = { emergency: 0, urgent: 1, priority: 2, routine: 3 };
        assert.deepEqual(levels, [...levels].sort((a, b) => order[a] - order[b]));

        const noComment = await request(app).post(`/api/reviews/${ids[0]}`).set("Authorization", `Bearer ${clinicianToken}`)
            .send({ decision: "reject" });
        assert.equal(noComment.status, 400);
        const rejected = await request(app).post(`/api/reviews/${ids[0]}`).set("Authorization", `Bearer ${clinicianToken}`)
            .send({ decision: "reject", comment: "Values unreadable; please repeat test." });
        assert.equal(rejected.body.report.status, "rejected");
        const view = await request(app).get(`/api/reports/${ids[0]}`).set("Authorization", `Bearer ${patient.token}`);
        assert.equal(view.body.report.interpretation, null);
    });

    it("keeps reports private to their patient", async () => {
        const a = await signup("owner@example.com");
        const b = await signup("intruder@example.com");
        const up = await request(app).post("/api/reports").set("Authorization", `Bearer ${a.token}`)
            .attach("file", PDF, { filename: "r.pdf", contentType: "application/pdf" });
        const res = await request(app).get(`/api/reports/${up.body.report_id}`).set("Authorization", `Bearer ${b.token}`);
        assert.equal(res.status, 404);
    });
});

describe("validation and errors", () => {
    it("validates uploads and symptom input", async () => {
        const p = await signup("val@example.com");
        const auth = { Authorization: `Bearer ${p.token}` };
        const bad = await request(app).post("/api/reports").set(auth)
            .attach("file", Buffer.from("MZ"), { filename: "x.exe", contentType: "application/x-msdownload" });
        assert.equal(bad.status, 415);
        const missing = await request(app).post("/api/reports").set(auth);
        assert.equal(missing.status, 400);
        const sym = await request(app).post("/api/symptoms").set(auth).send({ fatigueSeverity: 11, brainFogFrequency: "often", hairLoss: "mild" });
        assert.equal(sym.status, 400);
    });

    it("returns JSON errors for unknown routes and malformed JSON", async () => {
        const nf = await request(app).get("/api/nope");
        assert.equal(nf.status, 404);
        assert.equal(nf.body.success, false);
        const bad = await request(app).post("/api/auth/login").set("Content-Type", "application/json").send("{bad");
        assert.equal(bad.status, 400);
    });

    it("proxies cohort insights to signed-in users", async () => {
        const p = await signup("ins@example.com");
        const res = await request(app).get("/api/insights/cohort").set("Authorization", `Bearer ${p.token}`);
        assert.equal(res.status, 200);
        assert.equal(res.body.data.name, "cohort");
        const unknown = await request(app).get("/api/insights/secrets").set("Authorization", `Bearer ${p.token}`);
        assert.equal(unknown.status, 404);
    });
});
