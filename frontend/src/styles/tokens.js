/* ============================================================================
   DESIGN TOKENS
   ========================================================================== */

export const COLORS = {
  teal: "#0F6E63",
  tealSoft: "#E4F2EF",
  blue: "#2856C7",
  blueSoft: "#E8EEFB",
  success: "#1D9A6C",
  successSoft: "#E4F5EC",
  warning: "#C7791F",
  warningSoft: "#FBF0E1",
  critical: "#C4372B",
  criticalSoft: "#FAE7E5",
  ink: "#101A19",
  slate: "#5B6B69",
  line: "#E2E8E6",
  bg: "#F6F8F7",
  surface: "#FFFFFF",
};

/* Data-visualisation roles (validated reference palette; see docs/ARCHITECTURE.md).
   Status colours are reserved for state and always ship with an icon + label. */
export const VIZ = {
  series1: "#2a78d6", // blue  - "you" / primary series
  series2: "#eb6834", // orange - second category (e.g. strong tiredness)
  series3: "#1baf7a", // aqua
  context: "#c3c2b7", // recessive context points
  referenceBand: "#cde2fb", // lab reference range (sequential blue 100)
  functionalBand: "#2a78d6", // functional range outline / texture ink
  grid: "#e8e7e3",
  axis: "#52514e",
  status: {
    good: "#0ca30c",
    warning: "#fab219",
    serious: "#ec835a",
    critical: "#d03b3b",
  },
};
