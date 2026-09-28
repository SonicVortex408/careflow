import React from "react";
import { X } from "lucide-react";
import { COLORS } from "../../styles/tokens.js";
import { Card } from "../shared/Card.jsx";
import { PriorityBadge, StatusPill } from "../shared/Badges.jsx";
import { priorityScore } from "../../utils/queueLogic.js";

export function PatientDetails({ patient, departments, onClose, onAction }) {
  if (!patient) return null;
  const dept = departments.find((d) => d.name === patient.department);
  const score = priorityScore(patient, dept);
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} aria-hidden="true" />
      <div role="dialog" aria-modal="true" aria-label={`Details for ${patient.name}`} className="relative bg-white w-full sm:max-w-md h-full overflow-y-auto shadow-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b sticky top-0 bg-white z-10" style={{ borderColor: COLORS.line }}>
          <h2 className="text-base font-semibold" style={{ color: COLORS.ink }}>Patient Details</h2>
          <button onClick={onClose} aria-label="Close" className="p-1.5 rounded-lg hover:bg-slate-100"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-5 space-y-5">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-lg font-bold" style={{ color: COLORS.ink }}>{patient.name}</div>
              <div className="text-sm" style={{ color: COLORS.slate }}>#{patient.id} · Age {patient.age}</div>
            </div>
            <PriorityBadge priority={patient.priority} />
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm">
            {[
              ["Department", patient.department], ["Appointment", patient.appointment],
              ["Arrival time", patient.arrivalTime], ["Assigned doctor", patient.doctor],
              ["Queue position", `${Math.max(1, Math.round(patient.waitTime / 5))}`], ["Est. wait", `${patient.waitTime} min`],
            ].map(([label, val]) => (
              <div key={label} className="p-3 rounded-xl" style={{ backgroundColor: "#F7F9F8" }}>
                <div className="text-xs mb-0.5" style={{ color: COLORS.slate }}>{label}</div>
                <div className="font-medium" style={{ color: COLORS.ink }}>{val}</div>
              </div>
            ))}
          </div>

          <div>
            <div className="text-xs mb-1.5" style={{ color: COLORS.slate }}>Status</div>
            <StatusPill status={patient.status} />
          </div>

          {patient.symptoms && (
            <div>
              <div className="text-xs mb-1" style={{ color: COLORS.slate }}>Reason for visit</div>
              <p className="text-sm" style={{ color: COLORS.ink }}>{patient.symptoms}</p>
            </div>
          )}

          <Card className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold" style={{ color: COLORS.ink }}>Priority Score</span>
              <span className="text-lg font-bold" style={{ color: COLORS.teal }}>{score.total}</span>
            </div>
            <div className="space-y-1.5 text-xs" style={{ color: COLORS.slate }}>
              <div className="flex justify-between"><span>Medical urgency</span><span>+{score.urgency}</span></div>
              <div className="flex justify-between"><span>Waiting duration</span><span>+{score.waitScore}</span></div>
              <div className="flex justify-between"><span>Appointment status</span><span>+{score.apptFactor}</span></div>
              <div className="flex justify-between"><span>Resource availability</span><span>+{score.resourceFactor}</span></div>
            </div>
            <p className="text-xs mt-3 pt-3 border-t" style={{ color: COLORS.slate, borderColor: COLORS.line }}>
              Prototype prioritization logic for demonstration purposes. It does not replace clinical triage or professional medical judgment.
            </p>
          </Card>

          <div>
            <h3 className="text-sm font-semibold mb-3" style={{ color: COLORS.ink }}>Timeline</h3>
            <ul className="space-y-3">
              {(patient.timeline || []).map((t, i) => (
                <li key={i} className="flex gap-3 text-sm">
                  <span className="w-16 shrink-0 font-medium" style={{ color: COLORS.slate }}>{t.time}</span>
                  <span style={{ color: COLORS.ink }}>{t.label}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-2">
            <button onClick={() => onAction("serve", patient)} className="rounded-xl py-2.5 text-sm font-semibold text-white" style={{ backgroundColor: COLORS.teal }}>Mark being served</button>
            <button onClick={() => onAction("complete", patient)} className="rounded-xl py-2.5 text-sm font-semibold border" style={{ borderColor: COLORS.line, color: COLORS.ink }}>Mark completed</button>
            <button onClick={() => onAction("escalate", patient)} className="rounded-xl py-2.5 text-sm font-semibold border" style={{ borderColor: COLORS.critical, color: COLORS.critical }}>Escalate</button>
            <button onClick={() => onAction("transfer", patient)} className="rounded-xl py-2.5 text-sm font-semibold border" style={{ borderColor: COLORS.line, color: COLORS.ink }}>Transfer dept.</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PatientDetails;
