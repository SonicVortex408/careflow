import express from "express";

import protect from "../middleware/authMiddleware.js";
import requireRole from "../middleware/requireRole.js";

import { getReview, listReviews, submitReview } from "../controllers/reviewController.js";

const router = express.Router();

router.use(protect, requireRole("clinician", "admin"));

router.get("/", listReviews);
router.get("/:id", getReview);
// Sign-off is a clinician act; admins can view the queue but not approve.
router.post("/:id", requireRole("clinician"), submitReview);

export default router;
