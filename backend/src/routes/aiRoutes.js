import express from "express";

import protect from "../middleware/authMiddleware.js";
import requireRole from "../middleware/requireRole.js";
import { documentUpload } from "../middleware/uploadMiddleware.js";

import { chatWithAI } from "../controllers/aiController.js";
import { getDocumentStatus, uploadDocument } from "../controllers/documentController.js";

const router = express.Router();

router.post("/documents", protect, requireRole("patient"), documentUpload.single("document"), uploadDocument);
router.get("/documents/:id/status", protect, requireRole("patient"), getDocumentStatus);
router.post("/chat", protect, chatWithAI);

export default router;
