import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { BiomarkerGauge } from "../components/biomarkers/BiomarkerGauge.jsx";
import { EvidenceList } from "../components/biomarkers/EvidenceList.jsx";
import { RiskPanel } from "../components/biomarkers/RiskPanel.jsx";
import { SyntheticDataNotice } from "../components/shared/Badges.jsx";
import { validateReportFile } from "../pages/patient/LabUpload.jsx";

afterEach(cleanup);

const ferritin = {
  key: "FERRITIN", display: "Ferritin", value: 12, unit: "ug/L",
  reference: { low: 15, high: 150 }, reference_status: "below",
  functional: { low: 55.4, high: null, low_ci: [51, 60], high_ci: [399, 399] }, functional_status: "below",
  percentile: 7, percentile_fatigue_cohort: 24,
};

describe("components", () => {
  it("gauge states status with words, not colour alone, and shows details on hover", () => {
    render(<BiomarkerGauge band={ferritin} />);
    expect(screen.getByText("Below lab range")).toBeTruthy();
    expect(screen.getByText(/24th percentile/)).toBeTruthy();
    fireEvent.mouseEnter(screen.getByLabelText("Ferritin 12 ug/L"));
    expect(screen.getByRole("tooltip").textContent).toContain("Functional range (synthetic)");
  });

  it("synthetic-data notice carries the mandated label", () => {
    render(<SyntheticDataNotice />);
    expect(screen.getByRole("note").textContent).toMatch(/derived from synthetic data, for research\/demo purposes, not clinical guidance/i);
  });

  it("evidence list flags unverified links", () => {
    render(
      <EvidenceList evidence={{ chains: [
        { finding: "Ferritin below 30 ug/L", relation: "AMPLIFIES", condition: "Subclinical hypothyroidism pattern", symptoms: [], verified: false,
          edge: { evidence_level: "unverified", source_title: "Curated hypothesis" } },
        { finding: "Ferritin below 15 ug/L", relation: "INDICATES", condition: "Low iron stores", symptoms: [{ name: "Chronic fatigue", reported: true }], verified: true,
          edge: { evidence_level: "guideline", source_title: "WHO guideline" } },
      ] }} />
    );
    expect(screen.getByText("Unverified link")).toBeTruthy();
    expect(screen.getByText(/you reported this/)).toBeTruthy();
  });

  it("risk panel shows probability, level label and drivers with direction words", () => {
    render(<RiskPanel risk={{ fatigue: {
      label: "Strong tiredness", probability: 0.94, level: "high", cohort_prevalence: 0.185, model_auroc: 0.81,
      drivers: [{ marker: "FERRITIN", display: "Ferritin", contribution: 1.69, direction: "raises" }],
    } }} />);
    expect(screen.getByText("94%")).toBeTruthy();
    expect(screen.getByText("high likelihood")).toBeTruthy();
    expect(screen.getByText("raises")).toBeTruthy();
  });

  it("validates report files before upload", () => {
    expect(validateReportFile(null)).toMatch(/Choose/);
    expect(validateReportFile({ type: "application/x-msdownload", size: 10 })).toMatch(/PDF/);
    expect(validateReportFile({ type: "application/pdf", size: 11 * 1024 * 1024 })).toMatch(/10 MB/);
    expect(validateReportFile({ type: "application/pdf", size: 1000 })).toBe("");
  });
});
