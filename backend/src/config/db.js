import crypto from "crypto";
import fs from "fs/promises";
import path from "path";
import { fileURLToPath } from "url";

import pg from "pg";

import env from "./env.js";

const SCHEMA_FILE = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "db", "schema.sql");
// Arbitrary constant: serializes concurrent migrations from several instances.
const MIGRATION_LOCK = 4_242_001;

let pool = null;

/**
 * TLS for the database connection (DATABASE_SSL):
 *   verify   encrypt and verify against DATABASE_CA_CERT (Supabase: Settings -> Database -> SSL certificate)
 *   require  encrypt without verifying the server certificate
 *   disable  plain TCP (local Postgres)
 * Default: disable for localhost, require for anything else.
 */
export function sslConfig(url = env.databaseUrl, mode = env.databaseSsl, ca = env.databaseCaCert) {
    const host = (() => {
        try {
            return new URL(url).hostname;
        } catch {
            return "";
        }
    })();
    const resolved = mode || (["localhost", "127.0.0.1", "::1", ""].includes(host) ? "disable" : "require");
    if (resolved === "disable") return false;
    if (resolved === "verify") {
        if (!ca) throw new Error("DATABASE_SSL=verify needs DATABASE_CA_CERT");
        return { ca, rejectUnauthorized: true };
    }
    return { rejectUnauthorized: false };
}

export function getPool() {
    if (!pool) {
        if (!env.databaseUrl) throw new Error("DATABASE_URL is not set");
        // Strip sslmode from the URL so sslConfig() alone decides TLS.
        const url = new URL(env.databaseUrl);
        url.searchParams.delete("sslmode");
        pool = new pg.Pool({
            connectionString: url.toString(),
            ssl: sslConfig(),
            max: env.databasePoolSize,
            idleTimeoutMillis: 30_000,
        });
        pool.on("error", (err) => console.error("Postgres pool error:", err.message));
    }
    return pool;
}

export const query = (text, params) => getPool().query(text, params);

/** Run fn(client) in a transaction. */
export async function transaction(fn) {
    const client = await getPool().connect();
    try {
        await client.query("BEGIN");
        const result = await fn(client);
        await client.query("COMMIT");
        return result;
    } catch (error) {
        await client.query("ROLLBACK");
        throw error;
    } finally {
        client.release();
    }
}

/** 24-hex id, the same shape as the Mongo ObjectIds the ai-service expects. */
export const newId = () => crypto.randomBytes(12).toString("hex");

export const isId = (value) => typeof value === "string" && /^[0-9a-f]{24}$/.test(value);

export async function migrate() {
    const sql = await fs.readFile(SCHEMA_FILE, "utf8");
    // A transaction-scoped advisory lock also works behind Supabase's
    // transaction-mode pooler.
    await transaction(async (client) => {
        await client.query("SELECT pg_advisory_xact_lock($1)", [MIGRATION_LOCK]);
        await client.query(sql);
    });
}

export async function closePool() {
    if (pool) {
        const p = pool;
        pool = null;
        await p.end();
    }
}

const connectDB = async () => {
    try {
        await query("SELECT 1");
        if (env.dbAutoMigrate) await migrate();
        console.log("Postgres connected");
    } catch (error) {
        console.error("Postgres connection failed:", error.message);
        process.exit(1);
    }
};

export default connectDB;
