import { api } from "./apiClient.js";

/** Returns { response, escalation } - the reply has already passed the server-side guardrails. */
export async function sendAIMessage(message, conversationId) {
    const data = await api("/ai/chat", { method: "POST", body: { message, conversationId } });
    return { response: data.response, escalation: data.escalation };
}

export async function uploadDocument(file) {
    const form = new FormData();
    form.append("document", file);
    return api("/ai/documents", { method: "POST", form });
}

export const getDocumentStatus = async (id) => (await api(`/ai/documents/${id}/status`)).document;
