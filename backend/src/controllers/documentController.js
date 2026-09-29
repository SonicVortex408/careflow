import fs from "fs";
import Document from "../models/Document.js";
import env from "../config/env.js";

const AI_SERVICE_URL = env.aiServiceUrl;

// Maps a Celery job state (app/api/ocr.py's GET /api/ocr/jobs/:id) to
// this project's Document.status enum. Exported for
// tests/documentController.test.js -- kept as a pure function
// specifically so it's testable without a database or HTTP layer.
export function mapJobStateToStatus(jobState) {
    if (jobState === "SUCCESS") return "ready";
    if (jobState === "FAILURE") return "failed";
    if (jobState === "STARTED") return "ocr_running";
    return "queued"; // PENDING, RETRY, or anything else -- still in flight
}

export async function uploadDocument(req, res) {
    let document = null;

    try {
        if (req.role !== "user") {
            return res.status(403).json({
                success: false,
                message: "Only patients can upload medical documents",
            });
        }

        if (!req.file) {
            return res.status(400).json({
                success: false,
                message: "A document file is required",
            });
        }

        document = await Document.create({
            user: req.account._id,
            originalName: req.file.originalname,
            filename: req.file.filename,
            mimeType: req.file.mimetype,
            size: req.file.size,
            storagePath: req.file.path,
            status: "queued",
        });

        // multer's 10 MB limit (uploadMiddleware.js) keeps a full
        // in-memory read bounded; true zero-copy streaming would need
        // the `form-data` package (not currently a dependency) to
        // stream a Node Readable into the multipart body instead of
        // buffering it into a Blob first. Left as a documented
        // possible follow-up rather than added now -- the change that
        // actually matters here is below: this request no longer
        // *waits* for OCR/normalization to finish (see the 202
        // response), which was the real "blocks the Express request"
        // problem, not this buffer.
        const fileBuffer = fs.readFileSync(req.file.path);

        const formData = new FormData();

        const blob = new Blob(
            [fileBuffer],
            {
                type: req.file.mimetype,
            }
        );

        formData.append(
            "file",
            blob,
            req.file.originalname
        );

        formData.append(
            "patient_id",
            req.account._id.toString()
        );

        formData.append(
            "document_id",
            document._id.toString()
        );

        // POST /api/ocr enqueues and returns 202 immediately -- this
        // fetch resolves as soon as the job is queued, not once OCR
        // and normalization have finished (that was the old
        // POST /api/documents/process contract, which held this
        // Express request open for the full processing time).
        const aiResponse = await fetch(
            `${AI_SERVICE_URL}/api/ocr/`,
            {
                method: "POST",
                body: formData,
            }
        );

        if (!aiResponse.ok) {
            const errorText = await aiResponse.text();

            throw new Error(
                `AI document enqueue failed: ${aiResponse.status} ${errorText}`
            );
        }

        const result = await aiResponse.json();

        if (!result.success) {
            throw new Error(
                result.message ||
                "AI document enqueue failed"
            );
        }

        document.jobId = result.job_id;
        await document.save();

        return res.status(202).json({
            success: true,
            message: "Document uploaded and queued for processing",
            document: {
                id: document._id,
                originalName: document.originalName,
                mimeType: document.mimeType,
                size: document.size,
                status: document.status,
                uploadedAt: document.createdAt,
            },
            jobId: result.job_id,
            statusUrl: `/api/ai/documents/${document._id}/status`,
        });

    } catch (error) {
        console.error(
            "Document upload/enqueue error:",
            error
        );

        if (document) {
            try {
                document.status = "failed";
                await document.save();
            } catch (dbError) {
                console.error(
                    "Failed to update document status:",
                    dbError
                );
            }
        }

        return res.status(500).json({
            success: false,
            message: "Unable to process document",
        });
    }
}

export async function getDocumentStatus(req, res) {
    try {
        const document = await Document.findOne({
            _id: req.params.id,
            user: req.account._id,
        });

        if (!document) {
            return res.status(404).json({
                success: false,
                message: "Document not found",
            });
        }

        if (!document.jobId || ["ready", "failed"].includes(document.status)) {
            // Already resolved (or never got a job -- e.g. a row
            // written before the Week 2 pipeline existed): nothing to
            // poll, return what's in Mongo.
            return res.json({
                success: true,
                document: {
                    id: document._id,
                    status: document.status,
                    originalName: document.originalName,
                },
            });
        }

        const jobResponse = await fetch(
            `${AI_SERVICE_URL}/api/ocr/jobs/${document.jobId}`
        );

        if (!jobResponse.ok) {
            return res.status(502).json({
                success: false,
                message: "Unable to reach ai-service for job status",
            });
        }

        const job = await jobResponse.json();
        const newStatus = mapJobStateToStatus(job.state);

        if (newStatus !== document.status) {
            document.status = newStatus;
            await document.save();
        }

        return res.json({
            success: true,
            document: {
                id: document._id,
                status: document.status,
                originalName: document.originalName,
            },
            job,
        });

    } catch (error) {
        console.error("Document status check error:", error);

        return res.status(500).json({
            success: false,
            message: "Unable to check document status",
        });
    }
}
