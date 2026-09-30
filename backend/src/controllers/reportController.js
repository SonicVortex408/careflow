import Report, { audit } from "../models/Report.js";
import SymptomEntry, { toProms } from "../models/SymptomEntry.js";
import { enqueueReport } from "../services/aiService.js";
import { serializeForPatient, syncPendingForPatient, syncReport } from "../services/reportService.js";
import { removeUpload, saveUpload } from "../services/storageService.js";

function ageOf(user) {
    return user.birthYear ? new Date().getFullYear() - user.birthYear : undefined;
}

// POST /api/reports  (patient) -> 202 {report_id, job_id}
export async function uploadReport(req, res) {
    if (!req.file) {
        return res.status(400).json({ success: false, message: "A lab report file is required (field 'file')" });
    }

    const latestSymptoms = await SymptomEntry.latestForPatient(req.account.id);
    const proms = latestSymptoms ? toProms(latestSymptoms) : null;

    const storagePath = await saveUpload({
        buffer: req.file.buffer,
        mimeType: req.file.mimetype,
        folder: "reports",
        ownerId: req.account.id,
    });

    const report = await Report.create({
        patientId: req.account.id,
        originalName: req.file.originalname.slice(0, 200),
        storagePath,
        mimeType: req.file.mimetype,
        size: req.file.size,
        proms,
        auditTrail: [],
    });
    audit(report, "uploaded", { actor: req.account.id, actorRole: req.role, detail: { size: req.file.size } });

    try {
        const job = await enqueueReport({
            buffer: req.file.buffer,
            mimeType: req.file.mimetype,
            originalName: req.file.originalname,
            reportId: report.id,
            patientId: req.account.id,
            proms,
            sex: req.account.sex || undefined,
            age: ageOf(req.account),
        });
        report.jobId = job.job_id;
        audit(report, "enqueued", { detail: { jobId: job.job_id } });
        await Report.save(report);
    } catch (error) {
        report.status = "failed";
        report.jobError = "Processing service unavailable";
        audit(report, "enqueue_failed", { detail: { error: error.message } });
        await Report.save(report);
        return res.status(502).json({ success: false, message: "Processing service unavailable, please try again", report_id: report.id });
    }

    return res.status(202).json({
        success: true,
        report_id: report.id,
        job_id: report.jobId,
        status: report.status,
    });
}

// GET /api/reports  (patient: own reports)
export async function listMyReports(req, res) {
    await syncPendingForPatient(req.account.id);
    const reports = await Report.listForPatient(req.account.id, 100);
    res.json({ success: true, reports: reports.map(serializeForPatient) });
}

async function findOwnReport(req, res) {
    const report = await Report.findOwn(req.params.id, req.account.id);
    if (!report) {
        res.status(404).json({ success: false, message: "Report not found" });
        return null;
    }
    return report;
}

// GET /api/reports/:id/status  (polling)
export async function getReportStatus(req, res) {
    let report = await findOwnReport(req, res);
    if (!report) return;
    report = await syncReport(report);
    const { id, status, statusMessage, updatedAt } = serializeForPatient(report);
    res.json({ success: true, report: { id, status, statusMessage, updatedAt } });
}

// GET /api/reports/:id  (interpretation only once approved)
export async function getReport(req, res) {
    let report = await findOwnReport(req, res);
    if (!report) return;
    report = await syncReport(report);
    res.json({ success: true, report: serializeForPatient(report) });
}

// DELETE /api/reports/:id  (patient can withdraw a report)
export async function deleteReport(req, res) {
    const report = await findOwnReport(req, res);
    if (!report) return;
    await Report.remove(report.id);
    try {
        await removeUpload(report.storagePath);
    } catch (error) {
        // The record is gone; an orphaned object is logged, not surfaced.
        console.error("Could not delete stored upload:", error.message);
    }
    res.json({ success: true });
}
