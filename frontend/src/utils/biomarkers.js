/* Pure helpers for biomarker display (unit-tested). */

export const BIOMARKER_ORDER = ["TSH", "FT4", "FT3", "TPOAB", "VITD", "B12", "FERRITIN", "MG", "ZINC"];

export const SYNTHETIC_LABEL = "Derived from synthetic data, for research/demo purposes, not clinical guidance.";

export function formatValue(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  const n = Number(v);
  if (Number.isInteger(n) || Math.abs(n) >= 100) return String(Math.round(n));
  if (Math.abs(n) >= 10) return n.toFixed(1).replace(/\.0$/, "");
  return String(Number(n.toFixed(2)));
}

/** Overall status used for badges: outside the lab range beats outside the functional range. */
export function markerStatus(band) {
  if (!band) return "unknown";
  if (band.reference_status === "below") return "low";
  if (band.reference_status === "above") return "high";
  if (band.functional_status === "below" || band.functional_status === "above") return "borderline";
  return "in_range";
}

export const STATUS_META = {
  low: { label: "Below lab range", tone: "serious" },
  high: { label: "Above lab range", tone: "serious" },
  borderline: { label: "Near range edge", tone: "warning" },
  in_range: { label: "Within range", tone: "good" },
  unknown: { label: "Not measured", tone: "neutral" },
};

/**
 * Position of a value relative to its reference range: 0 = low end, 1 = high end.
 * Used by the radar so markers with different units share one scale.
 */
export function referencePosition(value, low, high) {
  if (value === null || value === undefined) return null;
  const span = high - low;
  if (!(span > 0)) return null;
  return (value - low) / span;
}

/** Radar radius in [0, 1]: reference range maps to [0.25, 0.75]; clamped beyond. */
export function radarRadius(position) {
  if (position === null) return null;
  const r = 0.25 + position * 0.5;
  return Math.max(0, Math.min(1, r));
}

/** Gauge domain covering reference, functional band and the value with 12% padding. */
export function gaugeDomain(value, reference, functional) {
  const points = [reference.low, reference.high, value];
  if (functional?.low !== null && functional?.low !== undefined) points.push(functional.low);
  if (functional?.high !== null && functional?.high !== undefined) points.push(functional.high);
  const lo = Math.min(...points);
  const hi = Math.max(...points);
  const pad = (hi - lo || Math.abs(hi) || 1) * 0.12;
  return [Math.max(0, lo - pad), hi + pad];
}

export function ordinal(n) {
  const s = n % 100 >= 11 && n % 100 <= 13 ? "th" : { 1: "st", 2: "nd", 3: "rd" }[n % 10] || "th";
  return `${n}${s}`;
}

export const RISK_TONE = { low: "good", moderate: "warning", high: "serious" };

export function sortBands(bands) {
  return BIOMARKER_ORDER.filter((k) => bands?.[k]).map((k) => bands[k]);
}
