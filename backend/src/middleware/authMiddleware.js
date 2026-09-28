import jwt from "jsonwebtoken";
import env from "../config/env.js";
import User from "../models/User.js";
import Admin from "../models/Admin.js";

const protect = async (req, res, next) => {
    try {
        const authHeader = req.headers.authorization;

        if (!authHeader || !authHeader.startsWith("Bearer ")) {
            return res.status(401).json({
                success: false,
                message: "Not authenticated",
            });
        }

        // Safely extract JWT even if there are extra spaces
        const token = authHeader
            .replace(/^Bearer\s+/i, "")
            .trim();

        if (!token) {
            return res.status(401).json({
                success: false,
                message: "Token is required",
            });
        }

        const decoded = jwt.verify(
            token,
            env.jwtSecret
        );

        let account;

        if (decoded.role === "user") {
            account = await User.findById(decoded.id)
                .select("-password");
        } else if (decoded.role === "admin") {
            account = await Admin.findById(decoded.id)
                .select("-password");
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
        req.role = decoded.role;

        next();

    } catch (error) {
        console.error(
            "Auth middleware error:",
            error.name,
            error.message
        );

        return res.status(401).json({
            success: false,
            message: "Invalid or expired token",
        });
    }
};

export default protect;