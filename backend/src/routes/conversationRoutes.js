import express from "express";

import protect from "../middleware/authMiddleware.js";

import {
    createConversation,
    getConversationMessages,
    getConversations
} from "../controllers/conversationController.js";

const router = express.Router();

router.get(
    "/",
    protect,
    getConversations
);

router.post(
    "/",
    protect,
    createConversation
);


router.get(
    "/:conversationId/messages",
    protect,
    getConversationMessages
);


export default router;