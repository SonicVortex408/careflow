import express from "express";

import protect from "../middleware/authMiddleware.js";
import requireRole from "../middleware/requireRole.js";
import { reportUpload } from "../middleware/uploadMiddleware.js";

import {
    deleteReport,
    getReport,
    getReportStatus,
    listMyReports,
    uploadReport,
} from "../controllers/reportController.js";

const router = express.Router();

router.use(protect, requireRole("patient"));

router.post("/", reportUpload.single("file"), uploadReport);
router.get("/", listMyReports);
router.get("/:id/status", getReportStatus);
router.get("/:id", getReport);
router.delete("/:id", deleteReport);

export default router;
