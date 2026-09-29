import React, { useEffect, useState } from "react";
import { Activity, FileUp, Loader2 } from "lucide-react";

import { COLORS } from "../../styles/tokens.js";
import { getReport, listReports } from "../../services/reportService.js";
import { Card } from "../../components/shared/Card.jsx";
import { ReportStatusBadge } from "../../components/shared/Badges.jsx";
import { InterpretationView } from "../../components/biomarkers/InterpretationView.jsx";

export function PatientDashboard({ user, onNavigate }) {
  const [state, setState] = useState({ loading: true, error: "", reports: [], latest: null });

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const reports = await listReports();
        const approved = reports.find((r) => r.status === "approved");
        const latest = approved ? await getReport(approved.id) : null;
        if (alive) setState({ loading: false, error: "", reports, latest });
      } catch (error) {
        if (alive) setState({ loading: false, error: error.message, reports: [], latest: null });
      }
    })();
    return () => { alive = false; };
  }, []);

  const pending = state.reports.filter((r) => ["processing", "pending_clinician_review"].includes(r.status));

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-5">
      <header>
        <h1 className="text-2xl font-bold" style={{ color: COLORS.ink }}>Hello{user?.name ? `, ${user.name.split(" ")[0]}` : ""}</h1>
        <p className="text-sm mt-1" style={{ color: COLORS.slate }}>Your thyroid and micronutrient results, explained in plain language after a clinician has reviewed them.</p>
      </header>

      {state.loading && (
        <div className="flex items-center gap-2 text-sm" style={{ color: COLORS.slate }}>
          <Loader2 className="w-4 h-4 animate-spin" /> Loading your results…
        </div>
      )}
      {state.error && <p role="alert" className="text-sm" style={{ color: COLORS.critical }}>{state.error}</p>}

      {pending.length > 0 && (
        <Card className="p-4 flex flex-wrap items-center justify-between gap-3">
          <div className="text-sm" style={{ color: COLORS.ink }}>
            {pending.length === 1 ? "One report is" : `${pending.length} reports are`} on the way: <em>{pending[0].statusMessage}</em>
          </div>
          <ReportStatusBadge status={pending[0].status} />
        </Card>
      )}

      {!state.loading && !state.latest && (
        <Card className="p-8 text-center">
          <Activity className="w-10 h-10 mx-auto mb-3" style={{ color: COLORS.teal }} aria-hidden="true" />
          <h2 className="text-lg font-semibold" style={{ color: COLORS.ink }}>No reviewed results yet</h2>
          <p className="text-sm mt-1 mb-5 max-w-md mx-auto" style={{ color: COLORS.slate }}>
            Tell us how you have been feeling, then upload a lab report. A clinician checks every summary before you see it.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <button type="button" onClick={() => onNavigate("symptoms")} className="rounded-xl px-4 py-2.5 text-sm font-semibold border" style={{ borderColor: COLORS.line, color: COLORS.ink }}>
              Log symptoms
            </button>
            <button type="button" onClick={() => onNavigate("upload")} className="inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white" style={{ backgroundColor: COLORS.teal }}>
              <FileUp className="w-4 h-4" /> Upload a lab report
            </button>
          </div>
        </Card>
      )}

      {state.latest && (
        <>
          <p className="text-xs" style={{ color: COLORS.slate }}>
            Showing your latest reviewed report: {state.latest.originalName} · reviewed {new Date(state.latest.reviewedAt || state.latest.updatedAt).toLocaleDateString()}
          </p>
          <InterpretationView interpretation={state.latest.interpretation} clinicianComment={state.latest.clinicianComment} />
        </>
      )}
    </div>
  );
}

export default PatientDashboard;
