import SymptomEntry, { BRAIN_FOG_LEVELS, HAIR_LOSS_LEVELS } from "../models/SymptomEntry.js";

const serialize = (s) => ({
    id: s.id,
    fatigueSeverity: s.fatigueSeverity,
    brainFogFrequency: s.brainFogFrequency,
    hairLoss: s.hairLoss,
    notes: s.notes,
    createdAt: s.createdAt,
});

// POST /api/symptoms  (patient symptom intake / PROMs)
export async function createSymptomEntry(req, res) {
    const { fatigueSeverity, brainFogFrequency, hairLoss, notes = "" } = req.body || {};
    const fatigue = Number(fatigueSeverity);

    if (!Number.isInteger(fatigue) || fatigue < 1 || fatigue > 10) {
        return res.status(400).json({ success: false, message: "fatigueSeverity must be a whole number from 1 to 10" });
    }
    if (!BRAIN_FOG_LEVELS.includes(brainFogFrequency)) {
        return res.status(400).json({ success: false, message: `brainFogFrequency must be one of ${BRAIN_FOG_LEVELS.join(", ")}` });
    }
    if (!HAIR_LOSS_LEVELS.includes(hairLoss)) {
        return res.status(400).json({ success: false, message: `hairLoss must be one of ${HAIR_LOSS_LEVELS.join(", ")}` });
    }

    const entry = await SymptomEntry.create({
        patientId: req.account.id,
        fatigueSeverity: fatigue,
        brainFogFrequency,
        hairLoss,
        notes: String(notes).slice(0, 2000),
    });

    res.status(201).json({ success: true, entry: serialize(entry) });
}

// GET /api/symptoms  (patient history, newest first)
export async function listSymptomEntries(req, res) {
    const entries = await SymptomEntry.listForPatient(req.account.id, 50);
    res.json({ success: true, entries: entries.map(serialize) });
}
