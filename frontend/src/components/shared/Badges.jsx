import React from "react";
import { ShieldAlert, AlertTriangle, Info, CheckCircle2, UserCheck, Stethoscope, Coffee, UserX } from "lucide-react";
import { COLORS } from "../../styles/tokens.js";

export const PRIORITY_STYLE = {
  Critical: { bg: COLORS.criticalSoft, fg: COLORS.critical, icon: ShieldAlert },
  High: { bg: COLORS.warningSoft, fg: COLORS.warning, icon: AlertTriangle },
  Medium: { bg: COLORS.blueSoft, fg: COLORS.blue, icon: Info },
  Low: { bg: COLORS.successSoft, fg: COLORS.success, icon: CheckCircle2 },
};

export function PriorityBadge({ priority, showIcon = true }) {
  const s = PRIORITY_STYLE[priority] || PRIORITY_STYLE.Low;
  const Icon = s.icon;
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
      style={{ backgroundColor: s.bg, color: s.fg }}
    >
      {showIcon && <Icon className="w-3.5 h-3.5" aria-hidden="true" />}
      {priority}
    </span>
  );
}

const STATUS_STYLE = {
  Waiting: { bg: "#F1F4F3", fg: COLORS.slate },
  "Being evaluated": { bg: COLORS.blueSoft, fg: COLORS.blue },
  Completed: { bg: COLORS.successSoft, fg: COLORS.success },
  Escalated: { bg: COLORS.criticalSoft, fg: COLORS.critical },
};

export function StatusPill({ status }) {
  const s = STATUS_STYLE[status] || STATUS_STYLE.Waiting;
  return (
    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium" style={{ backgroundColor: s.bg, color: s.fg }}>
      {status}
    </span>
  );
}

export function WorkloadTag({ status }) {
  const map = {
    Low: { bg: COLORS.successSoft, fg: COLORS.success },
    Moderate: { bg: COLORS.blueSoft, fg: COLORS.blue },
    High: { bg: COLORS.warningSoft, fg: COLORS.warning },
    Critical: { bg: COLORS.criticalSoft, fg: COLORS.critical },
  };
  const s = map[status] || map.Low;
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold" style={{ backgroundColor: s.bg, color: s.fg }}>
      {status}
    </span>
  );
}

export function DoctorStatusPill({ status }) {
  const map = {
    Available: { bg: COLORS.successSoft, fg: COLORS.success, icon: UserCheck },
    Consulting: { bg: COLORS.blueSoft, fg: COLORS.blue, icon: Stethoscope },
    "On Break": { bg: COLORS.warningSoft, fg: COLORS.warning, icon: Coffee },
    Unavailable: { bg: "#F1F4F3", fg: COLORS.slate, icon: UserX },
  };
  const s = map[status] || map.Available;
  const Icon = s.icon;
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold" style={{ backgroundColor: s.bg, color: s.fg }}>
      <Icon className="w-3.5 h-3.5" aria-hidden="true" />
      {status}
    </span>
  );
}
