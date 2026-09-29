import multer from "multer";

import env from "../config/env.js";

export const notFound = (req, res) => {
    res.status(404).json({ success: false, message: `Not found: ${req.method} ${req.originalUrl}` });
};

// eslint-disable-next-line no-unused-vars
export const errorHandler = (err, req, res, next) => {
    let status = err.status || err.statusCode || 500;
    let message = err.expose || status < 500 ? err.message : "Internal server error";

    if (err instanceof multer.MulterError) {
        status = err.code === "LIMIT_FILE_SIZE" ? 413 : 400;
        message = err.code === "LIMIT_FILE_SIZE" ? "File is too large (max 10 MB)" : err.message;
    } else if (err.name === "CastError") {
        status = 404;
        message = "Resource not found";
    } else if (err.name === "ValidationError") {
        status = 400;
        message = err.message;
    } else if (err.type === "entity.parse.failed") {
        status = 400;
        message = "Malformed JSON body";
    }

    if (status >= 500 && env.nodeEnv !== "test") {
        console.error("Unhandled error:", err);
    }

    res.status(status).json({ success: false, message });
};
