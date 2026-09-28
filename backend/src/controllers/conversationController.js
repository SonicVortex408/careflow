import crypto from "crypto";
import Conversation from "../models/Conversation.js";
import Message from "../models/Message.js";

export async function createConversation(req, res) {

    try {

        if (!req.account) {
            return res.status(401).json({
                success: false,
                message: "Not authenticated"
            });
        }

        const threadId = crypto.randomUUID();

        const conversation = await Conversation.create({
            user: req.account._id,
            title: "New Conversation",
            threadId
        });

        return res.status(201).json({
            success: true,
            conversation: {
                id: conversation._id,
                title: conversation.title,
                threadId: conversation.threadId,
                createdAt: conversation.createdAt,
                updatedAt: conversation.updatedAt
            }
        });

    } catch (error) {

        console.error(
            "Create conversation error:",
            error
        );

        return res.status(500).json({
            success: false,
            message: "Failed to create conversation"
        });
    }
}


export async function getConversationMessages(req, res) {

    try {

        const { conversationId } = req.params;


        // Make sure conversation belongs to logged-in user
        const conversation = await Conversation.findOne({

            _id: conversationId,

            user: req.account._id

        });


        if (!conversation) {

            return res.status(404).json({
                success: false,
                message: "Conversation not found"
            });

        }


        // Get all messages for this conversation
        const messages = await Message.find({

            conversation: conversation._id

        })
        .sort({ createdAt: 1 });


        return res.status(200).json({

            success: true,

            messages

        });

    } catch (error) {

        console.error(
            "Get conversation messages error:",
            error
        );

        return res.status(500).json({

            success: false,

            message: "Failed to get conversation messages"

        });

    }
}

export async function getConversations(req, res) {
    try {

        if (!req.account) {
            return res.status(401).json({
                success: false,
                message: "Not authenticated"
            });
        }

        const conversations = await Conversation.find({
            user: req.account._id
        })
        .sort({ updatedAt: -1 });

        return res.status(200).json({
            success: true,
            conversations: conversations.map((conversation) => ({
                id: conversation._id,
                title: conversation.title,
                threadId: conversation.threadId,
                createdAt: conversation.createdAt,
                updatedAt: conversation.updatedAt
            }))
        });

    } catch (error) {

        console.error(
            "Get conversations error:",
            error
        );

        return res.status(500).json({
            success: false,
            message: "Failed to get conversations"
        });
    }
}