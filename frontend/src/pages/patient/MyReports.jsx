import React, { useEffect, useState } from "react";
import { ArrowLeft, Loader2 } from "lucide-react";

import { COLORS } from "../../styles/tokens.js";
import { getReport, listReports } from "../../services/reportService.js";
import { Card } from "../../components/shared/Card.jsx";
import { ReportStatusBadge } from "../../components/shared/Badges.jsx";
import { InterpretationView } from "../../components/biomarkers/InterpretationView.jsx";

export function MyReports({ selectedId, onSelect }) {
  const [reports, setReports] = useState(null);
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => { listReports().then(setReports).catch((e) => setError(e.message)); }, []);

  useEffect(() => {
    if (!selectedId) return setDetail(null);
    setDetail("loading");
    getReport(selectedId).then(setDetail).catch((e) => { setError(e.message); setDetail(null); });
  }, [selectedId]);

  if (detail && detail !== "loading") {
    return (
      <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-4">
        <button type="button" onClick={() => onSelect(null)} className="inline-flex items-center gap-1 text-sm font-medium" style={{ color: COLORS.teal }}>
          <ArrowLeft className="w-4 h-4" /> All reports
        </button>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-bold" style={{ color: COLORS.ink }}>{detail.originalName}</h1>
          <ReportStatusBadge status={detail.status} />
        </div>
        {detail.interpretation ? (
          <InterpretationView interpretation={detail.interpretation} clinicianComment={detail.clinicianComment} />
        ) : (
          <Card className="p-6 text-sm" style={{ color: COLORS.slate }}>{detail.statusMessage}</Card>
        )}
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto space-y-5">
      <h1 className="text-2xl font-bold" style={{ color: COLORS.ink }}>My reports</h1>
      {error && <p role="alert" className="text-sm" style={{ color: COLORS.critical }}>{error}</p>}
      {(reports === null || detail === "loading") && <Loader2 className="w-5 h-5 animate-spin" style={{ color: COLORS.slate }} />}
      {reports?.length === 0 && <p className="text-sm" style={{ color: COLORS.slate }}>You have not uploaded any reports yet.</p>}
      <div className="space-y-3">
        {reports?.map((r) => (
          <Card key={r.id} className="p-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold" style={{ color: COLORS.ink }}>{r.originalName}</div>
              <div className="text-xs" style={{ color: COLORS.slate }}>{new Date(r.uploadedAt).toLocaleString()} · {r.statusMessage}</div>
            </div>
            <div className="flex items-center gap-3">
              <ReportStatusBadge status={r.status} />
              {r.status === "approved" && (
                <button type="button" onClick={() => onSelect(r.id)} className="text-sm font-semibold hover:underline" style={{ color: COLORS.teal }}>Open</button>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

export default MyReports;
