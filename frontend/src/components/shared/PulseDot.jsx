import React from "react";
import { COLORS } from "../../styles/tokens.js";

export function PulseDot({ color = COLORS.critical }) {
  return (
    <span className="relative inline-flex h-2 w-2">
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-60" style={{ backgroundColor: color }} />
      <span className="relative inline-flex rounded-full h-2 w-2" style={{ backgroundColor: color }} />
    </span>
  );
}

export default PulseDot;
