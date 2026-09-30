import { describe, expect, it } from "vitest";

import { formatValue, gaugeDomain, markerStatus, ordinal, radarRadius, referencePosition, sortBands } from "../utils/biomarkers.js";

describe("biomarker helpers", () => {
  it("classifies status with lab range before functional band", () => {
    expect(markerStatus({ reference_status: "below", functional_status: "below" })).toBe("low");
    expect(markerStatus({ reference_status: "above" })).toBe("high");
    expect(markerStatus({ reference_status: "within", functional_status: "below" })).toBe("borderline");
    expect(markerStatus({ reference_status: "within", functional_status: null })).toBe("in_range");
    expect(markerStatus(null)).toBe("unknown");
  });

  it("maps the reference range onto the radar's middle ring", () => {
    expect(radarRadius(referencePosition(15, 15, 150))).toBeCloseTo(0.25);
    expect(radarRadius(referencePosition(150, 15, 150))).toBeCloseTo(0.75);
    expect(radarRadius(referencePosition(1000, 15, 150))).toBe(1);
    expect(radarRadius(referencePosition(0, 15, 150))).toBeGreaterThanOrEqual(0);
    expect(referencePosition(1, 5, 5)).toBeNull();
  });

  it("builds a gauge domain that contains every landmark", () => {
    const [lo, hi] = gaugeDomain(12, { low: 15, high: 150 }, { low: 55, high: null });
    expect(lo).toBeLessThan(12);
    expect(hi).toBeGreaterThan(150);
    expect(lo).toBeGreaterThanOrEqual(0);
  });

  it("formats values and ordinals", () => {
    expect(formatValue(12)).toBe("12");
    expect(formatValue(5.8)).toBe("5.8");
    expect(formatValue(12.345)).toBe("12.3");
    expect(formatValue(null)).toBe("—");
    expect(ordinal(1)).toBe("1st");
    expect(ordinal(12)).toBe("12th");
    expect(ordinal(22)).toBe("22nd");
    expect(ordinal(83)).toBe("83rd");
  });

  it("sorts bands in catalog order", () => {
    const bands = { ZINC: { key: "ZINC" }, TSH: { key: "TSH" }, FERRITIN: { key: "FERRITIN" } };
    expect(sortBands(bands).map((b) => b.key)).toEqual(["TSH", "FERRITIN", "ZINC"]);
  });
});
