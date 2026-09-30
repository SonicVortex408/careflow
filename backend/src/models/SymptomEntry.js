import mongoose from "mongoose";

// Patient-reported outcome measures (PROMs).
export const BRAIN_FOG_LEVELS = ["never", "rarely", "sometimes", "often", "always"];
export const HAIR_LOSS_LEVELS = ["none", "mild", "moderate", "severe"];

const symptomEntrySchema = new mongoose.Schema(
    {
        patient: {
            type: mongoose.Schema.Types.ObjectId,
            ref: "User",
            required: true,
            index: true,
        },

        fatigueSeverity: { type: Number, required: true, min: 1, max: 10 },
        brainFogFrequency: { type: String, enum: BRAIN_FOG_LEVELS, required: true },
        hairLoss: { type: String, enum: HAIR_LOSS_LEVELS, required: true },
        notes: { type: String, maxlength: 2000, default: "" },
    },
    {
        timestamps: true,
    }
);

symptomEntrySchema.methods.toProms = function toProms() {
    return {
        fatigue_severity: this.fatigueSeverity,
        brain_fog_frequency: this.brainFogFrequency,
        hair_loss: this.hairLoss,
    };
};

const SymptomEntry = mongoose.model("SymptomEntry", symptomEntrySchema);

export default SymptomEntry;
