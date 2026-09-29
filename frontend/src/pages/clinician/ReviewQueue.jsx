import React, { useEffect, useState } from "react";
import { AlertTriangle, Loader2, RefreshCw } from "lucide-react";

import { COLORS } from "../../styles/tokens.js";
import { listReviews } from "../../services/reviewService.js";
import { Card } from "../../components/shared/Card.jsx";
import { EscalationBadge, Pill, ReportStatusBadge } from "../../components/shared/Badges.jsx";

const TABS = [
  { key: "pending_clinician_review", label: "Awaiting review" },
  { key: "approved", label: "Approved" },
  { key: "rejected", label: "Rejected" },
  { key: "failed", label: "Failed" },
];

export function ReviewQueue({ onOpen, escalationsOnly = false }) {
  const [tab, setTab] = useState("pending_clinician_review");
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");

  const load = () => {
    setItems(null);
    setError("");
    listReviews(tab).then(setItems).catch((e) => setError(e.message));
  };

  useEffect(load, [tab]);

  const shown = (items || []).filter((r) => !escalationsOnly || r.escalationLevel !== "routine");

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: COLORS.ink }}>{escalationsOnly ? "Escalations" : "Review queue"}</h1>
          <p className="text-sm mt-1" style={{ color: COLORS.slate }}>
            {escalationsOnly
              ? "Reports whose values or symptoms triggered a deterministic escalation rule."
              : "No interpretation reaches a patient until a clinician approves it. Most urgent first."}
          </p>
        </div>
        <button type="button" onClick={load} className="inline-flex items-center gap-1.5 rounded-xl border px-3 py-2 text-sm" style={{ borderColor: COLORS.line, color: COLORS.ink }}>
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </header>

      <div className="flex flex-wrap gap-2" role="tablist">
        {TABS.map((t) => (
          <button key={t.key} role="tab" aria-selected={tab === t.key} type="button" onClick={() => setTab(t.key)}
            className="rounded-full px-3 py-1.5 text-sm font-medium border"
            style={{ borderColor: tab === t.key ? COLORS.teal : COLORS.line, backgroundColor: tab === t.key ? COLORS.tealSoft : "white", color: tab === t.key ? COLORS.teal : COLORS.slate }}>
            {t.label}
          </button>
        ))}
      </div>

      {error && <p role="alert" className="text-sm" style={{ color: COLORS.critical }}>{error}</p>}
      {items === null && !error && <Loader2 className="w-5 h-5 animate-spin" style={{ color: COLORS.slate }} />}

      <Card className="overflow-x-auto">
        <table className="w-full text-sm min-w-[720px]">
          <thead>
            <tr className="text-left text-xs border-b" style={{ color: COLORS.slate, borderColor: COLORS.line }}>
              <th className="p-3 font-medium">Escalation</th>
              <th className="p-3 font-medium">Patient</th>
              <th className="p-3 font-medium">Report</th>
              <th className="p-3 font-medium">Markers</th>
              <th className="p-3 font-medium">Data quality</th>
              <th className="p-3 font-medium">Uploaded</th>
              <th className="p-3" />
            </tr>
          </thead>
          <tbody>
            {shown.length === 0 && items !== null && (
              <tr><td colSpan={7} className="p-6 text-center" style={{ color: COLORS.slate }}>Nothing here.</td></tr>
            )}
            {shown.map((r) => (
              <tr key={r.id} className="border-b last:border-0 hover:bg-slate-50" style={{ borderColor: COLORS.line, color: COLORS.ink }}>
                <td className="p-3"><EscalationBadge level={r.escalationLevel} /></td>
                <td className="p-3 font-medium">{r.patient?.name || "—"}</td>
                <td className="p-3">
                  <div>{r.originalName}</div>
                  {tab !== "pending_clinician_review" && <ReportStatusBadge status={r.status} />}
                </td>
                <td className="p-3 tabular-nums">{r.markersFound}/9</td>
                <td className="p-3">{r.qualityNeedsAttention ? <Pill tone="warning" icon={AlertTriangle}>Check values</Pill> : <span style={{ color: COLORS.slate }}>OK</span>}</td>
                <td className="p-3 whitespace-nowrap" style={{ color: COLORS.slate }}>{new Date(r.uploadedAt).toLocaleString()}</td>
                <td className="p-3 text-right">
                  <button type="button" onClick={() => onOpen(r.id)} className="rounded-lg px-3 py-1.5 text-sm font-semibold text-white" style={{ backgroundColor: COLORS.teal }}>
                    {tab === "pending_clinician_review" ? "Review" : "Open"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

export default ReviewQueue;
