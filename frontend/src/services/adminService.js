import { api } from "./apiClient.js";

export const listClinicians = async () => (await api("/admin/clinicians")).clinicians;

export const createClinician = async (fields) =>
    (await api("/admin/clinicians", { method: "POST", body: fields })).clinician;
