import { api } from "./apiClient.js";

export const REPORT_FILE_TYPES = ["application/pdf", "text/plain", "image/png", "image/jpeg"];
export const MAX_REPORT_BYTES = 10 * 1024 * 1024;

export async function uploadReport(file) {
    const form = new FormData();
    form.append("file", file);
    return api("/reports", { method: "POST", form });
}

export const listReports = async () => (await api("/reports")).reports;

export const getReport = async (id) => (await api(`/reports/${id}`)).report;

export const getReportStatus = async (id) => (await api(`/reports/${id}/status`)).report;

export const deleteReport = (id) => api(`/reports/${id}`, { method: "DELETE" });

/** Poll until the report leaves "processing" (or the signal aborts). */
export async function pollReport(id, { intervalMs = 2000, timeoutMs = 180000, onUpdate, signal } = {}) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
        const report = await getReportStatus(id);
        onUpdate?.(report);
        if (report.status !== "processing") return report;
        await new Promise((r) => setTimeout(r, intervalMs));
    }
    throw new Error("Processing is taking longer than expected. Check back in a few minutes.");
}
