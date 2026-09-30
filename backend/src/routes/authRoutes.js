import express from "express";
import rateLimit from "express-rate-limit";

import {
    registerUser,
    loginUser,
    loginAdmin
} from "../controllers/authController.js";

const router = express.Router();

const authLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    limit: Number(process.env.AUTH_RATE_LIMIT || 50),
    standardHeaders: "draft-7",
    legacyHeaders: false,
});

router.use(authLimiter);

router.post("/register", registerUser);
router.post("/login", loginUser);

// Admin self-registration was removed: seed the first admin with
// `npm run seed`, and admins create clinicians via POST /api/admin/clinicians.
router.post("/admin/login", loginAdmin);

export default router;
