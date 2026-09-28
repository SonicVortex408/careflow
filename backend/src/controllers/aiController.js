import { sendMessageToAI } from "../services/aiService.js";
import Conversation from "../models/Conversation.js";
import Message from "../models/Message.js";


export async function chatWithAI(req, res) {

    try {

        const { message, conversationId } = req.body;


        // Validate message
        if (!message || typeof message !== "string") {

            return res.status(400).json({
                success: false,
                message: "Message is required"
            });

        }


        // Validate conversation ID
        if (!conversationId) {

            return res.status(400).json({
                success: false,
                message: "Conversation ID is required"
            });

        }


        // Find conversation belonging to authenticated user
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


        // Save user's message
        await Message.create({

            conversation: conversation._id,

            role: "user",

            content: message

        });


        // Set conversation title from first message
        if (conversation.title === "New Conversation") {

            conversation.title = message.substring(0, 100);

        }


        // Use conversation-specific LangGraph thread
        const threadId = conversation.threadId;


        // Send message to AI service
const result = await sendMessageToAI(
    message,
    threadId,
    req.account._id.toString()
);


        // Save AI response
        await Message.create({

            conversation: conversation._id,

            role: "assistant",

            content: result.response

        });


        // Update conversation timestamp
        conversation.updatedAt = new Date();

        await conversation.save();


        return res.status(200).json({

            success: true,

            response: result.response

        });

    } catch (error) {

        console.error(
            "AI chat error:",
            error
        );


        return res.status(500).json({

            success: false,

            message: "AI service unavailable"

        });

    }
}