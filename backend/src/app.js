import express from "express";
import cors from "cors";
import helmet from "helmet";

import env from "./config/env.js";
import { errorHandler, notFound } from "./middleware/errorMiddleware.js";

import authRoutes from "./routes/authRoutes.js";
import userRoutes from "./routes/userRoutes.js";
import adminRoutes from "./routes/adminRoutes.js";
import aiRoutes from "./routes/aiRoutes.js";
import conversationRoutes from "./routes/conversationRoutes.js";
import reportRoutes from "./routes/reportRoutes.js";
import reviewRoutes from "./routes/reviewRoutes.js";
import symptomRoutes from "./routes/symptomRoutes.js";
import insightRoutes from "./routes/insightRoutes.js";

const app = express();

const allowedOrigins = ["http://localhost:5173", ...env.frontendUrls];

app.disable("x-powered-by");
app.use(helmet());
app.use(
    cors({
        origin: allowedOrigins,
        credentials: true,
    })
);

app.use(express.json({ limit: "1mb" }));

app.use("/api/auth", authRoutes);
app.use("/api/users", userRoutes);
app.use("/api/admin", adminRoutes);
app.use("/api/ai", aiRoutes);
app.use("/api/conversations", conversationRoutes);
app.use("/api/reports", reportRoutes);
app.use("/api/reviews", reviewRoutes);
app.use("/api/symptoms", symptomRoutes);
app.use("/api/insights", insightRoutes);

app.get("/", (req, res) => {
    res.json({
        success: true,
        message: "PolyMarker Analytics API is running",
    });
});

app.get("/api/health", (req, res) => {
    res.json({ success: true, status: "ok" });
});

app.use(notFound);
app.use(errorHandler);

export default app;
