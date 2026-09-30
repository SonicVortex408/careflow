/**
 * Seed the first platform admin and a demo clinician (risk R8: the review queue
 * needs a clinician to exist). Idempotent. Applies the schema and creates the
 * Storage bucket first.
 *
 *   SEED_ADMIN_EMAIL=... SEED_ADMIN_PASSWORD=... \
 *   SEED_CLINICIAN_EMAIL=... SEED_CLINICIAN_PASSWORD=... npm run seed
 */
import bcrypt from "bcryptjs";

import { closePool, migrate } from "../config/db.js";
import Admin from "../models/Admin.js";
import User from "../models/User.js";
import { ensureBucket } from "../services/storageService.js";

async function upsert(Model, { name, email, password, ...extra }) {
    if (!email || !password) return null;
    if (await Model.findByEmail(email)) return { email, created: false };
    await Model.create({ name, email, password: await bcrypt.hash(password, 10), ...extra });
    return { email, created: true };
}

export async function seed() {
    return {
        admin: await upsert(Admin, {
            name: process.env.SEED_ADMIN_NAME || "Platform Admin",
            email: process.env.SEED_ADMIN_EMAIL,
            password: process.env.SEED_ADMIN_PASSWORD,
        }),
        clinician: await upsert(User, {
            name: process.env.SEED_CLINICIAN_NAME || "Dr. Demo Clinician",
            email: process.env.SEED_CLINICIAN_EMAIL,
            password: process.env.SEED_CLINICIAN_PASSWORD,
            role: "clinician",
        }),
        patient: await upsert(User, {
            name: process.env.SEED_PATIENT_NAME || "Demo Patient",
            email: process.env.SEED_PATIENT_EMAIL,
            password: process.env.SEED_PATIENT_PASSWORD,
            role: "patient",
            sex: "F",
            birthYear: 1985,
        }),
    };
}

if (import.meta.url === `file://${process.argv[1]}`) {
    await migrate();
    await ensureBucket();
    console.log(JSON.stringify(await seed(), null, 2));
    await closePool();
}
