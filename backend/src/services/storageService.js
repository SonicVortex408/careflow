/**
 * Where uploaded originals are kept.
 *
 *   supabase  private Supabase Storage bucket (SUPABASE_URL + SUPABASE_SERVICE_KEY);
 *             used in production, where the backend container has no persistent disk.
 *   local     UPLOAD_DIR on disk (docker-compose, local dev, tests).
 *
 * Stored paths are prefixed with the driver ("supabase:" / "local:") so a
 * report keeps pointing at the right place if the configuration changes.
 */
import crypto from "crypto";
import fs from "fs/promises";
import path from "path";

import env from "../config/env.js";

const EXTENSIONS = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "image/png": ".png",
    "image/jpeg": ".jpg",
};

export const storageDriver = () => (env.supabaseUrl && env.supabaseServiceKey ? "supabase" : "local");

function supabaseHeaders(extra = {}) {
    return {
        apikey: env.supabaseServiceKey,
        Authorization: `Bearer ${env.supabaseServiceKey}`,
        ...extra,
    };
}

async function supabaseFetch(pathname, init) {
    const response = await fetch(`${env.supabaseUrl}/storage/v1${pathname}`, init);
    if (!response.ok) {
        const text = await response.text();
        const error = new Error(`Supabase Storage ${response.status}: ${text.slice(0, 200)}`);
        error.upstreamStatus = response.status;
        throw error;
    }
    return response;
}

/** Create the private bucket if it does not exist (idempotent). */
export async function ensureBucket() {
    if (storageDriver() !== "supabase") return false;
    try {
        await supabaseFetch("/bucket", {
            method: "POST",
            headers: supabaseHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify({ id: env.storageBucket, name: env.storageBucket, public: false }),
        });
        return true;
    } catch (error) {
        // Storage answers 400/409 "already exists" for an existing bucket.
        if ([400, 409].includes(error.upstreamStatus) && /exist/i.test(error.message)) return false;
        throw error;
    }
}

/** Save an upload; returns the storage path to keep on the record. */
export async function saveUpload({ buffer, mimeType, folder, ownerId }) {
    const name = `${Date.now()}-${crypto.randomUUID()}${EXTENSIONS[mimeType] || ""}`;
    const key = `${folder}/${ownerId}/${name}`;

    if (storageDriver() === "supabase") {
        await supabaseFetch(`/object/${env.storageBucket}/${key}`, {
            method: "POST",
            headers: supabaseHeaders({ "Content-Type": mimeType, "x-upsert": "false" }),
            body: buffer,
        });
        return `supabase:${key}`;
    }

    const file = path.resolve(process.cwd(), env.uploadDir, key);
    await fs.mkdir(path.dirname(file), { recursive: true });
    await fs.writeFile(file, buffer);
    return `local:${file}`;
}

export async function removeUpload(storagePath) {
    const [driver, ...rest] = String(storagePath).split(":");
    const location = rest.join(":");

    if (driver === "supabase") {
        if (storageDriver() !== "supabase") return;
        await supabaseFetch(`/object/${env.storageBucket}`, {
            method: "DELETE",
            headers: supabaseHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify({ prefixes: [location] }),
        });
    } else if (driver === "local") {
        await fs.rm(location, { force: true });
    }
}
