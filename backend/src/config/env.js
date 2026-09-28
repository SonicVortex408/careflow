import dotenv from "dotenv";

dotenv.config();

const env = {
    port: process.env.PORT || 5000,

    mongoUri: process.env.MONGO_URI,

    jwtSecret: process.env.JWT_SECRET,

    aiServiceUrl:
        process.env.AI_SERVICE_URL || "http://localhost:8000",

    nodeEnv:
        process.env.NODE_ENV || "development",
};

export default env;