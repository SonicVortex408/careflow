import bcrypt from "bcryptjs";

import User from "../models/User.js";
import Admin from "../models/Admin.js";
import generateToken from "../utils/generateToken.js";

// =========================
// REGISTER USER
// =========================

export const registerUser = async (req, res) => {
    try {
        const { name, email, password } = req.body;

        if (!name || !email || !password) {
            return res.status(400).json({
                success: false,
                message: "Name, email and password are required"
            });
        }

        const existingUser = await User.findOne({ email });

        if (existingUser) {
            return res.status(409).json({
                success: false,
                message: "User already exists"
            });
        }

        const hashedPassword = await bcrypt.hash(password, 10);

        const user = await User.create({
            name,
            email,
            password: hashedPassword
        });

        const token = generateToken(user._id, "user");

        res.status(201).json({
            success: true,
            message: "User registered successfully",
            token,
            user: {
                id: user._id,
                name: user.name,
                email: user.email
            }
        });

    } catch (error) {
        console.error("Register user error:", error);

        res.status(500).json({
            success: false,
            message: "Failed to register user"
        });
    }
};


// =========================
// LOGIN USER
// =========================

export const loginUser = async (req, res) => {
    try {
        const { email, password } = req.body;

        const user = await User.findOne({ email });

        if (!user) {
            return res.status(401).json({
                success: false,
                message: "Invalid credentials"
            });
        }

        const passwordMatch = await bcrypt.compare(
            password,
            user.password
        );

        if (!passwordMatch) {
            return res.status(401).json({
                success: false,
                message: "Invalid credentials"
            });
        }

        const token = generateToken(user._id, "user");

        res.json({
            success: true,
            message: "Login successful",
            token,
            user: {
                id: user._id,
                name: user.name,
                email: user.email
            }
        });

    } catch (error) {
        console.error("Login user error:", error);

        res.status(500).json({
            success: false,
            message: "Failed to login"
        });
    }
};


// =========================
// REGISTER ADMIN
// =========================




// =========================
// LOGIN ADMIN
// =========================

export const loginAdmin = async (req, res) => {
    try {
        const { email, password } = req.body;

        const admin = await Admin.findOne({ email });

        if (!admin) {
            return res.status(401).json({
                success: false,
                message: "Invalid credentials"
            });
        }

        const passwordMatch = await bcrypt.compare(
            password,
            admin.password
        );

        if (!passwordMatch) {
            return res.status(401).json({
                success: false,
                message: "Invalid credentials"
            });
        }

        const token = generateToken(admin._id, "admin");

        res.json({
            success: true,
            message: "Admin login successful",
            token,
            admin: {
                id: admin._id,
                name: admin.name,
                email: admin.email
            }
        });

    } catch (error) {
        console.error("Login admin error:", error);

        res.status(500).json({
            success: false,
            message: "Failed to login"
        });
    }
};

export const getMyProfile = async (req, res) => {
    res.status(200).json({
        success: true,
        user: req.account
    });
};