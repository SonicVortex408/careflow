import React, { useEffect, useState } from "react";
import { ArrowLeft, CheckCircle2, Loader2, Pencil, ShieldCheck, XCircle } from "lucide-react";

import { COLORS } from "../../styles/tokens.js";
import { getReview, submitReview } from "../../services/reviewService.js";
import { formatValue, sortBands } from "../../utils/biomarkers.js";
import { Card } from "../../components/shared/Card.jsx";
import { EscalationBadge, Pill, ReportStatusBadge, SyntheticDataNotice } from "../../components/shared/Badges.jsx";
import { BiomarkerGauge, GaugeLegend } from "../../components/biomarkers/BiomarkerGauge.jsx";
import { EvidenceList } from "../../components/biomarkers/EvidenceList.jsx";
import { Section, SummaryText } from "../../components/biomarkers/InterpretationView.jsx";
import { RiskPanel } from "../../components/biomarkers/RiskPanel.jsx";

const SEVERITY_TONE = { error: "critical", warning: "warning", info: "neutral" };

export function ReviewDetail({ reportId, onBack }) {
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [mode, setMode] = useState("approve");
  const [comment, setComment] = useState("");
  const [edited, setEdited] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getReview(reportId)
      .then((r) => { setReport(r); setEdited(r.interpretation?.summary?.text || ""); })
      .catch((e) => setError(e.message));
  }, [reportId]);

  if (error && !report) return <p role="alert" className="p-8 text-sm" style={{ color: COLORS.critical }}>{error}</p>;
  if (!report) return <div className="p-8"><Loader2 className="w-5 h-5 animate-spin" style={{ color: COLORS.slate }} /></div>;

  const i = report.interpretation || {};
  const extraction = i.extraction || {};
  const quality = extraction.quality || {};
  const pending = report.status === "pending_clinician_review";

  const decide = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const updated = await submitReview(report.id, { decision: mode, comment, editedSummary: mode === "edit" ? edited : undefined });
      setReport({ ...report, ...updated });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-5">
      <button type="button" onClick={onBack} className="inline-flex items-center gap-1 text-sm font-medium" style={{ color: COLORS.teal }}>
        <ArrowLeft className="w-4 h-4" /> Back to queue
      </button>

      <header className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-bold" style={{ color: COLORS.ink }}>{report.patient?.name} · {report.originalName}</h1>
        <ReportStatusBadge status={report.status} />
        <EscalationBadge level={report.escalationLevel} />
      </header>
      <p className="text-xs" style={{ color: COLORS.slate }}>
        Sex {report.patient?.sex || extraction.metadata?.sex || "unknown"} · Age {extraction.metadata?.age ?? (report.patient?.birthYear ? new Date().getFullYear() - report.patient.birthYear : "unknown")}
        {" · "}Lab {extraction.metadata?.lab_provider || "unknown"} · Collected {extraction.metadata?.collected_at || "unknown"}
        {" · "}OCR {extraction.ocr?.method || "—"}{extraction.ocr?.mean_confidence ? ` (${Math.round(extraction.ocr.mean_confidence * 100)}% conf.)` : ""}
      </p>

      {i.escalation?.reasons?.length > 0 && (
        <Section title="Escalation reasons" subtitle="Deterministic rules; thresholds are illustrative defaults to be configured by the clinical team">
          <ul className="space-y-1.5 text-sm" style={{ color: COLORS.ink }}>
            {i.escalation.reasons.map((r, idx) => (
              <li key={idx} className="flex flex-wrap items-center gap-2">
                <EscalationBadge level={r.level} /> {r.reason}{r.threshold ? ` (${r.threshold})` : ""}
                {r.evidence_level && <span className="text-xs" style={{ color: COLORS.slate }}>evidence: {r.evidence_level}</span>}
              </li>
            ))}
          </ul>
        </Section>
      )}

      <div className="grid gap-5 xl:grid-cols-2">
        <Section title="Extracted values" subtitle="Raw report values, normalised to LOINC + SI units, with extraction confidence">
          <div className="overflow-x-auto">
            <table className="w-full text-xs min-w-[520px]">
              <thead>
                <tr className="text-left border-b" style={{ color: COLORS.slate, borderColor: COLORS.line }}>
                  <th className="py-1.5 font-medium">Marker (LOINC)</th><th className="font-medium">On report</th><th className="font-medium">Normalised</th><th className="font-medium">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {(extraction.biomarkers || []).map((b) => (
                  <tr key={b.key} className="border-b last:border-0" style={{ borderColor: COLORS.line, color: COLORS.ink }}>
                    <td className="py-1.5">{b.display} <span style={{ color: COLORS.slate }}>({b.loinc})</span></td>
                    <td>{b.raw_label}: {b.raw_value} {b.raw_unit}</td>
                    <td className="tabular-nums">{formatValue(b.value)} {b.unit}</td>
                    <td>
                      {b.confidence < 0.75 ? <Pill tone="warning">{Math.round(b.confidence * 100)}% verify</Pill> : <span className="tabular-nums">{Math.round(b.confidence * 100)}%</span>}
                      {b.unit_inferred && <span className="ml-1"><Pill tone="warning">unit inferred</Pill></span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {quality.issues?.length > 0 && (
            <div className="mt-4">
              <div className="text-xs font-semibold mb-1.5" style={{ color: COLORS.ink }}>Data-quality checks · completeness {Math.round((quality.completeness || 0) * 100)}%</div>
              <ul className="space-y-1">
                {quality.issues.map((q, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-xs" style={{ color: COLORS.ink }}>
                    <Pill tone={SEVERITY_TONE[q.severity]}>{q.code.replace(/_/g, " ")}</Pill><span>{q.message}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Section>

        <Section
          title="Generated summary"
          subtitle={`Source: ${i.summary?.source || "—"} · reading grade ${i.summary?.readability_grade ?? "—"} · attempts ${i.summary?.attempts ?? 0}`}
          right={i.guardrails?.passed ? <Pill tone="good" icon={ShieldCheck}>Guardrails passed</Pill> : <Pill tone="warning" icon={ShieldCheck}>Guardrails redacted</Pill>}
        >
          {pending && mode === "edit" ? (
            <textarea value={edited} onChange={(e) => setEdited(e.target.value)} rows={16} className="w-full rounded-xl border p-3 text-sm" style={{ borderColor: COLORS.line }} aria-label="Edited summary" />
          ) : (
            <SummaryText text={report.review?.editedSummary || i.summary?.text} />
          )}
          {i.appointment_guide?.length > 0 && (
            <div className="mt-4">
              <div className="text-xs font-semibold mb-1" style={{ color: COLORS.ink }}>Appointment guide shown to the patient</div>
              <ol className="list-decimal pl-5 text-xs space-y-0.5" style={{ color: COLORS.ink }}>{i.appointment_guide.map((q, idx) => <li key={idx}>{q}</li>)}</ol>
            </div>
          )}
        </Section>
      </div>

      <SyntheticDataNotice />

      <Section title="Results vs ranges" right={<GaugeLegend />}>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {sortBands(i.analytics?.bands).map((b) => <BiomarkerGauge key={b.key} band={b} />)}
        </div>
      </Section>

      {i.analytics?.risk && (
        <Section title="Symptom likelihood + SHAP drivers" subtitle={i.analytics.cluster ? `Closest cohort group: ${i.analytics.cluster.name} (GMM certainty ${Math.round(i.analytics.cluster.gmm_certainty * 100)}%)` : ""}>
          <RiskPanel risk={i.analytics.risk} />
        </Section>
      )}

      <Section title="Knowledge-graph evidence" subtitle={`Backend: ${i.evidence?.backend || "—"}`}>
        <EvidenceList evidence={i.evidence} />
      </Section>

      <Section title="Guardrail audit trail">
        <ul className="text-xs space-y-1 font-mono" style={{ color: COLORS.slate }}>
          {(i.guardrails?.audit || []).map((a, idx) => <li key={idx}>{JSON.stringify(a)}</li>)}
        </ul>
      </Section>

      <Card className="p-5 sticky bottom-4 shadow-lg">
        {pending ? (
          <form onSubmit={decide} className="space-y-3">
            <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Decision">
              {[
                { key: "approve", label: "Approve", icon: CheckCircle2 },
                { key: "edit", label: "Edit & approve", icon: Pencil },
                { key: "reject", label: "Reject", icon: XCircle },
              ].map((d) => (
                <button key={d.key} type="button" role="radio" aria-checked={mode === d.key} onClick={() => setMode(d.key)}
                  className="inline-flex items-center gap-1.5 rounded-xl border px-3 py-2 text-sm font-medium"
                  style={{ borderColor: mode === d.key ? COLORS.teal : COLORS.line, backgroundColor: mode === d.key ? COLORS.tealSoft : "white", color: mode === d.key ? COLORS.teal : COLORS.ink }}>
                  <d.icon className="w-4 h-4" /> {d.label}
                </button>
              ))}
            </div>
            <textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={2} maxLength={4000}
              placeholder={mode === "reject" ? "Reason (required, shared with the patient)" : "Optional note to the patient"}
              className="w-full rounded-xl border p-3 text-sm" style={{ borderColor: COLORS.line }} aria-label="Comment" />
            {error && <p role="alert" className="text-sm" style={{ color: COLORS.critical }}>{error}</p>}
            <button type="submit" disabled={saving} className="inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
              style={{ backgroundColor: mode === "reject" ? COLORS.critical : COLORS.teal }}>
              {saving && <Loader2 className="w-4 h-4 animate-spin" />} Sign off: {mode === "reject" ? "reject" : "release to patient"}
            </button>
          </form>
        ) : (
          <p className="text-sm" style={{ color: COLORS.ink }}>
            {report.review ? `Decision "${report.review.decision}" by ${report.review.reviewerName} on ${new Date(report.review.reviewedAt).toLocaleString()}${report.review.comment ? ` — "${report.review.comment}"` : ""}` : `Status: ${report.status}`}
          </p>
        )}
      </Card>
    </div>
  );
}

export default ReviewDetail;
