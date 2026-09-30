import Report from "../models/Report.js";
import { serializeForClinician, syncAllProcessing } from "../services/reportService.js";

const ESCALATION_ORDER = { emergency: 0, urgent: 1, priority: 2, routine: 3 };
const REVIEWABLE = ["pending_clinician_review", "approved", "rejected", "failed", "processing"];

// GET /api/reviews?status=pending_clinician_review  (clinician / admin)
export async function listReviews(req, res) {
    await syncAllProcessing();
    const status = REVIEWABLE.includes(req.query.status) ? req.query.status : "pending_clinician_review";
    const reports = await Report.find({ status })
        .populate("patient", "name email sex birthYear")
        .sort({ createdAt: 1 })
        .limit(200);

    const items = reports
        .map((r) => {
            const i = r.interpretation || {};
            return {
                id: r._id,
                status: r.status,
                patient: r.patient ? { id: r.patient._id, name: r.patient.name } : null,
                originalName: r.originalName,
                uploadedAt: r.createdAt,
                escalationLevel: r.escalationLevel,
                qualityNeedsAttention: Boolean(i.extraction?.quality?.needs_clinician_attention),
                markersFound: (i.extraction?.biomarkers || []).length,
                summarySource: i.summary?.source || null,
                reviewedAt: r.review?.reviewedAt || null,
            };
        })
        .sort((a, b) => ESCALATION_ORDER[a.escalationLevel] - ESCALATION_ORDER[b.escalationLevel]);

    res.json({ success: true, status, reviews: items });
}

// GET /api/reviews/:id
export async function getReview(req, res) {
    const report = await Report.findById(req.params.id).populate("patient", "name email sex birthYear");
    if (!report) {
        return res.status(404).json({ success: false, message: "Report not found" });
    }
    report.audit("viewed_by_reviewer", { actor: req.account._id, actorRole: req.role });
    await report.save();
    res.json({ success: true, report: serializeForClinician(report) });
}

// POST /api/reviews/:id  {decision: approve|edit|reject, comment, editedSummary}
export async function submitReview(req, res) {
    const { decision, comment = "", editedSummary } = req.body || {};

    if (!["approve", "edit", "reject"].includes(decision)) {
        return res.status(400).json({ success: false, message: "decision must be approve, edit or reject" });
    }
    if (decision === "edit" && !(editedSummary && String(editedSummary).trim())) {
        return res.status(400).json({ success: false, message: "editedSummary is required when decision is edit" });
    }
    if (decision === "reject" && !String(comment).trim()) {
        return res.status(400).json({ success: false, message: "A comment is required when rejecting" });
    }

    const report = await Report.findById(req.params.id);
    if (!report) {
        return res.status(404).json({ success: false, message: "Report not found" });
    }
    if (report.status !== "pending_clinician_review") {
        return res.status(409).json({ success: false, message: `Report is ${report.status}, not awaiting review` });
    }

    report.review = {
        reviewer: req.account._id,
        reviewerName: req.account.name,
        decision,
        comment: String(comment).slice(0, 4000),
        editedSummary: decision === "edit" ? String(editedSummary).slice(0, 20000) : undefined,
        reviewedAt: new Date(),
    };
    report.status = decision === "reject" ? "rejected" : "approved";
    report.audit(`review_${decision}`, {
        actor: req.account._id,
        actorRole: req.role,
        detail: { comment: report.review.comment || null, edited: decision === "edit" },
    });
    await report.save();

    res.json({ success: true, report: serializeForClinician(report) });
}
