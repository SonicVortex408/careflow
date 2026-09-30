import React, { useEffect, useState } from "react";
import { AlertOctagon, ClipboardList, MessageSquareQuote } from "lucide-react";

import { COLORS } from "../../styles/tokens.js";
import { getInsight } from "../../services/insightService.js";
import { sortBands } from "../../utils/biomarkers.js";
import { Card } from "../shared/Card.jsx";
import { SyntheticDataNotice } from "../shared/Badges.jsx";
import { BiomarkerGauge, GaugeLegend } from "./BiomarkerGauge.jsx";
import { BiomarkerRadar } from "./BiomarkerRadar.jsx";
import { CohortScatter } from "./CohortScatter.jsx";
import { EvidenceList } from "./EvidenceList.jsx";
import { RiskPanel } from "./RiskPanel.jsx";

export function Section({ title, subtitle, children, right }) {
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-2 mb-4">
        <div>
          <h2 className="text-base font-semibold" style={{ color: COLORS.ink }}>{title}</h2>
          {subtitle && <p className="text-xs mt-0.5" style={{ color: COLORS.slate }}>{subtitle}</p>}
        </div>
        {right}
      </div>
      {children}
    </Card>
  );
}

export function SummaryText({ text }) {
  return (
    <div className="space-y-3 text-sm leading-relaxed" style={{ color: COLORS.ink }}>
      {String(text || "").split(/\n{2,}/).map((p, i) => <p key={i}>{p}</p>)}
    </div>
  );
}

/**
 * The patient-facing interpretation: summary, gauges, radar, cohort position,
 * symptom likelihood, evidence and the appointment guide.
 * `interpretation` is the (patient-serialised) approved interpretation.
 */
export function InterpretationView({ interpretation, clinicianComment }) {
  const [cohort, setCohort] = useState(null);
  const analytics = interpretation?.analytics || {};
  const bands = analytics.bands || {};
  const cluster = analytics.cluster;
  const escalation = interpretation?.escalation;

  useEffect(() => {
    let alive = true;
    getInsight("cohort").then((c) => alive && setCohort(c)).catch(() => {});
    return () => { alive = false; };
  }, []);

  return (
    <div className="space-y-5">
      {escalation?.required && ["urgent", "emergency"].includes(escalation.level) && (
        <div role="alert" className="flex items-start gap-3 rounded-2xl p-4" style={{ backgroundColor: COLORS.criticalSoft, color: COLORS.critical }}>
          <AlertOctagon className="w-5 h-5 shrink-0 mt-0.5" aria-hidden="true" />
          <div className="text-sm">
            <strong>Some results need prompt attention.</strong> Please contact your clinician today. If you feel very unwell, call your local emergency number.
          </div>
        </div>
      )}

      <Section title="Your summary" subtitle={interpretation?.summary?.editedByClinician ? "Reviewed and edited by your clinician" : "Reviewed by your clinician"}>
        <SummaryText text={interpretation?.summary?.text} />
        {clinicianComment && (
          <div className="mt-4 flex items-start gap-2 rounded-xl p-3 text-sm" style={{ backgroundColor: COLORS.tealSoft, color: COLORS.teal }}>
            <MessageSquareQuote className="w-4 h-4 mt-0.5 shrink-0" aria-hidden="true" />
            <span><strong>Note from your clinician:</strong> {clinicianComment}</span>
          </div>
        )}
      </Section>

      <SyntheticDataNotice />

      <Section title="Your results" subtitle="Standard lab range compared with the functional range found in the synthetic cohort" right={<GaugeLegend />}>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {sortBands(bands).map((b) => <BiomarkerGauge key={b.key} band={b} />)}
        </div>
      </Section>

      <div className="grid gap-5 xl:grid-cols-2">
        <Section title="Pattern across markers" subtitle="Each spoke is scaled to that marker's lab range">
          <BiomarkerRadar bands={bands} />
        </Section>
        <Section
          title="Where you sit in the cohort"
          subtitle={cluster ? `Closest group: ${cluster.name} (${Math.round(cluster.share_of_cohort * 100)}% of the synthetic cohort)` : "Cohort analytics unavailable"}
        >
          {cohort ? (
            <CohortScatter cohort={cohort} position={cluster?.position} clusterId={cluster?.id} clusterName={cluster?.name} />
          ) : (
            <p className="text-sm" style={{ color: COLORS.slate }}>Loading cohort map…</p>
          )}
        </Section>
      </div>

      {analytics.risk && (
        <Section title="Symptom likelihood" subtitle="Calibrated model estimates from the synthetic cohort, with the markers that shaped them">
          <RiskPanel risk={analytics.risk} />
        </Section>
      )}

      <Section title="Why these results may matter" subtitle="Evidence chains from the clinical knowledge graph">
        <EvidenceList evidence={interpretation?.evidence} />
      </Section>

      {interpretation?.appointmentGuide?.length > 0 && (
        <Section title="Questions for your next appointment" right={<ClipboardList className="w-5 h-5" style={{ color: COLORS.slate }} aria-hidden="true" />}>
          <ol className="list-decimal pl-5 space-y-1.5 text-sm" style={{ color: COLORS.ink }}>
            {interpretation.appointmentGuide.map((q, i) => <li key={i}>{q}</li>)}
          </ol>
          <button type="button" onClick={() => window.print()} className="mt-4 text-sm font-semibold hover:underline" style={{ color: COLORS.teal }}>
            Print this page for your visit
          </button>
        </Section>
      )}

      <p className="text-xs" style={{ color: COLORS.slate }}>{interpretation?.disclaimer}</p>
    </div>
  );
}

export default InterpretationView;
