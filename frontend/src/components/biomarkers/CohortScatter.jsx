import React, { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

import { COLORS, VIZ } from "../../styles/tokens.js";

/**
 * Where the patient sits relative to the synthetic cohort (2-D PCA map of the
 * 9-marker vectors). Only two categories are ever coloured at once - "your
 * group" vs the rest, or "strong tiredness" vs the rest - so the palette stays
 * within the scatter series cap; everything else is recessive grey.
 */
export function CohortScatter({ cohort, position, clusterId, clusterName, height = 340 }) {
  const [colorBy, setColorBy] = useState(clusterId !== undefined && clusterId !== null ? "group" : "fatigue");

  const { highlight, rest } = useMemo(() => {
    const h = [];
    const r = [];
    for (const p of cohort?.points || []) {
      const hit = colorBy === "group" ? p.cluster === clusterId : p.fatigue === 1;
      (hit ? h : r).push(p);
    }
    return { highlight: h, rest: r };
  }, [cohort, colorBy, clusterId]);

  const profiles = Object.fromEntries((cohort?.profiles || []).map((p) => [p.cluster, p]));
  const highlightName = colorBy === "group" ? `Your group: ${clusterName || "—"}` : "Reported strong tiredness";
  const highlightColor = colorBy === "group" ? VIZ.series1 : VIZ.series2;

  const tooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const p = payload[0].payload;
    if (p.you) {
      return <Box><strong>You</strong><div>{clusterName ? `Closest group: ${clusterName}` : ""}</div></Box>;
    }
    const prof = profiles[p.cluster];
    return (
      <Box>
        <div className="font-semibold">{prof?.name || `Group ${p.cluster}`}</div>
        {prof && <div>{Math.round(prof.fatigue_rate * 100)}% of this group report strong tiredness</div>}
        <div style={{ color: COLORS.slate }}>{p.fatigue ? "This person reported strong tiredness" : "No strong tiredness reported"}</div>
      </Box>
    );
  };

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 mb-2" role="group" aria-label="Colour the cohort map by">
        <span className="text-xs" style={{ color: COLORS.slate }}>Highlight:</span>
        {clusterId !== undefined && clusterId !== null && (
          <Toggle active={colorBy === "group"} onClick={() => setColorBy("group")}>Your group</Toggle>
        )}
        <Toggle active={colorBy === "fatigue"} onClick={() => setColorBy("fatigue")}>Strong tiredness</Toggle>
      </div>
      <div style={{ width: "100%", height }}>
        <ResponsiveContainer>
          <ScatterChart margin={{ top: 8, right: 16, bottom: 24, left: 0 }}>
            <CartesianGrid stroke={VIZ.grid} strokeDasharray="3 3" />
            <XAxis type="number" dataKey="x" name="Map axis 1" tick={{ fontSize: 10, fill: VIZ.axis }}
              label={{ value: "Cohort map axis 1", position: "insideBottom", offset: -12, fontSize: 11, fill: VIZ.axis }} />
            <YAxis type="number" dataKey="y" name="Map axis 2" tick={{ fontSize: 10, fill: VIZ.axis }} width={36} />
            <ZAxis range={[18, 18]} />
            <Tooltip content={tooltip} cursor={{ strokeDasharray: "3 3" }} />
            <Legend verticalAlign="top" height={24} wrapperStyle={{ fontSize: 12 }} />
            <Scatter name="Other people in the synthetic cohort" data={rest} fill={VIZ.context} fillOpacity={0.45} isAnimationActive={false} />
            <Scatter name={highlightName} data={highlight} fill={highlightColor} fillOpacity={0.55} isAnimationActive={false} />
            {position && (
              <Scatter
                name="You"
                data={[{ ...position, you: true }]}
                fill={COLORS.ink}
                shape={(props) => (
                  <g>
                    <circle cx={props.cx} cy={props.cy} r={9} fill="#fff" />
                    <circle cx={props.cx} cy={props.cy} r={6.5} fill={COLORS.ink} />
                  </g>
                )}
                isAnimationActive={false}
              />
            )}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function Box({ children }) {
  return (
    <div className="rounded-xl border bg-white shadow p-2.5 text-xs max-w-[240px]" style={{ borderColor: COLORS.line, color: COLORS.ink }}>
      {children}
    </div>
  );
}

function Toggle({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className="px-2.5 py-1 rounded-full text-xs font-medium border"
      style={{
        borderColor: active ? COLORS.teal : COLORS.line,
        backgroundColor: active ? COLORS.tealSoft : "white",
        color: active ? COLORS.teal : COLORS.slate,
      }}
    >
      {children}
    </button>
  );
}

export default CohortScatter;
