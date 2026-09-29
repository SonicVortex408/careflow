import mongoose from "mongoose";

const documentSchema = new mongoose.Schema(
    {
        user: {
            type: mongoose.Schema.Types.ObjectId,
            ref: "User",
            required: true,
            index: true,
        },

        originalName: {
            type: String,
            required: true,
            trim: true,
        },

        filename: {
            type: String,
            required: true,
        },

        mimeType: {
            type: String,
            required: true,
        },

        size: {
            type: Number,
            required: true,
        },

        storagePath: {
            type: String,
            required: true,
        },

        status: {
            type: String,
            enum: [
                "uploaded",
                // Legacy value from the old synchronous
                // /api/documents/process call. No longer written by
                // uploadDocument (which now writes "queued"), kept in
                // the enum so existing rows written before the Week 2
                // async pipeline landed remain valid.
                "processing",
                // Week 2 async pipeline states (backend/src/controllers/
                // documentController.js -> ai-service POST /api/ocr ->
                // Celery job, polled via GET /api/ocr/jobs/:jobId).
                "queued",
                "ocr_running",
                "extracted",
                "normalized",
                "ready",
                "failed",
            ],
            default: "uploaded",
        },

        // The ai-service Celery task id, set once POST /api/ocr enqueues
        // the job. getDocumentStatus polls
        // GET /api/ocr/jobs/:jobId with this.
        jobId: {
            type: String,
            default: null,
        },
    },
    {
        timestamps: true,
    }
);

const Document = mongoose.model(
    "Document",
    documentSchema
);

export default Document;