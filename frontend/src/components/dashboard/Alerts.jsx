import React from "react";
import { AlertTriangle, Info, CheckCheck, Trash2, CheckCircle2 } from "lucide-react";
import { COLORS } from "../../styles/tokens.js";
import { Card } from "../shared/Card.jsx";

export const ALERT_STYLE = {
  critical: { bg: COLORS.criticalSoft, fg: COLORS.critical, icon: AlertTriangle },
  warning: { bg: COLORS.warningSoft, fg: COLORS.warning, icon: AlertTriangle },
  info: { bg: COLORS.tealSoft, fg: COLORS.teal, icon: Info },
};

export function AlertsList({ alerts, tab, onResolve, onDismiss }) {
  const shown = alerts.filter((a) => (tab === "active" ? a.status === "active" : a.status === "resolved"));
  return (
    <div className="space-y-3">
      {shown.map((a) => {
        const s = ALERT_STYLE[a.severity] || ALERT_STYLE.info;
        const Icon = s.icon;
        return (
          <Card key={a.id} className="p-4 sm:p-5">
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style={{ backgroundColor: s.bg }}>
                <Icon style={{ width: 18, height: 18, color: s.fg }} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold" style={{ color: COLORS.ink }}>{a.title}</span>
                  {a.status === "resolved" && <span className="text-xs font-medium flex items-center gap-1" style={{ color: COLORS.success }}><CheckCheck className="w-3.5 h-3.5" /> Resolved</span>}
                </div>
                <p className="text-sm mt-0.5" style={{ color: COLORS.slate }}>{a.message}</p>
              </div>
              {a.status === "active" && (
                <div className="flex gap-2 shrink-0">
                  <button onClick={() => onResolve(a.id)} className="text-xs font-semibold px-3 py-1.5 rounded-lg text-white" style={{ backgroundColor: COLORS.teal }}>Resolve</button>
                  <button onClick={() => onDismiss(a.id)} aria-label="Dismiss alert" className="p-1.5 rounded-lg hover:bg-slate-100"><Trash2 className="w-4 h-4" style={{ color: COLORS.slate }} /></button>
                </div>
              )}
            </div>
          </Card>
        );
      })}
      {shown.length === 0 && (
        <Card className="p-10 text-center">
          <CheckCircle2 className="w-8 h-8 mx-auto mb-2" style={{ color: COLORS.success }} />
          <p className="text-sm" style={{ color: COLORS.slate }}>No {tab} alerts right now.</p>
        </Card>
      )}
    </div>
  );
}

export default AlertsList;
