/**
 * Apply src/db/schema.sql (idempotent) and create the private Storage bucket
 * when Supabase Storage is configured.
 *
 *   DATABASE_URL=... npm run migrate
 */
import { closePool, migrate } from "../config/db.js";
import { ensureBucket, storageDriver } from "../services/storageService.js";

await migrate();
const bucketCreated = await ensureBucket();
console.log(JSON.stringify({ schema: "applied", storage: storageDriver(), bucketCreated }));
await closePool();
