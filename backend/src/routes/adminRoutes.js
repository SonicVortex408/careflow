import express from "express";

import protect from "../middleware/authMiddleware.js";
import adminOnly from "../middleware/adminMiddleware.js";

import { getAdminProfile } from "../controllers/adminController.js";

const router = express.Router();

router.get(
    "/profile",
    protect,
    adminOnly,
    getAdminProfile
);

export default router;