import { getInsight } from "../services/aiService.js";

// Cohort-level artifacts change only when models are retrained: cache briefly.
const TTL_MS = 5 * 60 * 1000;
const cache = new Map();
const ALLOWED = new Set(["cohort", "bands", "catalog", "model"]);

export async function getInsightProxy(req, res) {
    const name = req.params.name;

    if (!ALLOWED.has(name)) {
        return res.status(404).json({ success: false, message: "Unknown insight" });
    }

    const hit = cache.get(name);
    if (hit && Date.now() - hit.at < TTL_MS) {
        return res.json({ success: true, data: hit.data });
    }

    const data = await getInsight(name);
    cache.set(name, { at: Date.now(), data });
    res.json({ success: true, data });
}

export function clearInsightCache() {
    cache.clear();
}
