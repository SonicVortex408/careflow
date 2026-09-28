import express from "express";

import protect from "../middleware/authMiddleware.js";

import {
    chatWithAI
} from "../controllers/aiController.js";

import upload from "../middleware/uploadMiddleware.js";

import {
    uploadDocument
} from "../controllers/documentController.js";

const router = express.Router();


router.post(
    "/documents",
    protect,
    upload.single("document"),
    uploadDocument
);

router.post(
    "/chat",
    protect,
    chatWithAI
);


export default router;