/**
 * Seed the first platform admin and a demo clinician (risk R8: the review queue
 * needs a clinician to exist). Idempotent.
 *
 *   SEED_ADMIN_EMAIL=... SEED_ADMIN_PASSWORD=... \
 *   SEED_CLINICIAN_EMAIL=... SEED_CLINICIAN_PASSWORD=... npm run seed
 */
import bcrypt from "bcryptjs";
import mongoose from "mongoose";

import env from "../config/env.js";
import Admin from "../models/Admin.js";
import User from "../models/User.js";

async function upsert(Model, { name, email, password, ...extra }) {
    if (!email || !password) return null;
    const existing = await Model.findOne({ email: email.toLowerCase() });
    if (existing) return { email, created: false };
    await Model.create({ name, email, password: await bcrypt.hash(password, 10), ...extra });
    return { email, created: true };
}

export async function seed() {
    const results = {
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
    return results;
}

if (import.meta.url === `file://${process.argv[1]}`) {
    await mongoose.connect(env.mongoUri);
    console.log(JSON.stringify(await seed(), null, 2));
    await mongoose.disconnect();
}
