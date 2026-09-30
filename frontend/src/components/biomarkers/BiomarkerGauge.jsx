import React, { useId, useState } from "react";

import { COLORS, VIZ } from "../../styles/tokens.js";
import { formatValue, gaugeDomain, markerStatus, ordinal } from "../../utils/biomarkers.js";
import { MarkerStatusBadge } from "../shared/Badges.jsx";

const W = 320;
const H = 44;
const TRACK_Y = 16;
const TRACK_H = 12;

/**
 * Horizontal gauge: lab reference range (filled band) vs discovered functional
 * range (outlined, textured band) vs the patient's value (marker).
 * Status is carried by the badge (icon + label), never by colour alone.
 */
export function BiomarkerGauge({ band }) {
  const [hover, setHover] = useState(false);
  const patternId = useId().replace(/:/g, "");
  const { value, reference, functional } = band;
  const [lo, hi] = gaugeDomain(value, reference, functional);
  const x = (v) => 8 + ((v - lo) / (hi - lo)) * (W - 16);
  const fLow = functional?.low ?? lo;
  const fHigh = functional?.high ?? hi;
  const status = markerStatus(band);
  const cohortPct = band.percentile_fatigue_cohort;

  return (
    <div
      className="relative rounded-2xl border p-4 bg-white"
      style={{ borderColor: COLORS.line }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onFocus={() => setHover(true)}
      onBlur={() => setHover(false)}
      tabIndex={0}
      aria-label={`${band.display} ${formatValue(value)} ${band.unit}`}
    >
      <div className="flex items-start justify-between gap-3 mb-1">
        <div>
          <div className="text-sm font-semibold" style={{ color: COLORS.ink }}>{band.display}</div>
          <div className="text-lg font-bold tabular-nums" style={{ color: COLORS.ink }}>
            {formatValue(value)} <span className="text-xs font-medium" style={{ color: COLORS.slate }}>{band.unit}</span>
          </div>
        </div>
        <MarkerStatusBadge status={status} />
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-hidden="true">
        <defs>
          <pattern id={patternId} width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
            <line x1="0" y1="0" x2="0" y2="6" stroke={VIZ.functionalBand} strokeWidth="1.5" strokeOpacity="0.55" />
          </pattern>
        </defs>
        <rect x={8} y={TRACK_Y} width={W - 16} height={TRACK_H} rx={4} fill={VIZ.grid} />
        <rect
          x={x(reference.low)} y={TRACK_Y}
          width={Math.max(2, x(reference.high) - x(reference.low))} height={TRACK_H}
          rx={4} fill={VIZ.referenceBand}
        />
        {functional && (
          <rect
            x={x(fLow)} y={TRACK_Y - 3}
            width={Math.max(2, x(fHigh) - x(fLow))} height={TRACK_H + 6}
            rx={4} fill={`url(#${patternId})`} stroke={VIZ.functionalBand} strokeWidth="1.5"
          />
        )}
        <line x1={x(value)} x2={x(value)} y1={TRACK_Y - 8} y2={TRACK_Y + TRACK_H + 8} stroke={COLORS.ink} strokeWidth="2.5" strokeLinecap="round" />
        <circle cx={x(value)} cy={TRACK_Y - 9} r={4.5} fill={COLORS.ink} stroke="#fff" strokeWidth="2" />
        <text x={x(reference.low)} y={H - 1} fontSize="9" textAnchor="middle" fill={VIZ.axis}>{formatValue(reference.low)}</text>
        <text x={x(reference.high)} y={H - 1} fontSize="9" textAnchor="middle" fill={VIZ.axis}>{formatValue(reference.high)}</text>
      </svg>

      {typeof cohortPct === "number" && (
        <p className="text-xs mt-1" style={{ color: COLORS.slate }}>
          {ordinal(cohortPct)} percentile among the synthetic cohort with strong tiredness
        </p>
      )}

      {hover && (
        <div
          role="tooltip"
          className="absolute z-10 left-4 right-4 top-full -mt-2 rounded-xl border bg-white shadow-lg p-3 text-xs space-y-1"
          style={{ borderColor: COLORS.line, color: COLORS.ink }}
        >
          <div><strong>Your value:</strong> {formatValue(value)} {band.unit}</div>
          <div><strong>Lab reference range:</strong> {formatValue(reference.low)}–{formatValue(reference.high)} {band.unit}</div>
          <div>
            <strong>Functional range (synthetic):</strong>{" "}
            {functional ? `${functional.low === null ? "≤" : formatValue(functional.low)}–${functional.high === null ? "and above" : formatValue(functional.high)}` : "no clear symptom link found"}
          </div>
          {typeof band.percentile === "number" && <div><strong>Cohort percentile:</strong> {ordinal(band.percentile)}</div>}
        </div>
      )}
    </div>
  );
}

export function GaugeLegend() {
  return (
    <div className="flex flex-wrap items-center gap-4 text-xs" style={{ color: COLORS.slate }}>
      <span className="inline-flex items-center gap-1.5">
        <span className="inline-block w-5 h-2.5 rounded" style={{ backgroundColor: VIZ.referenceBand }} /> Lab reference range
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span
          className="inline-block w-5 h-3 rounded"
          style={{
            border: `1.5px solid ${VIZ.functionalBand}`,
            backgroundImage: `repeating-linear-gradient(45deg, ${VIZ.functionalBand}88 0 1.5px, transparent 1.5px 5px)`,
          }}
        /> Functional range (synthetic cohort)
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="inline-block w-0.5 h-3.5 rounded" style={{ backgroundColor: COLORS.ink }} /> Your value
      </span>
    </div>
  );
}

export default BiomarkerGauge;
