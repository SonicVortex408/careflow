import crypto from "crypto";
import fs from "fs";
import multer from "multer";
import path from "path";

import env from "../config/env.js";

export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

const ALLOWED = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "image/png": ".png",
    "image/jpeg": ".jpg",
};

function makeUpload(subdir, allowedTypes) {
    const uploadDir = path.resolve(process.cwd(), env.uploadDir, subdir);

    fs.mkdirSync(uploadDir, { recursive: true });

    const storage = multer.diskStorage({
        destination: (req, file, cb) => cb(null, uploadDir),

        // Never reuse the client's filename on disk.
        filename: (req, file, cb) => cb(null, `${Date.now()}-${crypto.randomUUID()}${ALLOWED[file.mimetype]}`),
    });

    const fileFilter = (req, file, cb) => {
        if (allowedTypes.includes(file.mimetype)) {
            cb(null, true);
        } else {
            const error = new Error(`Only ${allowedTypes.map((t) => ALLOWED[t]).join(", ")} files are allowed`);
            error.status = 415;
            cb(error, false);
        }
    };

    return multer({ storage, fileFilter, limits: { fileSize: MAX_UPLOAD_BYTES } });
}

export const reportUpload = makeUpload("reports", Object.keys(ALLOWED));
export const documentUpload = makeUpload("medical-documents", ["application/pdf", "text/plain"]);

export default documentUpload;
