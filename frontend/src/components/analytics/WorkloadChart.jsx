import React from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { COLORS } from "../../styles/tokens.js";
import { ChartCard } from "./ChartCard.jsx";

export function WorkloadChart({ departments }) {
  const data = departments.map((d) => ({ name: d.name.length > 10 ? d.name.slice(0, 9) + "…" : d.name, workload: d.workload }));
  return (
    <ChartCard title="Department Workload" subtitle="Percent utilization">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ left: -20, top: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.line} vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 11, fill: COLORS.slate }} axisLine={{ stroke: COLORS.line }} tickLine={false} />
          <YAxis tick={{ fontSize: 12, fill: COLORS.slate }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={{ borderRadius: 12, borderColor: COLORS.line, fontSize: 13 }} />
          <Bar dataKey="workload" name="Workload %" radius={[6, 6, 0, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.workload >= 80 ? COLORS.critical : d.workload >= 60 ? COLORS.warning : COLORS.teal} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export default WorkloadChart;
