import dotenv from "dotenv";

dotenv.config({ quiet: true });

const nodeEnv = process.env.NODE_ENV || "development";

if (!process.env.JWT_SECRET && nodeEnv === "production") {
    throw new Error("JWT_SECRET must be set in production");
}

const env = {
    port: process.env.PORT || 5000,

    mongoUri: process.env.MONGO_URI,

    jwtSecret: process.env.JWT_SECRET || "dev-only-insecure-secret",

    // ai-service container listens on 8080 (was wrongly defaulted to 8000).
    aiServiceUrl: process.env.AI_SERVICE_URL || "http://localhost:8080",

    // Shared secret sent to ai-service as X-Internal-Key.
    aiInternalKey: process.env.AI_INTERNAL_KEY || "",

    aiTimeoutMs: Number(process.env.AI_TIMEOUT_MS || 60000),

    frontendUrls: (process.env.FRONTEND_URL || "")
        .split(",")
        .map((u) => u.trim())
        .filter(Boolean),

    uploadDir: process.env.UPLOAD_DIR || "uploads",

    nodeEnv,
};

export default env;
