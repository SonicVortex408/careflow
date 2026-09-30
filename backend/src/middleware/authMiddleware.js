import jwt from "jsonwebtoken";
import env from "../config/env.js";
import User from "../models/User.js";
import Admin from "../models/Admin.js";

// Tokens issued before the role split carry role "user"; they are patients.
const USER_TOKEN_ROLES = new Set(["user", "patient", "clinician"]);

const protect = async (req, res, next) => {
    try {
        const authHeader = req.headers.authorization;

        if (!authHeader || !authHeader.startsWith("Bearer ")) {
            return res.status(401).json({
                success: false,
                message: "Not authenticated",
            });
        }

        const token = authHeader.replace(/^Bearer\s+/i, "").trim();

        if (!token) {
            return res.status(401).json({
                success: false,
                message: "Token is required",
            });
        }

        const decoded = jwt.verify(token, env.jwtSecret);

        let account;
        let role;

        if (USER_TOKEN_ROLES.has(decoded.role)) {
            account = await User.findById(decoded.id).select("-password");
            // The database, not the token, is authoritative for the role.
            role = account?.role || "patient";
        } else if (decoded.role === "admin") {
            account = await Admin.findById(decoded.id).select("-password");
            role = "admin";
        } else {
            return res.status(401).json({
                success: false,
                message: "Invalid account role",
            });
        }

        if (!account) {
            return res.status(401).json({
                success: false,
                message: "Account not found",
            });
        }

        req.account = account;
        req.role = role;

        next();
    } catch (error) {
        return res.status(401).json({
            success: false,
            message: "Invalid or expired token",
        });
    }
};

export default protect;
