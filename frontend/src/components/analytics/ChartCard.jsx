import React from "react";
import { COLORS } from "../../styles/tokens.js";
import { Card } from "../shared/Card.jsx";

export function ChartCard({ title, children, subtitle }) {
  return (
    <Card className="p-5">
      <h3 className="text-sm font-semibold" style={{ color: COLORS.ink }}>{title}</h3>
      {subtitle && <p className="text-xs mb-1" style={{ color: COLORS.slate }}>{subtitle}</p>}
      <div className="mt-3" style={{ width: "100%", height: 260 }}>{children}</div>
    </Card>
  );
}

export default ChartCard;
