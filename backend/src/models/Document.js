import mongoose from "mongoose";

const documentSchema = new mongoose.Schema(
    {
        user: {
            type: mongoose.Schema.Types.ObjectId,
            ref: "User",
            required: true,
            index: true,
        },

        originalName: {
            type: String,
            required: true,
            trim: true,
        },

        filename: {
            type: String,
            required: true,
        },

        mimeType: {
            type: String,
            required: true,
        },

        size: {
            type: Number,
            required: true,
        },

        storagePath: {
            type: String,
            required: true,
        },

        status: {
            type: String,
            enum: [
                "uploaded",
                "processing",
                "ready",
                "failed",
            ],
            default: "uploaded",
        },
    },
    {
        timestamps: true,
    }
);

const Document = mongoose.model(
    "Document",
    documentSchema
);

export default Document;