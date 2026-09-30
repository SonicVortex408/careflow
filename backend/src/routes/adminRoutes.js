import express from "express";

import protect from "../middleware/authMiddleware.js";
import adminOnly from "../middleware/adminMiddleware.js";

import { createClinician, getAdminProfile, listClinicians } from "../controllers/adminController.js";

const router = express.Router();

router.use(protect, adminOnly);

router.get("/profile", getAdminProfile);
router.get("/clinicians", listClinicians);
router.post("/clinicians", createClinician);

export default router;
