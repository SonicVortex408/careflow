import express from "express";

import protect from "../middleware/authMiddleware.js";

import { getInsightProxy } from "../controllers/insightController.js";

const router = express.Router();

// Cohort-level synthetic analytics (no patient data): any signed-in role.
router.get("/:name", protect, getInsightProxy);

export default router;
