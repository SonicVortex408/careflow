import React from "react";
import { TrendingUp, TrendingDown } from "lucide-react";
import { COLORS } from "../../styles/tokens.js";
import { Card } from "../shared/Card.jsx";

export function StatCard({ icon: Icon, label, value, sub, trend, trendDir, accent }) {
  return (
    <Card className="p-4 sm:p-5">
      <div className="flex items-start justify-between">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ backgroundColor: accent.soft }}>
          <Icon style={{ width: 18, height: 18, color: accent.fg }} />
        </div>
        {trend && (
          <span className="flex items-center gap-1 text-xs font-semibold" style={{ color: trendDir === "up" ? COLORS.critical : COLORS.success }}>
            {trendDir === "up" ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
            {trend}
          </span>
        )}
      </div>
      <div className="mt-3 text-2xl font-bold" style={{ color: COLORS.ink }}>{value}</div>
      <div className="text-sm" style={{ color: COLORS.slate }}>{label}</div>
      {sub && <div className="text-xs mt-1" style={{ color: COLORS.slate }}>{sub}</div>}
    </Card>
  );
}

export default StatCard;
