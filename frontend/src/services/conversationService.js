import { api } from "./apiClient.js";

export const getConversations = async () => (await api("/conversations")).conversations;

export const createConversation = async () => (await api("/conversations", { method: "POST" })).conversation;

export const getConversationMessages = async (conversationId) =>
    (await api(`/conversations/${conversationId}/messages`)).messages;
