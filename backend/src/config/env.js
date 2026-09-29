import dotenv from "dotenv";

dotenv.config();

const env = {
    port: process.env.PORT || 5000,

    mongoUri: process.env.MONGO_URI,

    jwtSecret: process.env.JWT_SECRET,

    // ai-service's Dockerfile EXPOSEs 8080 (and reads $PORT, defaulting
    // to 8080) -- 8000 was never correct for the containerised setup,
    // only for a bare `uvicorn --port 8000` run outside Docker.
    aiServiceUrl:
        process.env.AI_SERVICE_URL || "http://localhost:8080",

    nodeEnv:
        process.env.NODE_ENV || "development",
};

export default env;