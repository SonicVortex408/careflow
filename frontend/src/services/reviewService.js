import { api } from "./apiClient.js";

export const listReviews = async (status = "pending_clinician_review") =>
    (await api(`/reviews?status=${encodeURIComponent(status)}`)).reviews;

export const getReview = async (id) => (await api(`/reviews/${id}`)).report;

export const submitReview = async (id, { decision, comment, editedSummary }) =>
    (await api(`/reviews/${id}`, { method: "POST", body: { decision, comment, editedSummary } })).report;
