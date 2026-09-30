import React from "react";
import {
  AlertOctagon,
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  CircleDashed,
  Clock,
  FlaskConical,
  Info,
  ShieldAlert,
  XCircle,
} from "lucide-react";

import { COLORS, VIZ } from "../../styles/tokens.js";
import { STATUS_META, SYNTHETIC_LABEL } from "../../utils/biomarkers.js";

const TONES = {
  good: { fg: "#0b7a0b", bg: COLORS.successSoft },
  warning: { fg: "#8a5a00", bg: "#FDF3DC" },
  serious: { fg: "#a8481f", bg: "#FCEBE3" },
  critical: { fg: VIZ.status.critical, bg: COLORS.criticalSoft },
  neutral: { fg: COLORS.slate, bg: "#F1F4F3" },
  info: { fg: COLORS.blue, bg: COLORS.blueSoft },
};

export function Pill({ tone = "neutral", icon: Icon, children, title }) {
  const t = TONES[tone] || TONES.neutral;
  return (
    <span
      title={title}
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap"
      style={{ backgroundColor: t.bg, color: t.fg }}
    >
      {Icon && <Icon className="w-3.5 h-3.5" aria-hidden="true" />}
      {children}
    </span>
  );
}

const STATUS_ICON = { low: ArrowDown, high: ArrowUp, borderline: AlertTriangle, in_range: CheckCircle2, unknown: CircleDashed };

export function MarkerStatusBadge({ status }) {
  const meta = STATUS_META[status] || STATUS_META.unknown;
  return <Pill tone={meta.tone} icon={STATUS_ICON[status]}>{meta.label}</Pill>;
}

const REPORT_STATUS = {
  processing: { tone: "info", icon: Clock, label: "Processing" },
  pending_clinician_review: { tone: "warning", icon: Clock, label: "Awaiting clinician review" },
  approved: { tone: "good", icon: CheckCircle2, label: "Reviewed" },
  rejected: { tone: "serious", icon: XCircle, label: "Not approved" },
  failed: { tone: "critical", icon: XCircle, label: "Could not read" },
};

export function ReportStatusBadge({ status }) {
  const s = REPORT_STATUS[status] || REPORT_STATUS.processing;
  return <Pill tone={s.tone} icon={s.icon}>{s.label}</Pill>;
}

const ESCALATION = {
  routine: { tone: "neutral", icon: Info, label: "Routine" },
  priority: { tone: "warning", icon: AlertTriangle, label: "Priority" },
  urgent: { tone: "critical", icon: ShieldAlert, label: "Urgent" },
  emergency: { tone: "critical", icon: AlertOctagon, label: "Emergency" },
};

export function EscalationBadge({ level = "routine" }) {
  const e = ESCALATION[level] || ESCALATION.routine;
  return <Pill tone={e.tone} icon={e.icon}>{e.label}</Pill>;
}

/** Required on every view that shows cohort-derived analytics. */
export function SyntheticDataNotice({ compact = false }) {
  if (compact) {
    return (
      <Pill tone="info" icon={FlaskConical} title={SYNTHETIC_LABEL}>
        Synthetic cohort
      </Pill>
    );
  }
  return (
    <div
      role="note"
      className="flex items-start gap-2 rounded-xl px-3.5 py-2.5 text-xs"
      style={{ backgroundColor: COLORS.blueSoft, color: COLORS.blue }}
    >
      <FlaskConical className="w-4 h-4 mt-0.5 shrink-0" aria-hidden="true" />
      <span>
        <strong>Cohort comparisons are {SYNTHETIC_LABEL.charAt(0).toLowerCase() + SYNTHETIC_LABEL.slice(1)}</strong>{" "}
        Functional ranges, groups, percentiles and risk scores are research outputs.
      </span>
    </div>
  );
}

export default Pill;
