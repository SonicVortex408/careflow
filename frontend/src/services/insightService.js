import { api } from "./apiClient.js";

const cache = new Map();

/** Cohort-level synthetic analytics: cohort | bands | catalog | model. Cached per session. */
export async function getInsight(name) {
    if (!cache.has(name)) {
        cache.set(name, api(`/insights/${name}`).then((d) => d.data).catch((e) => {
            cache.delete(name);
            throw e;
        }));
    }
    return cache.get(name);
}
