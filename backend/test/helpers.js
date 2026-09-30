import express from "express";
import mongoose from "mongoose";
import multer from "multer";
import os from "os";
import path from "path";

/** Fake ai-service: records calls and answers like the real one. */
export function startFakeAI() {
    const app = express();
    const upload = multer({ storage: multer.memoryStorage() });
    const state = { enqueued: [], chats: [], jobs: new Map(), headers: [] };

    app.use(express.json());
    app.use((req, res, next) => {
        state.headers.push(req.headers["x-internal-key"] || null);
        next();
    });

    app.post("/api/ocr", upload.single("file"), (req, res) => {
        const jobId = `00000000-0000-0000-0000-${String(state.enqueued.length + 1).padStart(12, "0")}`;
        state.enqueued.push({ ...req.body, fileName: req.file?.originalname, size: req.file?.size });
        state.jobs.set(jobId, { polls: 0, reportId: req.body.report_id, level: req.body.report_id.endsWith("f") ? "urgent" : "routine" });
        res.status(202).json({ job_id: jobId, status: "queued" });
    });

    app.get("/api/ocr/jobs/:id", (req, res) => {
        const job = state.jobs.get(req.params.id);
        if (!job) return res.status(404).json({ detail: "Job not found" });
        job.polls += 1;
        if (job.polls < 2) return res.json({ job_id: req.params.id, status: "processing" });
        res.json({
            job_id: req.params.id,
            status: "completed",
            result: {
                label: "Derived from synthetic data, for research/demo purposes, not clinical guidance.",
                disclaimer: "This summary is for information only.",
                extraction: {
                    metadata: { sex: "F", age: 41 },
                    biomarkers: [
                        { key: "FERRITIN", value: 12, unit: "ug/L", display: "Ferritin" },
                        { key: "TSH", value: 5.8, unit: "mIU/L", display: "TSH" },
                    ],
                    quality: { needs_clinician_attention: false, issues: [] },
                },
                analytics: { models_available: true, bands: {}, cluster: null, risk: null },
                evidence: { chains: [] },
                summary: { text: "Generated summary.", source: "template", readability_grade: 6.1 },
                guardrails: { passed: true, audit: [] },
                escalation: { required: job.level !== "routine", level: job.level, reasons: [] },
                appointment_guide: ["Should my ferritin be re-tested?"],
                proms: { fatigue_severity: 8, brain_fog_frequency: "often", hair_loss: "mild" },
                review: { required: true, status: "pending_clinician_review" },
            },
        });
    });

    app.post("/api/chat/", (req, res) => {
        state.chats.push(req.body);
        res.json({ response: "Guarded answer.", escalation: { required: false, level: "routine", reasons: [] }, guardrails: { passed: true } });
    });

    app.get("/api/inference/:name", (req, res) => res.json({ label: "synthetic", name: req.params.name }));

    return new Promise((resolve) => {
        const server = app.listen(0, () => resolve({ server, state, url: `http://127.0.0.1:${server.address().port}` }));
    });
}

export async function setupEnv() {
    const fake = await startFakeAI();
    process.env.NODE_ENV = "test";
    process.env.AI_SERVICE_URL = fake.url;
    process.env.AI_INTERNAL_KEY = "test-internal-key";
    process.env.JWT_SECRET = "test-secret";
    process.env.UPLOAD_DIR = path.join(os.tmpdir(), `pm-uploads-${process.pid}`);
    process.env.AUTH_RATE_LIMIT = "1000";
    const uri = process.env.MONGO_URI_TEST || "mongodb://127.0.0.1:27017/polymarker_test";
    const dbName = `pm_test_${process.pid}_${Date.now()}`;
    await mongoose.connect(uri, { dbName });
    const { default: app } = await import("../src/app.js");
    return { app, fake };
}

export async function teardown(fake) {
    await mongoose.connection.dropDatabase();
    await mongoose.disconnect();
    fake.server.close();
}
