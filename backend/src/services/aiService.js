import fs from "fs";

import env from "../config/env.js";

export class AIServiceError extends Error {
    constructor(message, status = 502) {
        super(message);
        this.status = status;
    }
}

async function aiFetch(path, { method = "GET", body, headers = {}, timeoutMs = env.aiTimeoutMs } = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
        const response = await fetch(`${env.aiServiceUrl}${path}`, {
            method,
            body,
            signal: controller.signal,
            headers: {
                ...(env.aiInternalKey ? { "X-Internal-Key": env.aiInternalKey } : {}),
                ...headers,
            },
        });

        const text = await response.text();
        let data = null;

        try {
            data = text ? JSON.parse(text) : null;
        } catch {
            data = { raw: text };
        }

        if (!response.ok) {
            const error = new AIServiceError(
                `AI service ${response.status}: ${data?.detail || data?.message || "error"}`,
                response.status >= 500 ? 502 : response.status
            );
            error.upstreamStatus = response.status;
            throw error;
        }

        return data;
    } catch (error) {
        if (error instanceof AIServiceError) throw error;
        throw new AIServiceError(error.name === "AbortError" ? "AI service timed out" : "AI service unavailable");
    } finally {
        clearTimeout(timer);
    }
}

const jsonBody = (payload) => ({
    body: JSON.stringify(payload),
    headers: { "Content-Type": "application/json" },
});

async function fileForm(filePath, mimeType, originalName, fields) {
    const form = new FormData();
    // openAsBlob streams from disk instead of reading the whole upload into memory.
    const blob = await fs.openAsBlob(filePath, { type: mimeType });
    form.append("file", blob, originalName);
    for (const [key, value] of Object.entries(fields)) {
        if (value !== undefined && value !== null) form.append(key, typeof value === "string" ? value : String(value));
    }
    return form;
}

export async function enqueueReport({ filePath, mimeType, originalName, reportId, patientId, proms, sex, age }) {
    const form = await fileForm(filePath, mimeType, originalName, {
        report_id: reportId,
        patient_id: patientId,
        proms: proms ? JSON.stringify(proms) : undefined,
        sex,
        age,
    });
    return aiFetch("/api/ocr", { method: "POST", body: form });
}

export async function enqueueDocument({ filePath, mimeType, originalName, documentId, patientId }) {
    const form = await fileForm(filePath, mimeType, originalName, {
        document_id: documentId,
        patient_id: patientId,
    });
    return aiFetch("/api/documents/process", { method: "POST", body: form });
}

export const getJob = (jobId) => aiFetch(`/api/ocr/jobs/${encodeURIComponent(jobId)}`);

export async function sendMessageToAI(message, threadId, patientId, patientContext = null) {
    return aiFetch("/api/chat/", {
        method: "POST",
        ...jsonBody({
            message,
            thread_id: threadId,
            patient_id: patientId,
            patient_context: patientContext,
        }),
    });
}

export const getInsight = (name) => aiFetch(`/api/inference/${name}`);

export const runInference = (payload) => aiFetch("/api/inference", { method: "POST", ...jsonBody(payload) });
