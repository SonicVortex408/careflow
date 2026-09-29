import mongoose from "mongoose";

export const REPORT_STATUSES = [
    "processing",
    "pending_clinician_review",
    "approved",
    "rejected",
    "failed",
];

export const SYNTHETIC_DATA_LABEL =
    "Derived from synthetic data, for research/demo purposes, not clinical guidance.";

const auditSchema = new mongoose.Schema(
    {
        at: { type: Date, default: Date.now },
        actor: { type: mongoose.Schema.Types.ObjectId, default: null },
        actorRole: { type: String, default: "system" },
        action: { type: String, required: true },
        detail: { type: mongoose.Schema.Types.Mixed, default: null },
    },
    { _id: false }
);

const reviewSchema = new mongoose.Schema(
    {
        reviewer: { type: mongoose.Schema.Types.ObjectId, ref: "User" },
        reviewerName: String,
        decision: { type: String, enum: ["approve", "edit", "reject"] },
        comment: { type: String, maxlength: 4000 },
        editedSummary: { type: String, maxlength: 20000 },
        reviewedAt: Date,
    },
    { _id: false }
);

const reportSchema = new mongoose.Schema(
    {
        patient: {
            type: mongoose.Schema.Types.ObjectId,
            ref: "User",
            required: true,
            index: true,
        },

        originalName: { type: String, required: true, trim: true },
        storagePath: { type: String, required: true },
        mimeType: { type: String, required: true },
        size: { type: Number, required: true },

        status: {
            type: String,
            enum: REPORT_STATUSES,
            default: "processing",
            index: true,
        },

        jobId: { type: String, default: null },
        jobError: { type: String, default: null },

        // PROMs snapshot sent with the upload (from the latest symptom intake).
        proms: { type: mongoose.Schema.Types.Mixed, default: null },

        // Unified interpretation JSON from ai-service. Never shown to the
        // patient before a clinician approves it.
        interpretation: { type: mongoose.Schema.Types.Mixed, default: null },

        escalationLevel: {
            type: String,
            enum: ["routine", "priority", "urgent", "emergency"],
            default: "routine",
            index: true,
        },

        review: { type: reviewSchema, default: null },

        auditTrail: { type: [auditSchema], default: [] },

        syntheticDataLabel: { type: String, default: SYNTHETIC_DATA_LABEL },
    },
    {
        timestamps: true,
    }
);

reportSchema.methods.audit = function audit(action, { actor = null, actorRole = "system", detail = null } = {}) {
    this.auditTrail.push({ action, actor, actorRole, detail });
};

const Report = mongoose.model("Report", reportSchema);

export default Report;
