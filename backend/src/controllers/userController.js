import { publicUser } from "./authController.js";

export const getMyProfile = async (req, res) => {
    res.status(200).json({
        success: true,
        user: req.role === "admin"
            ? { id: req.account._id, name: req.account.name, email: req.account.email, role: "admin" }
            : publicUser(req.account),
    });
};

export const updateMyProfile = async (req, res) => {
    if (req.role === "admin") {
        return res.status(400).json({ success: false, message: "Admins have no patient profile" });
    }

    const { sex, birthYear, name } = req.body || {};

    if (sex !== undefined) {
        if (![null, "F", "M"].includes(sex)) {
            return res.status(400).json({ success: false, message: "sex must be F, M or null" });
        }
        req.account.sex = sex;
    }
    if (birthYear !== undefined) {
        const year = birthYear === null ? null : Number(birthYear);
        if (year !== null && !(year >= 1900 && year <= new Date().getFullYear())) {
            return res.status(400).json({ success: false, message: "Invalid birth year" });
        }
        req.account.birthYear = year;
    }
    if (name) {
        req.account.name = String(name).slice(0, 120);
    }

    await req.account.save();
    res.json({ success: true, user: publicUser(req.account) });
};
