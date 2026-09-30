import fs from "fs/promises";

import Report from "../models/Report.js";
import SymptomEntry from "../models/SymptomEntry.js";
import { enqueueReport } from "../services/aiService.js";
import { serializeForPatient, syncPendingForPatient, syncReport } from "../services/reportService.js";

function ageOf(user) {
    return user.birthYear ? new Date().getFullYear() - user.birthYear : undefined;
}

// POST /api/reports  (patient) -> 202 {report_id, job_id}
export async function uploadReport(req, res) {
    if (!req.file) {
        return res.status(400).json({ success: false, message: "A lab report file is required (field 'file')" });
    }

    const latestSymptoms = await SymptomEntry.findOne({ patient: req.account._id }).sort({ createdAt: -1 });
    const proms = latestSymptoms ? latestSymptoms.toProms() : null;

    const report = new Report({
        patient: req.account._id,
        originalName: req.file.originalname.slice(0, 200),
        storagePath: req.file.path,
        mimeType: req.file.mimetype,
        size: req.file.size,
        status: "processing",
        proms,
    });
    report.audit("uploaded", { actor: req.account._id, actorRole: req.role, detail: { size: req.file.size } });
    await report.save();

    try {
        const job = await enqueueReport({
            filePath: req.file.path,
            mimeType: req.file.mimetype,
            originalName: req.file.originalname,
            reportId: report._id.toString(),
            patientId: req.account._id.toString(),
            proms,
            sex: req.account.sex || undefined,
            age: ageOf(req.account),
        });
        report.jobId = job.job_id;
        report.audit("enqueued", { detail: { jobId: job.job_id } });
        await report.save();
    } catch (error) {
        report.status = "failed";
        report.jobError = "Processing service unavailable";
        report.audit("enqueue_failed", { detail: { error: error.message } });
        await report.save();
        return res.status(502).json({ success: false, message: "Processing service unavailable, please try again", report_id: report._id });
    }

    return res.status(202).json({
        success: true,
        report_id: report._id,
        job_id: report.jobId,
        status: report.status,
    });
}

// GET /api/reports  (patient: own reports)
export async function listMyReports(req, res) {
    await syncPendingForPatient(req.account._id);
    const reports = await Report.find({ patient: req.account._id }).sort({ createdAt: -1 }).limit(100);
    res.json({ success: true, reports: reports.map(serializeForPatient) });
}

async function findOwnReport(req, res) {
    const report = await Report.findOne({ _id: req.params.id, patient: req.account._id });
    if (!report) {
        res.status(404).json({ success: false, message: "Report not found" });
        return null;
    }
    return report;
}

// GET /api/reports/:id/status  (polling)
export async function getReportStatus(req, res) {
    const report = await findOwnReport(req, res);
    if (!report) return;
    await syncReport(report);
    const { id, status, statusMessage, updatedAt } = serializeForPatient(report);
    res.json({ success: true, report: { id, status, statusMessage, updatedAt } });
}

// GET /api/reports/:id  (interpretation only once approved)
export async function getReport(req, res) {
    const report = await findOwnReport(req, res);
    if (!report) return;
    await syncReport(report);
    res.json({ success: true, report: serializeForPatient(report) });
}

// DELETE /api/reports/:id  (patient can withdraw a report)
export async function deleteReport(req, res) {
    const report = await findOwnReport(req, res);
    if (!report) return;
    await fs.rm(report.storagePath, { force: true });
    await report.deleteOne();
    res.json({ success: true });
}
