import multer from "multer";
import path from "path";
import fs from "fs";

const uploadDir = path.join(process.cwd(), "uploads", "medical-documents");

if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir, {
        recursive: true,
    });
}

const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, uploadDir);
    },

    filename: (req, file, cb) => {
        const extension = path.extname(file.originalname);

        const uniqueName =
            `${Date.now()}-${Math.round(Math.random() * 1e9)}${extension}`;

        cb(null, uniqueName);
    },
});

const fileFilter = (req, file, cb) => {
    const allowedTypes = [
        "application/pdf",
        "text/plain",
    ];

    if (allowedTypes.includes(file.mimetype)) {
        cb(null, true);
    } else {
        cb(
            new Error(
                "Only PDF and text files are allowed"
            ),
            false
        );
    }
};

const upload = multer({
    storage,

    fileFilter,

    limits: {
        fileSize: 10 * 1024 * 1024,
    },
});

export default upload;