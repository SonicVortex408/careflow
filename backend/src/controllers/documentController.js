import Document from "../models/Document.js";
import { enqueueDocument, getJob } from "../services/aiService.js";
import { saveUpload } from "../services/storageService.js";

// POST /api/ai/documents  (patient) -> 202; the assistant can use the document once indexed.
export async function uploadDocument(req, res) {
    if (!req.file) {
        return res.status(400).json({ success: false, message: "A document file is required" });
    }

    const storagePath = await saveUpload({
        buffer: req.file.buffer,
        mimeType: req.file.mimetype,
        folder: "medical-documents",
        ownerId: req.account.id,
    });

    let document = await Document.create({
        userId: req.account.id,
        originalName: req.file.originalname.slice(0, 200),
        mimeType: req.file.mimetype,
        size: req.file.size,
        storagePath,
        status: "processing",
    });

    try {
        const job = await enqueueDocument({
            buffer: req.file.buffer,
            mimeType: req.file.mimetype,
            originalName: req.file.originalname,
            documentId: document.id,
            patientId: req.account.id,
        });
        document = await Document.update(document.id, { jobId: job.job_id });
    } catch (error) {
        await Document.update(document.id, { status: "failed" });
        return res.status(502).json({ success: false, message: "Unable to process document" });
    }

    return res.status(202).json({
        success: true,
        message: "Document received and queued for processing",
        document: {
            id: document.id,
            originalName: document.originalName,
            status: document.status,
            uploadedAt: document.createdAt,
        },
    });
}

// GET /api/ai/documents/:id/status
export async function getDocumentStatus(req, res) {
    let document = await Document.findOwn(req.params.id, req.account.id);

    if (!document) {
        return res.status(404).json({ success: false, message: "Document not found" });
    }

    if (document.status === "processing" && document.jobId) {
        try {
            const job = await getJob(document.jobId);
            const status = { completed: "ready", failed: "failed" }[job.status];
            if (status) document = await Document.update(document.id, { status });
        } catch {
            // keep "processing"; the client will poll again
        }
    }

    res.json({ success: true, document: { id: document.id, status: document.status, originalName: document.originalName } });
}
