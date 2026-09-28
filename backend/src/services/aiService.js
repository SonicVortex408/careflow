import env from "../config/env.js";

const AI_SERVICE_URL = env.aiServiceUrl;

export async function sendMessageToAI(
    message,
    threadId,
    patientId
) {
    const response = await fetch(
        `${AI_SERVICE_URL}/api/chat/`,
        {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                message,
                thread_id: threadId,
                patient_id: patientId
            })
        }
    );

    if (!response.ok) {
        const errorText = await response.text();

        throw new Error(
            `AI service error ${response.status}: ${errorText}`
        );
    }

    return await response.json();
}