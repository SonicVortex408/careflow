import express from "express";
import cors from "cors";

import authRoutes from "./routes/authRoutes.js";
import userRoutes from "./routes/userRoutes.js";
import adminRoutes from "./routes/adminRoutes.js";
import aiRoutes from "./routes/aiRoutes.js";
import conversationRoutes from "./routes/conversationRoutes.js";

const app = express();

const allowedOrigins = [
    "http://localhost:5173",
    process.env.FRONTEND_URL,
].filter(Boolean);

app.use(
    cors({
        origin: allowedOrigins,
        credentials: true,
    })
);

app.use(express.json());

app.use("/api/auth", authRoutes);
app.use("/api/users", userRoutes);
app.use("/api/admin", adminRoutes);
app.use("/api/ai", aiRoutes);
app.use("/api/conversations", conversationRoutes);

app.get("/", (req, res) => {
    res.json({
        success: true,
        message: "Hackathon backend API is running",
    });
});

export default app;