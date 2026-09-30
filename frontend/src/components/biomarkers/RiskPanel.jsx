import React from "react";
import { AlertTriangle, ArrowDownRight, ArrowUpRight, CheckCircle2, TrendingUp } from "lucide-react";

import { COLORS, VIZ } from "../../styles/tokens.js";
import { RISK_TONE } from "../../utils/biomarkers.js";
import { Pill } from "../shared/Badges.jsx";

const LEVEL_ICON = { low: CheckCircle2, moderate: AlertTriangle, high: TrendingUp };

/**
 * Calibrated symptom likelihood per target + the three biomarkers that pushed
 * the model most (TreeSHAP). Bars show magnitude; the arrow and words show
 * direction, so nothing relies on colour alone.
 */
export function RiskPanel({ risk }) {
  if (!risk) return null;
  const entries = Object.entries(risk);
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {entries.map(([key, r]) => {
        const maxAbs = Math.max(...r.drivers.map((d) => Math.abs(d.contribution)), 0.001);
        return (
          <div key={key} className="rounded-2xl border bg-white p-4" style={{ borderColor: COLORS.line }}>
            <div className="text-sm font-semibold mb-1" style={{ color: COLORS.ink }}>{r.label}</div>
            <div className="flex items-baseline gap-2 mb-2">
              <span className="text-3xl font-bold tabular-nums" style={{ color: COLORS.ink }}>{Math.round(r.probability * 100)}%</span>
              <Pill tone={RISK_TONE[r.level]} icon={LEVEL_ICON[r.level]}>{r.level} likelihood</Pill>
            </div>
            <p className="text-xs mb-3" style={{ color: COLORS.slate }}>
              In the synthetic cohort, {Math.round(r.cohort_prevalence * 100)}% overall report this.
            </p>
            {r.drivers.length > 0 && (
              <>
                <div className="text-xs font-semibold mb-1.5" style={{ color: COLORS.ink }}>What shaped this most</div>
                <ul className="space-y-1.5">
                  {r.drivers.map((d) => {
                    const Icon = d.direction === "raises" ? ArrowUpRight : ArrowDownRight;
                    return (
                      <li key={d.marker} className="text-xs" title={`SHAP contribution ${d.contribution.toFixed(2)} (log-odds)`}>
                        <div className="flex items-center justify-between gap-2" style={{ color: COLORS.ink }}>
                          <span className="inline-flex items-center gap-1"><Icon className="w-3.5 h-3.5" aria-hidden="true" />{d.display}</span>
                          <span style={{ color: COLORS.slate }}>{d.direction === "raises" ? "raises" : "lowers"}</span>
                        </div>
                        <div className="h-1.5 rounded-full mt-1" style={{ backgroundColor: VIZ.grid }}>
                          <div className="h-1.5 rounded-full" style={{ width: `${(Math.abs(d.contribution) / maxAbs) * 100}%`, backgroundColor: VIZ.series1 }} />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </>
            )}
            <p className="text-[11px] mt-3" style={{ color: COLORS.slate }}>Model AUROC {r.model_auroc.toFixed(2)} on held-out synthetic data.</p>
          </div>
        );
      })}
    </div>
  );
}

export default RiskPanel;
