import mongoose from "mongoose";

const conversationSchema = new mongoose.Schema(
    {
        user: {
            type: mongoose.Schema.Types.ObjectId,
            ref: "User",
            required: true,
        },

        title: {
            type: String,
            default: "New Conversation",
            trim: true,
            maxlength: 100,
        },

        threadId: {
            type: String,
            required: true,
            unique: true,
        },
    },
    {
        timestamps: true,
    }
);

const Conversation = mongoose.model(
    "Conversation",
    conversationSchema
);

export default Conversation;