import React, { useMemo } from "react";
import { Sparkles } from "lucide-react";
import { COLORS } from "../../styles/tokens.js";
import { Card } from "../shared/Card.jsx";
import { predictWait } from "../../utils/queueLogic.js";

export function WaitingPrediction({ dept }) {
  const pred = useMemo(() => predictWait(dept, dept?.queue ? Math.round(dept.queue / 4) : 3), [dept]);
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-sm font-semibold" style={{ color: COLORS.ink }}>Predicted Waiting Time</h3>
        <span className="inline-flex items-center gap-1 text-xs font-medium" style={{ color: COLORS.teal }}>
          <Sparkles className="w-3.5 h-3.5" /> AI estimate
        </span>
      </div>
      <div className="flex items-end gap-6 mt-3 mb-4">
        <div>
          <div className="text-3xl font-bold" style={{ color: COLORS.ink }}>{pred.estimate} min</div>
          <div className="text-xs" style={{ color: COLORS.slate }}>Estimated wait — {dept?.name || "Hospital-wide"}</div>
        </div>
        <div>
          <div className="text-3xl font-bold" style={{ color: COLORS.teal }}>{pred.confidence}%</div>
          <div className="text-xs" style={{ color: COLORS.slate }}>Confidence</div>
        </div>
      </div>
      <div className="space-y-2">
        {[
          { label: "Queue size", val: pred.queueFactor },
          { label: "Doctor availability", val: pred.doctorFactor },
          { label: "Department load", val: pred.loadFactor },
          { label: "Priority patients", val: pred.priorityFactor },
        ].map((f) => (
          <div key={f.label} className="flex items-center justify-between text-sm">
            <span style={{ color: COLORS.slate }}>{f.label}</span>
            <span className="font-semibold" style={{ color: f.val >= 0 ? COLORS.critical : COLORS.success }}>{f.val >= 0 ? `+${f.val}` : f.val} min</span>
          </div>
        ))}
      </div>
      <p className="text-xs mt-4 pt-4 border-t" style={{ color: COLORS.slate, borderColor: COLORS.line }}>
        Waiting times are estimates and may change based on patient priority, emergencies, and resource availability.
      </p>
    </Card>
  );
}

export default WaitingPrediction;
