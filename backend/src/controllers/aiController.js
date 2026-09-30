import { sendMessageToAI } from "../services/aiService.js";
import { latestApprovedContext } from "../services/reportService.js";
import Conversation from "../models/Conversation.js";
import Message from "../models/Message.js";


export async function chatWithAI(req, res) {
    const { message, conversationId } = req.body || {};

    if (!message || typeof message !== "string" || message.length > 4000) {
        return res.status(400).json({
            success: false,
            message: "Message is required (max 4000 characters)"
        });
    }

    if (!conversationId) {
        return res.status(400).json({
            success: false,
            message: "Conversation ID is required"
        });
    }

    // Conversation must belong to the authenticated user.
    const conversation = await Conversation.findOwn(conversationId, req.account.id);

    if (!conversation) {
        return res.status(404).json({
            success: false,
            message: "Conversation not found"
        });
    }

    await Message.create({
        conversationId: conversation.id,
        role: "user",
        content: message
    });

    const newTitle = conversation.title === "New Conversation" ? message.substring(0, 100) : null;

    // Only clinician-approved results are ever given to the assistant as context.
    const patientContext = req.role === "patient"
        ? await latestApprovedContext(req.account)
        : null;

    let result;
    try {
        result = await sendMessageToAI(
            message,
            conversation.threadId,
            req.account.id,
            patientContext
        );
    } catch (error) {
        return res.status(502).json({
            success: false,
            message: "AI service unavailable"
        });
    }

    await Message.create({
        conversationId: conversation.id,
        role: "assistant",
        content: result.response,
        escalation: result.escalation || null
    });

    await Conversation.touch(conversation.id, newTitle);

    return res.status(200).json({
        success: true,
        response: result.response,
        escalation: result.escalation || null
    });
}
