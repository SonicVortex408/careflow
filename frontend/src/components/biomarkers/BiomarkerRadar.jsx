import React from "react";
import {
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import { COLORS, VIZ } from "../../styles/tokens.js";
import { formatValue, markerStatus, radarRadius, referencePosition, sortBands, STATUS_META } from "../../utils/biomarkers.js";

/**
 * Multi-biomarker spider plot. Each axis is scaled to the marker's own lab
 * reference range (inner dashed ring = low end, outer = high end), so markers
 * with different units can be compared at a glance.
 */
export function BiomarkerRadar({ bands }) {
  const rows = sortBands(bands).map((b) => ({
    marker: b.display.replace(" (25-OH)", ""),
    you: radarRadius(referencePosition(b.value, b.reference.low, b.reference.high)),
    low: 0.25,
    high: 0.75,
    band: b,
  }));

  if (rows.length < 3) {
    return <p className="text-sm" style={{ color: COLORS.slate }}>At least three markers are needed for the pattern view.</p>;
  }

  return (
    <div style={{ width: "100%", height: 320 }}>
      <ResponsiveContainer>
        <RadarChart data={rows} outerRadius="72%">
          <PolarGrid stroke={VIZ.grid} />
          <PolarAngleAxis dataKey="marker" tick={{ fontSize: 11, fill: VIZ.axis }} />
          <PolarRadiusAxis domain={[0, 1]} tick={false} axisLine={false} />
          <Radar name="Lab range: low end" dataKey="low" stroke={VIZ.axis} strokeDasharray="4 3" strokeWidth={1.5} fill="none" legendType="plainline" isAnimationActive={false} />
          <Radar name="Lab range: high end" dataKey="high" stroke={VIZ.axis} strokeDasharray="1 3" strokeWidth={1.5} fill="none" legendType="plainline" isAnimationActive={false} />
          <Radar
            name="Your results"
            dataKey="you"
            stroke={VIZ.series1}
            strokeWidth={2}
            fill={VIZ.series1}
            fillOpacity={0.15}
            dot={{ r: 4, fill: VIZ.series1, stroke: "#fff", strokeWidth: 2 }}
            isAnimationActive={false}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const b = payload[0].payload.band;
              return (
                <div className="rounded-xl border bg-white shadow p-2.5 text-xs" style={{ borderColor: COLORS.line, color: COLORS.ink }}>
                  <div className="font-semibold">{b.display}</div>
                  <div>{formatValue(b.value)} {b.unit} (range {formatValue(b.reference.low)}–{formatValue(b.reference.high)})</div>
                  <div style={{ color: COLORS.slate }}>{STATUS_META[markerStatus(b)].label}</div>
                </div>
              );
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: COLORS.slate }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default BiomarkerRadar;
