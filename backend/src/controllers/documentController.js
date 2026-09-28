import fs from "fs";
import Document from "../models/Document.js";
import env from "../config/env.js";

const AI_SERVICE_URL = env.aiServiceUrl;

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
            status: "processing",
        });

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

        const aiResponse = await fetch(
            `${AI_SERVICE_URL}/api/documents/process`,
            {
                method: "POST",
                body: formData,
            }
        );

        if (!aiResponse.ok) {
            const errorText = await aiResponse.text();

            throw new Error(
                `AI document processing failed: ${aiResponse.status} ${errorText}`
            );
        }

        const result = await aiResponse.json();

        if (!result.success) {
            throw new Error(
                result.message ||
                "AI document processing failed"
            );
        }

        document.status = "ready";
        await document.save();

        return res.status(201).json({
            success: true,
            message: "Document uploaded and processed successfully",
            document: {
                id: document._id,
                originalName: document.originalName,
                mimeType: document.mimeType,
                size: document.size,
                status: document.status,
                uploadedAt: document.createdAt,
            },
            processing: result,
        });

    } catch (error) {
        console.error(
            "Document upload/processing error:",
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