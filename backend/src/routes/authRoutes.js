import express from "express";

import {
    registerUser,
    loginUser,
    registerAdmin,
    loginAdmin
} from "../controllers/authController.js";

const router = express.Router();

router.post("/register", registerUser);
router.post("/login", loginUser);

router.post("/admin/register", registerAdmin);
router.post("/admin/login", loginAdmin);

export default router;