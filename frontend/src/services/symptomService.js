import { api } from "./apiClient.js";

export const BRAIN_FOG_LEVELS = ["never", "rarely", "sometimes", "often", "always"];
export const HAIR_LOSS_LEVELS = ["none", "mild", "moderate", "severe"];

export const submitSymptoms = async (entry) => (await api("/symptoms", { method: "POST", body: entry })).entry;

export const listSymptoms = async () => (await api("/symptoms")).entries;
