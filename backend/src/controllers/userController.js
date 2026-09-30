import User from "../models/User.js";
import { publicUser } from "./authController.js";

export const getMyProfile = async (req, res) => {
    res.status(200).json({
        success: true,
        user: req.role === "admin"
            ? { id: req.account.id, name: req.account.name, email: req.account.email, role: "admin" }
            : publicUser(req.account),
    });
};

export const updateMyProfile = async (req, res) => {
    if (req.role === "admin") {
        return res.status(400).json({ success: false, message: "Admins have no patient profile" });
    }

    const { sex, birthYear, name } = req.body || {};
    const fields = {};

    if (sex !== undefined) {
        if (![null, "F", "M"].includes(sex)) {
            return res.status(400).json({ success: false, message: "sex must be F, M or null" });
        }
        fields.sex = sex;
    }
    if (birthYear !== undefined) {
        const year = birthYear === null ? null : Number(birthYear);
        if (year !== null && !(year >= 1900 && year <= new Date().getFullYear())) {
            return res.status(400).json({ success: false, message: "Invalid birth year" });
        }
        fields.birthYear = year;
    }
    if (name) {
        fields.name = String(name).slice(0, 120);
    }

    const user = await User.update(req.account.id, fields);
    res.json({ success: true, user: publicUser(user) });
};
