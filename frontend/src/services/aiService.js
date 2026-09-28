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
   SEND AI MESSAGE
========================= */

export const sendAIMessage = async (
    message,
    conversationId
) => {
    const response = await fetch(
        `${API_BASE_URL}/ai/chat`,
        {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify({
                message,
                conversationId,
            }),
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.message || "AI request failed"
        );
    }

    return data.response;
};


/* =========================
   UPLOAD MEDICAL DOCUMENT
========================= */

export const uploadDocument = async (file) => {
    const token = localStorage.getItem("token");

    const formData = new FormData();

    formData.append(
        "document",
        file
    );

    const response = await fetch(
        `${API_BASE_URL}/ai/documents`,
        {
            method: "POST",
            headers: {
                Authorization: `Bearer ${token}`,
            },
            body: formData,
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.message ||
            "Document upload failed"
        );
    }

    return data;
};
