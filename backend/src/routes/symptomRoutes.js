import express from "express";

import protect from "../middleware/authMiddleware.js";
import requireRole from "../middleware/requireRole.js";

import { createSymptomEntry, listSymptomEntries } from "../controllers/symptomController.js";

const router = express.Router();

router.use(protect, requireRole("patient"));

router.post("/", createSymptomEntry);
router.get("/", listSymptomEntries);

export default router;
