import multer from "multer";

export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

const ALLOWED = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "image/png": ".png",
    "image/jpeg": ".jpg",
};

// Uploads are kept in memory (10 MB cap), forwarded to the ai-service and stored
// by storageService; the backend needs no persistent disk.
function makeUpload(allowedTypes) {
    const fileFilter = (req, file, cb) => {
        if (allowedTypes.includes(file.mimetype)) {
            cb(null, true);
        } else {
            const error = new Error(`Only ${allowedTypes.map((t) => ALLOWED[t]).join(", ")} files are allowed`);
            error.status = 415;
            cb(error, false);
        }
    };

    return multer({ storage: multer.memoryStorage(), fileFilter, limits: { fileSize: MAX_UPLOAD_BYTES } });
}

export const reportUpload = makeUpload(Object.keys(ALLOWED));
export const documentUpload = makeUpload(["application/pdf", "text/plain"]);

export default documentUpload;
