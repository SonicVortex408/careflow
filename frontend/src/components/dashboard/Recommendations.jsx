import React from "react";
import { Zap } from "lucide-react";
import { COLORS } from "../../styles/tokens.js";
import { Card } from "../shared/Card.jsx";

export function RecommendationCard({ recommendation, onDismiss }) {
  if (!recommendation) return null;
  return (
    <Card className="p-5" style={{ backgroundColor: COLORS.tealSoft, borderColor: "transparent" }}>
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 bg-white">
          <Zap style={{ width: 18, height: 18, color: COLORS.teal }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold mb-1" style={{ color: COLORS.ink }}>CareFlow Recommendation</div>
          <p className="text-sm mb-3" style={{ color: COLORS.ink }}>{recommendation.message}</p>
          <div className="flex flex-wrap gap-2">
            <button className="text-xs font-semibold px-3 py-1.5 rounded-lg text-white" style={{ backgroundColor: COLORS.teal }}>Reassign available doctor</button>
            <button className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-white" style={{ color: COLORS.teal }}>Adjust queue routing</button>
            <button onClick={onDismiss} className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-white" style={{ color: COLORS.slate }}>Dismiss</button>
          </div>
        </div>
      </div>
    </Card>
  );
}

export default RecommendationCard;
