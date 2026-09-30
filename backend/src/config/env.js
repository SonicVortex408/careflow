import dotenv from "dotenv";

dotenv.config({ quiet: true });

const nodeEnv = process.env.NODE_ENV || "development";

if (!process.env.JWT_SECRET && nodeEnv === "production") {
    throw new Error("JWT_SECRET must be set in production");
}

const env = {
    port: process.env.PORT || 5000,

    // Postgres (Supabase: Project Settings -> Database -> Connection string, pooler URL).
    databaseUrl: process.env.DATABASE_URL,
    databaseSsl: process.env.DATABASE_SSL || "",
    databaseCaCert: process.env.DATABASE_CA_CERT || "",
    databasePoolSize: Number(process.env.DATABASE_POOL_SIZE || 5),
    dbAutoMigrate: process.env.DB_AUTO_MIGRATE !== "false",

    jwtSecret: process.env.JWT_SECRET || "dev-only-insecure-secret",

    // ai-service container listens on 8080 (was wrongly defaulted to 8000).
    aiServiceUrl: (process.env.AI_SERVICE_URL || "http://localhost:8080").replace(/\/+$/, ""),

    // Shared secret sent to ai-service as X-Internal-Key.
    aiInternalKey: process.env.AI_INTERNAL_KEY || process.env.INTERNAL_API_KEY || "",

    aiTimeoutMs: Number(process.env.AI_TIMEOUT_MS || 60000),

    frontendUrls: (process.env.FRONTEND_URL || "")
        .split(",")
        .map((u) => u.trim())
        .filter(Boolean),

    // Uploaded originals: Supabase Storage when SUPABASE_URL + SUPABASE_SERVICE_KEY
    // are set, otherwise the local UPLOAD_DIR.
    uploadDir: process.env.UPLOAD_DIR || "uploads",
    supabaseUrl: (process.env.SUPABASE_URL || "").replace(/\/+$/, ""),
    supabaseServiceKey: process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY || "",
    storageBucket: process.env.STORAGE_BUCKET || "lab-reports",

    nodeEnv,
};

export default env;
