import app from "./app.js";
import env from "./config/env.js";
import connectDB from "./config/db.js";
import { ensureBucket } from "./services/storageService.js";

const startServer = async () => {
    await connectDB();
    await ensureBucket().catch((error) => console.error("Storage bucket check failed:", error.message));

    app.listen(env.port, () => {
        console.log(`PolyMarker API listening on port ${env.port}`);
    });
};

startServer();
