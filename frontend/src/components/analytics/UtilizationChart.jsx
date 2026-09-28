import React from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { COLORS } from "../../styles/tokens.js";
import { ChartCard } from "./ChartCard.jsx";

export function UtilizationChart({ doctors }) {
  const data = doctors.filter((d) => d.status !== "Unavailable").map((d) => ({ name: d.name.replace("Dr. ", ""), load: d.load }));
  return (
    <ChartCard title="Doctor Utilization" subtitle="Consultation load per active doctor">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ left: -20, top: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.line} vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 10, fill: COLORS.slate }} axisLine={{ stroke: COLORS.line }} tickLine={false} interval={0} angle={-25} textAnchor="end" height={60} />
          <YAxis tick={{ fontSize: 12, fill: COLORS.slate }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={{ borderRadius: 12, borderColor: COLORS.line, fontSize: 13 }} />
          <Bar dataKey="load" name="Utilization %" radius={[6, 6, 0, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.load >= 80 ? COLORS.critical : d.load >= 55 ? COLORS.warning : COLORS.success} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export default UtilizationChart;
