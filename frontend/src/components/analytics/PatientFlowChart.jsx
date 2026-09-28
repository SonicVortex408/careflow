import React from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { COLORS } from "../../styles/tokens.js";
import { ChartCard } from "./ChartCard.jsx";

export function PatientFlowChart({ data }) {
  return (
    <ChartCard title="Patient Flow" subtitle="Patients by stage, today">
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 10, top: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.line} horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 12, fill: COLORS.slate }} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="stage" tick={{ fontSize: 12, fill: COLORS.slate }} axisLine={false} tickLine={false} width={90} />
          <Tooltip contentStyle={{ borderRadius: 12, borderColor: COLORS.line, fontSize: 13 }} />
          <Bar dataKey="count" name="Patients" fill={COLORS.blue} radius={[0, 6, 6, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export default PatientFlowChart;
