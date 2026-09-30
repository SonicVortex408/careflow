import express from "express";

import protect from "../middleware/authMiddleware.js";

import { getMyProfile, updateMyProfile } from "../controllers/userController.js";

const router = express.Router();

router.get("/profile", protect, getMyProfile);
router.patch("/profile", protect, updateMyProfile);

export default router;
