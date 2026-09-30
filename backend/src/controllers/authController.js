import bcrypt from "bcryptjs";

import User from "../models/User.js";
import Admin from "../models/Admin.js";
import generateToken from "../utils/generateToken.js";

const EMAIL_RE = /^\S+@\S+\.\S+$/;

export const publicUser = (user) => ({
    id: user._id,
    name: user.name,
    email: user.email,
    role: user.role,
    sex: user.sex ?? null,
    birthYear: user.birthYear ?? null,
});

// Public self-registration always creates a patient. Clinicians are created by
// an admin (POST /api/admin/clinicians) or the seed script.
export const registerUser = async (req, res) => {
    const { name, email, password, sex, birthYear } = req.body || {};

    if (!name || !email || !password) {
        return res.status(400).json({ success: false, message: "Name, email and password are required" });
    }
    if (!EMAIL_RE.test(email)) {
        return res.status(400).json({ success: false, message: "Enter a valid email address" });
    }
    if (String(password).length < 8) {
        return res.status(400).json({ success: false, message: "Password must be at least 8 characters" });
    }

    const existingUser = await User.findOne({ email: String(email).toLowerCase() });

    if (existingUser) {
        return res.status(409).json({ success: false, message: "User already exists" });
    }

    const user = await User.create({
        name,
        email,
        password: await bcrypt.hash(password, 10),
        role: "patient",
        sex: ["F", "M"].includes(sex) ? sex : null,
        birthYear: Number.isInteger(Number(birthYear)) && birthYear ? Number(birthYear) : null,
    });

    res.status(201).json({
        success: true,
        message: "User registered successfully",
        token: generateToken(user._id, user.role),
        user: publicUser(user),
    });
};

// Patients and clinicians sign in here; the role comes from the account.
export const loginUser = async (req, res) => {
    const { email, password } = req.body || {};

    const user = email ? await User.findOne({ email: String(email).toLowerCase() }) : null;

    if (!user || !password || !(await bcrypt.compare(password, user.password))) {
        return res.status(401).json({ success: false, message: "Invalid credentials" });
    }

    res.json({
        success: true,
        message: "Login successful",
        token: generateToken(user._id, user.role),
        user: publicUser(user),
    });
};

export const loginAdmin = async (req, res) => {
    const { email, password } = req.body || {};

    const admin = email ? await Admin.findOne({ email: String(email).toLowerCase() }) : null;

    if (!admin || !password || !(await bcrypt.compare(password, admin.password))) {
        return res.status(401).json({ success: false, message: "Invalid credentials" });
    }

    res.json({
        success: true,
        message: "Admin login successful",
        token: generateToken(admin._id, "admin"),
        admin: { id: admin._id, name: admin.name, email: admin.email, role: "admin" },
    });
};
