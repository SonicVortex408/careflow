import React from "react";
import { COLORS } from "../../styles/tokens.js";
import { PriorityBadge, StatusPill } from "../shared/Badges.jsx";
import { priorityScore } from "../../utils/queueLogic.js";
import { PatientRowActions } from "./PatientRowActions.jsx";

export function PatientTable({ patients, departments, onSelect, onAction }) {
  return (
    <div className="overflow-x-auto -mx-4 sm:mx-0">
      <table className="w-full text-sm min-w-[820px]">
        <thead>
          <tr className="text-left border-b" style={{ borderColor: COLORS.line }}>
            {["Patient", "Department", "Priority", "Arrival", "Wait", "Doctor", "Status", ""].map((h) => (
              <th key={h} scope="col" className="px-4 py-3 font-semibold text-xs uppercase tracking-wide" style={{ color: COLORS.slate }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {patients.map((p) => {
            const dept = departments.find((d) => d.name === p.department);
            const score = priorityScore(p, dept).total;
            return (
              <tr key={p.id} className="border-b hover:bg-slate-50 transition cursor-pointer" style={{ borderColor: COLORS.line }} onClick={() => onSelect(p)}>
                <td className="px-4 py-3">
                  <div className="font-medium" style={{ color: COLORS.ink }}>{p.name}</div>
                  <div className="text-xs" style={{ color: COLORS.slate }}>#{p.id} · Score {score}</div>
                </td>
                <td className="px-4 py-3" style={{ color: COLORS.slate }}>{p.department}</td>
                <td className="px-4 py-3"><PriorityBadge priority={p.priority} /></td>
                <td className="px-4 py-3" style={{ color: COLORS.slate }}>{p.arrivalTime}</td>
                <td className="px-4 py-3 font-medium" style={{ color: COLORS.ink }}>{p.waitTime} min</td>
                <td className="px-4 py-3" style={{ color: COLORS.slate }}>{p.doctor}</td>
                <td className="px-4 py-3"><StatusPill status={p.status} /></td>
                <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                  <PatientRowActions patient={p} onAction={onAction} />
                </td>
              </tr>
            );
          })}
          {patients.length === 0 && (
            <tr><td colSpan={8} className="px-4 py-10 text-center text-sm" style={{ color: COLORS.slate }}>No patients match the current filters.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default PatientTable;
