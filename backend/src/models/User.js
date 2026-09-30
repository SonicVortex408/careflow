import mongoose from "mongoose";

// Patients and clinicians share one collection (architecture decision 2);
// platform administrators stay in the separate Admin collection.
export const USER_ROLES = ["patient", "clinician"];

const userSchema = new mongoose.Schema(
    {
        name: {
            type: String,
            required: true,
            trim: true,
        },

        email: {
            type: String,
            required: true,
            unique: true,
            lowercase: true,
            trim: true,
        },

        password: {
            type: String,
            required: true,
        },

        role: {
            type: String,
            enum: USER_ROLES,
            default: "patient",
            index: true,
        },

        // Optional demographics used for sex-specific reference ranges and cohort inference.
        sex: {
            type: String,
            enum: ["F", "M", null],
            default: null,
        },

        birthYear: {
            type: Number,
            min: 1900,
            max: 2100,
            default: null,
        },
    },
    {
        timestamps: true,
    }
);

const User = mongoose.model("User", userSchema);

export default User;
