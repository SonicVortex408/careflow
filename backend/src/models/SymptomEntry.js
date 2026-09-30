import { newId, query } from "../config/db.js";

// Patient-reported outcome measures (PROMs).
export const BRAIN_FOG_LEVELS = ["never", "rarely", "sometimes", "often", "always"];
export const HAIR_LOSS_LEVELS = ["none", "mild", "moderate", "severe"];

const COLUMNS = "id, patient_id, fatigue_severity, brain_fog_frequency, hair_loss, notes, created_at, updated_at";

const toEntry = (r) =>
    r && {
        id: r.id,
        patientId: r.patient_id,
        fatigueSeverity: r.fatigue_severity,
        brainFogFrequency: r.brain_fog_frequency,
        hairLoss: r.hair_loss,
        notes: r.notes,
        createdAt: r.created_at,
        updatedAt: r.updated_at,
    };

export const toProms = (entry) => ({
    fatigue_severity: entry.fatigueSeverity,
    brain_fog_frequency: entry.brainFogFrequency,
    hair_loss: entry.hairLoss,
});

const SymptomEntry = {
    create: async ({ patientId, fatigueSeverity, brainFogFrequency, hairLoss, notes = "" }) =>
        toEntry(
            (
                await query(
                    `INSERT INTO symptom_entries (id, patient_id, fatigue_severity, brain_fog_frequency, hair_loss, notes)
                     VALUES ($1, $2, $3, $4, $5, $6) RETURNING ${COLUMNS}`,
                    [newId(), patientId, fatigueSeverity, brainFogFrequency, hairLoss, notes]
                )
            ).rows[0]
        ),

    listForPatient: async (patientId, limit = 50) =>
        (
            await query(
                `SELECT ${COLUMNS} FROM symptom_entries WHERE patient_id = $1 ORDER BY created_at DESC, id DESC LIMIT $2`,
                [patientId, limit]
            )
        ).rows.map(toEntry),

    latestForPatient: async (patientId) => (await SymptomEntry.listForPatient(patientId, 1))[0] || null,
};

export default SymptomEntry;
