import Document from "../models/Document.js";
import { enqueueDocument, getJob } from "../services/aiService.js";

// POST /api/ai/documents  (patient) -> 202; the assistant can use the document once indexed.
export async function uploadDocument(req, res) {
    if (!req.file) {
        return res.status(400).json({ success: false, message: "A document file is required" });
    }

    const document = await Document.create({
        user: req.account._id,
        originalName: req.file.originalname.slice(0, 200),
        filename: req.file.filename,
        mimeType: req.file.mimetype,
        size: req.file.size,
        storagePath: req.file.path,
        status: "processing",
    });

    try {
        const job = await enqueueDocument({
            filePath: req.file.path,
            mimeType: req.file.mimetype,
            originalName: req.file.originalname,
            documentId: document._id.toString(),
            patientId: req.account._id.toString(),
        });
        document.jobId = job.job_id;
        await document.save();
    } catch (error) {
        document.status = "failed";
        await document.save();
        return res.status(502).json({ success: false, message: "Unable to process document" });
    }

    return res.status(202).json({
        success: true,
        message: "Document received and queued for processing",
        document: {
            id: document._id,
            originalName: document.originalName,
            status: document.status,
            uploadedAt: document.createdAt,
        },
    });
}

// GET /api/ai/documents/:id/status
export async function getDocumentStatus(req, res) {
    const document = await Document.findOne({ _id: req.params.id, user: req.account._id });

    if (!document) {
        return res.status(404).json({ success: false, message: "Document not found" });
    }

    if (document.status === "processing" && document.jobId) {
        try {
            const job = await getJob(document.jobId);
            if (job.status === "completed") document.status = "ready";
            if (job.status === "failed") document.status = "failed";
            await document.save();
        } catch {
            // keep "processing"; the client will poll again
        }
    }

    res.json({ success: true, document: { id: document._id, status: document.status, originalName: document.originalName } });
}
