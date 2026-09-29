import bcrypt from "bcryptjs";

import User from "../models/User.js";
import { publicUser } from "./authController.js";

export const getAdminProfile = async (req, res) => {
    res.json({
        success: true,
        admin: { id: req.account._id, name: req.account.name, email: req.account.email, role: "admin" },
    });
};

// Invite-only clinician accounts (replaces the unauthenticated admin/register route).
export const createClinician = async (req, res) => {
    const { name, email, password } = req.body || {};

    if (!name || !email || !password || String(password).length < 8) {
        return res.status(400).json({ success: false, message: "Name, email and a password of 8+ characters are required" });
    }

    if (await User.findOne({ email: String(email).toLowerCase() })) {
        return res.status(409).json({ success: false, message: "An account with this email already exists" });
    }

    const clinician = await User.create({
        name,
        email,
        password: await bcrypt.hash(password, 10),
        role: "clinician",
    });

    res.status(201).json({ success: true, clinician: publicUser(clinician) });
};

export const listClinicians = async (req, res) => {
    const clinicians = await User.find({ role: "clinician" }).select("-password").sort({ createdAt: -1 });
    res.json({ success: true, clinicians: clinicians.map(publicUser) });
};
