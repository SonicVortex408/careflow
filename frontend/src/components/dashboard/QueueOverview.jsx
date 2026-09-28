import React from "react";
import { ChevronRight } from "lucide-react";
import { COLORS } from "../../styles/tokens.js";
import { Card } from "../shared/Card.jsx";
import { PriorityBadge } from "../shared/Badges.jsx";
import { priorityScore } from "../../utils/queueLogic.js";

export function QueueOverview({ patients, departments, onSelectPatient, onNavigate }) {
  const waiting = patients.filter((p) => p.status !== "Completed");
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold" style={{ color: COLORS.ink }}>Intelligent Queue Overview</h3>
        <button onClick={() => onNavigate("patients")} className="text-xs font-medium flex items-center gap-1 hover:underline" style={{ color: COLORS.teal }}>
          View full queue <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
      <div className="space-y-3">
        {waiting.slice(0, 5).map((p) => {
          const dept = departments.find((d) => d.name === p.department);
          const score = priorityScore(p, dept).total;
          return (
            <button
              key={p.id}
              onClick={() => onSelectPatient(p)}
              className="w-full text-left flex items-center gap-3 p-3 rounded-xl border hover:border-slate-300 transition focus:outline-none focus-visible:ring-2"
              style={{ borderColor: COLORS.line, "--tw-ring-color": COLORS.teal }}
            >
              <div className="flex flex-col items-center justify-center w-12 h-12 rounded-xl shrink-0" style={{ backgroundColor: COLORS.tealSoft }}>
                <span className="text-sm font-bold" style={{ color: COLORS.teal }}>{score}</span>
                <span className="text-[9px] uppercase" style={{ color: COLORS.teal }}>score</span>
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold truncate" style={{ color: COLORS.ink }}>{p.name}</span>
                  <span className="text-xs shrink-0" style={{ color: COLORS.slate }}>#{p.id}</span>
                </div>
                <div className="text-xs truncate" style={{ color: COLORS.slate }}>{p.department} · {p.doctor}</div>
              </div>
              <div className="text-right shrink-0">
                <PriorityBadge priority={p.priority} />
                <div className="text-xs mt-1" style={{ color: COLORS.slate }}>{p.waitTime} min</div>
              </div>
            </button>
          );
        })}
      </div>
    </Card>
  );
}

export function QueueTimeline({ patients }) {
  const sorted = [...patients].filter((p) => p.status !== "Completed").sort((a, b) => a.waitTime - b.waitTime).slice(0, 6);
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold" style={{ color: COLORS.ink }}>Queue Timeline</h3>
        <span className="text-xs" style={{ color: COLORS.slate }}>Live order</span>
      </div>
      <div className="relative pl-4">
        <div className="absolute left-[7px] top-1 bottom-1 w-px" style={{ backgroundColor: COLORS.line }} />
        <div className="flex items-center gap-2 mb-4 relative">
          <span className="absolute -left-4 w-3.5 h-3.5 rounded-full ring-4" style={{ backgroundColor: COLORS.teal, ringColor: COLORS.tealSoft }} />
          <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: COLORS.teal }}>Now</span>
        </div>
        <ul className="space-y-4">
          {sorted.map((p, i) => (
            <li key={p.id} className="relative flex items-center justify-between gap-3">
              <span className="absolute -left-4 w-3 h-3 rounded-full" style={{ backgroundColor: i === 0 ? COLORS.critical : COLORS.slate, opacity: i === 0 ? 1 : 0.5 }} />
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-sm font-medium truncate" style={{ color: COLORS.ink }}>#{p.id}</span>
                <span className="text-sm truncate" style={{ color: COLORS.slate }}>{p.name}</span>
                {i === 0 && <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded" style={{ backgroundColor: COLORS.criticalSoft, color: COLORS.critical }}>Serving</span>}
              </div>
              <span className="text-sm font-semibold shrink-0" style={{ color: COLORS.slate }}>{p.waitTime} min</span>
            </li>
          ))}
        </ul>
      </div>
    </Card>
  );
}
