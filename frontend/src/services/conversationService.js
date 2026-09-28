const API_BASE_URL = "https://careflow-gwxc.onrender.com/api";

/* =========================
   AUTH HEADER
========================= */

const getAuthHeaders = () => {
    const token = localStorage.getItem("token");

    return {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
    };
};


/* =========================
   GET ALL CONVERSATIONS
========================= */

export const getConversations = async () => {
    const response = await fetch(
        `${API_BASE_URL}/conversations`,
        {
            method: "GET",
            headers: getAuthHeaders(),
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.message || "Failed to load conversations"
        );
    }

    return data.conversations;
};


/* =========================
   CREATE CONVERSATION
========================= */

export const createConversation = async () => {
    const response = await fetch(
        `${API_BASE_URL}/conversations`,
        {
            method: "POST",
            headers: getAuthHeaders(),
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.message || "Failed to create conversation"
        );
    }

    return data.conversation;
};


/* =========================
   GET CONVERSATION MESSAGES
========================= */

export const getConversationMessages = async (
    conversationId
) => {
    const response = await fetch(
        `${API_BASE_URL}/conversations/${conversationId}/messages`,
        {
            method: "GET",
            headers: getAuthHeaders(),
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.message || "Failed to load messages"
        );
    }

    return data.messages;
};
