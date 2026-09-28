import React from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { COLORS } from "../../styles/tokens.js";
import { ChartCard } from "./ChartCard.jsx";

export function WaitingTimeChart({ data }) {
  return (
    <ChartCard title="Average Waiting Time" subtitle="Minutes, by hour">
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ left: -20, top: 5 }}>
          <defs>
            <linearGradient id="waitGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={COLORS.teal} stopOpacity={0.35} />
              <stop offset="95%" stopColor={COLORS.teal} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.line} vertical={false} />
          <XAxis dataKey="time" tick={{ fontSize: 12, fill: COLORS.slate }} axisLine={{ stroke: COLORS.line }} tickLine={false} />
          <YAxis tick={{ fontSize: 12, fill: COLORS.slate }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={{ borderRadius: 12, borderColor: COLORS.line, fontSize: 13 }} />
          <Area type="monotone" dataKey="wait" name="Wait (min)" stroke={COLORS.teal} strokeWidth={2.5} fill="url(#waitGrad)" />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export default WaitingTimeChart;
