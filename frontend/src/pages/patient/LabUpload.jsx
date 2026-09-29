import React, { useEffect, useRef, useState } from "react";
import { CheckCircle2, FileUp, Loader2, UploadCloud, XCircle } from "lucide-react";

import { COLORS } from "../../styles/tokens.js";
import { MAX_REPORT_BYTES, REPORT_FILE_TYPES, listReports, pollReport, uploadReport } from "../../services/reportService.js";
import { Card } from "../../components/shared/Card.jsx";
import { ReportStatusBadge } from "../../components/shared/Badges.jsx";

const STEPS = [
  { key: "upload", label: "Uploaded" },
  { key: "processing", label: "Reading and checking values" },
  { key: "pending_clinician_review", label: "Waiting for clinician review" },
];

export function validateReportFile(file) {
  if (!file) return "Choose a file first.";
  if (!REPORT_FILE_TYPES.includes(file.type)) return "Please upload a PDF, image (PNG/JPEG) or text file.";
  if (file.size > MAX_REPORT_BYTES) return "The file must be 10 MB or less.";
  return "";
}

export function LabUpload({ onNavigate }) {
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [phase, setPhase] = useState(null); // upload | processing | pending_clinician_review | failed
  const [message, setMessage] = useState("");
  const [history, setHistory] = useState([]);
  const inputRef = useRef(null);
  const abortRef = useRef(null);

  const refresh = () => listReports().then(setHistory).catch(() => {});

  useEffect(() => {
    refresh();
    return () => abortRef.current?.abort();
  }, []);

  const choose = (f) => {
    setError(validateReportFile(f));
    setFile(f || null);
    setPhase(null);
  };

  const submit = async () => {
    const problem = validateReportFile(file);
    if (problem) return setError(problem);
    setError("");
    setPhase("upload");
    try {
      const { report_id: reportId } = await uploadReport(file);
      setPhase("processing");
      abortRef.current = new AbortController();
      const report = await pollReport(reportId, {
        signal: abortRef.current.signal,
        onUpdate: (r) => setMessage(r.statusMessage),
      });
      setPhase(report.status);
      setMessage(report.statusMessage);
      refresh();
    } catch (e) {
      if (e.name === "AbortError") return;
      setPhase("failed");
      setMessage(e.message);
    }
  };

  const activeIndex = STEPS.findIndex((s) => s.key === phase);

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto space-y-5">
      <header>
        <h1 className="text-2xl font-bold" style={{ color: COLORS.ink }}>Upload a lab report</h1>
        <p className="text-sm mt-1" style={{ color: COLORS.slate }}>
          We read thyroid (TSH, free T3, free T4, anti-TPO) and micronutrient (vitamin D, B12, ferritin, magnesium, zinc) results.
          Your latest symptom check-in is included so the summary can take it into account.
        </p>
      </header>

      <Card className="p-6">
        <label
          htmlFor="report-file"
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); choose(e.dataTransfer.files?.[0]); }}
          className="flex flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed p-8 cursor-pointer text-center"
          style={{ borderColor: COLORS.line, backgroundColor: COLORS.bg }}
        >
          <UploadCloud className="w-10 h-10" style={{ color: COLORS.teal }} aria-hidden="true" />
          <span className="text-sm font-semibold" style={{ color: COLORS.ink }}>{file ? file.name : "Drop your report here or click to choose"}</span>
          <span className="text-xs" style={{ color: COLORS.slate }}>PDF, PNG, JPEG or TXT · up to 10 MB</span>
          <input
            ref={inputRef}
            id="report-file"
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.txt,application/pdf,image/png,image/jpeg,text/plain"
            className="sr-only"
            onChange={(e) => { choose(e.target.files?.[0]); e.target.value = ""; }}
          />
        </label>

        {error && <p role="alert" className="mt-3 text-sm" style={{ color: COLORS.critical }}>{error}</p>}

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={submit}
            disabled={!file || phase === "upload" || phase === "processing"}
            className="inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
            style={{ backgroundColor: COLORS.teal }}
          >
            {phase === "upload" || phase === "processing" ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileUp className="w-4 h-4" />}
            Upload and analyse
          </button>
          <button type="button" onClick={() => onNavigate("symptoms")} className="text-sm font-medium hover:underline" style={{ color: COLORS.teal }}>
            Update my symptoms first
          </button>
        </div>

        {phase && (
          <ol className="mt-6 space-y-2" aria-live="polite">
            {phase === "failed" ? (
              <li className="flex items-center gap-2 text-sm" style={{ color: COLORS.critical }}>
                <XCircle className="w-4 h-4" /> {message || "Something went wrong."}
              </li>
            ) : (
              STEPS.map((s, i) => {
                const done = i < activeIndex || (i === activeIndex && s.key === "pending_clinician_review");
                const current = i === activeIndex && !done;
                return (
                  <li key={s.key} className="flex items-center gap-2 text-sm" style={{ color: done || current ? COLORS.ink : COLORS.slate }}>
                    {done ? <CheckCircle2 className="w-4 h-4" style={{ color: COLORS.success }} /> : current ? <Loader2 className="w-4 h-4 animate-spin" /> : <span className="w-4 h-4 rounded-full border" style={{ borderColor: COLORS.line }} />}
                    {s.label}
                  </li>
                );
              })
            )}
            {phase === "pending_clinician_review" && (
              <li className="text-sm pt-2" style={{ color: COLORS.slate }}>{message} We will show it on your dashboard once approved.</li>
            )}
          </ol>
        )}
      </Card>

      <Card className="p-5">
        <h2 className="text-base font-semibold mb-3" style={{ color: COLORS.ink }}>Your reports</h2>
        {history.length === 0 ? (
          <p className="text-sm" style={{ color: COLORS.slate }}>No reports yet.</p>
        ) : (
          <ul className="divide-y" style={{ borderColor: COLORS.line }}>
            {history.map((r) => (
              <li key={r.id} className="py-3 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="text-sm font-medium" style={{ color: COLORS.ink }}>{r.originalName}</div>
                  <div className="text-xs" style={{ color: COLORS.slate }}>{new Date(r.uploadedAt).toLocaleString()}</div>
                </div>
                <div className="flex items-center gap-3">
                  <ReportStatusBadge status={r.status} />
                  {r.status === "approved" && (
                    <button type="button" onClick={() => onNavigate("reports", r.id)} className="text-sm font-semibold hover:underline" style={{ color: COLORS.teal }}>View</button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

export default LabUpload;
