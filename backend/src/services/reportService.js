import Report, { SYNTHETIC_DATA_LABEL, audit } from "../models/Report.js";
import { AIServiceError, getJob } from "./aiService.js";

/**
 * Pull the ai-service job state into the report row and return the current report.
 *
 * processing --job completed--> pending_clinician_review (interpretation stored,
 *                               NOT visible to the patient yet)
 * processing --job failed-----> failed
 *
 * Transitions are conditional on the row still being "processing", so
 * concurrent polls apply each one exactly once.
 */
export async function syncReport(report) {
    if (report.status !== "processing" || !report.jobId) {
        return report;
    }

    let job;
    try {
        job = await getJob(report.jobId);
    } catch (error) {
        if (error instanceof AIServiceError && error.upstreamStatus === 404) {
            report.status = "failed";
            report.jobError = "Processing job was lost; please upload again.";
            audit(report, "job_lost");
            return commit(report);
        }
        return report;
    }

    if (job.status === "completed") {
        const interpretation = job.result;
        report.interpretation = interpretation;
        report.status = "pending_clinician_review";
        report.escalationLevel = interpretation?.escalation?.level || "routine";
        audit(report, "interpretation_ready", {
            detail: {
                summarySource: interpretation?.summary?.source,
                readabilityGrade: interpretation?.summary?.readability_grade,
                guardrailsPassed: interpretation?.guardrails?.passed,
                escalation: report.escalationLevel,
                markers: (interpretation?.extraction?.biomarkers || []).length,
            },
        });
        return commit(report);
    }
    if (job.status === "failed") {
        report.status = "failed";
        report.jobError = job.error || "Processing failed";
        audit(report, "job_failed", { detail: { error: report.jobError } });
        return commit(report);
    }

    return report;
}

async function commit(report) {
    if (await Report.save(report, { expectStatus: "processing" })) return report;
    // Another request applied the transition first; return what it stored.
    return (await Report.findById(report.id)) || report;
}

export async function syncPendingForPatient(patientId) {
    const pending = await Report.listProcessing({ patientId });
    await Promise.all(pending.map((r) => syncReport(r)));
}

export async function syncAllProcessing(limit = 50) {
    const pending = await Report.listProcessing({ limit });
    await Promise.all(pending.map((r) => syncReport(r)));
}

const STATUS_MESSAGES = {
    processing: "Your report is being read. This usually takes under a minute.",
    pending_clinician_review: "Your results are ready and waiting for a clinician to review them.",
    approved: "A clinician has reviewed your results.",
    rejected: "A clinician reviewed this report and could not approve the automated summary. They will follow up with you.",
    failed: "We could not read this report. Please try another file or contact your clinic.",
};

function base(report) {
    return {
        id: report.id,
        originalName: report.originalName,
        status: report.status,
        statusMessage: STATUS_MESSAGES[report.status],
        uploadedAt: report.createdAt,
        updatedAt: report.updatedAt,
        syntheticDataLabel: report.syntheticDataLabel || SYNTHETIC_DATA_LABEL,
    };
}

/**
 * The patient sees an interpretation only after clinician approval. If the
 * clinician edited the summary, the edited text replaces the generated one.
 */
export function serializeForPatient(report) {
    const out = base(report);

    if (report.status !== "approved" || !report.interpretation) {
        return { ...out, interpretation: null };
    }

    const i = report.interpretation;
    const summaryText = report.review?.editedSummary || i.summary?.text;

    return {
        ...out,
        reviewedAt: report.review?.reviewedAt,
        clinicianComment: report.review?.comment || null,
        interpretation: {
            label: i.label,
            disclaimer: i.disclaimer,
            summary: { text: summaryText, editedByClinician: Boolean(report.review?.editedSummary) },
            biomarkers: i.extraction?.biomarkers || [],
            metadata: i.extraction?.metadata || {},
            analytics: i.analytics,
            evidence: i.evidence,
            escalation: i.escalation,
            appointmentGuide: i.appointment_guide || [],
            proms: i.proms,
        },
    };
}

export function serializeForClinician(report) {
    return {
        ...base(report),
        patient: report.patient,
        escalationLevel: report.escalationLevel,
        jobError: report.jobError,
        proms: report.proms,
        interpretation: report.interpretation,
        review: report.review,
        auditTrail: report.auditTrail,
    };
}

/** Latest approved results, handed to the assistant as patient context. */
export async function latestApprovedContext(patient) {
    const report = await Report.latestApproved(patient.id);

    if (!report?.interpretation) {
        return null;
    }

    const markers = {};
    for (const b of report.interpretation.extraction?.biomarkers || []) {
        markers[b.key] = b.value;
    }

    return {
        markers,
        proms: report.interpretation.proms || null,
        sex: patient.sex || report.interpretation.extraction?.metadata?.sex || null,
        age: patient.birthYear ? new Date().getFullYear() - patient.birthYear : report.interpretation.extraction?.metadata?.age || null,
    };
}
