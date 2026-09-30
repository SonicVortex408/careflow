/* Single HTTP client for the PolyMarker API.
   The base URL comes from VITE_API_BASE_URL (set it in Vercel per environment). */

const configured = import.meta.env.VITE_API_BASE_URL;

export const API_BASE_URL = (configured || "http://localhost:5000/api").replace(/\/+$/, "");

if (!configured && import.meta.env.PROD) {
    // eslint-disable-next-line no-console
    console.warn("VITE_API_BASE_URL is not set; falling back to", API_BASE_URL);
}

export class ApiError extends Error {
    constructor(message, status, data) {
        super(message);
        this.status = status;
        this.data = data;
    }
}

export const tokenStore = {
    get: () => localStorage.getItem("token"),
    set: (token) => localStorage.setItem("token", token),
    clear: () => localStorage.removeItem("token"),
};

/**
 * api("/reports", { method: "POST", form })  -> parsed JSON
 * Throws ApiError with the server's message. A 401 emits "auth:expired".
 */
export async function api(path, { method = "GET", body, form, auth = true, signal } = {}) {
    const headers = {};
    const token = tokenStore.get();

    if (auth && token) headers.Authorization = `Bearer ${token}`;
    if (body !== undefined) headers["Content-Type"] = "application/json";

    let response;
    try {
        response = await fetch(`${API_BASE_URL}${path}`, {
            method,
            headers,
            signal,
            body: form ?? (body !== undefined ? JSON.stringify(body) : undefined),
        });
    } catch (error) {
        if (error.name === "AbortError") throw error;
        throw new ApiError("Cannot reach the server. Check your connection and try again.", 0);
    }

    const text = await response.text();
    let data = null;
    try {
        data = text ? JSON.parse(text) : null;
    } catch {
        data = null;
    }

    if (!response.ok) {
        if (response.status === 401 && auth && token) {
            window.dispatchEvent(new CustomEvent("auth:expired"));
        }
        throw new ApiError(data?.message || `Request failed (${response.status})`, response.status, data);
    }

    return data;
}
