import React from "react";
import { BookOpen, HelpCircle } from "lucide-react";

import { COLORS } from "../../styles/tokens.js";
import { Pill } from "../shared/Badges.jsx";

/** Knowledge-graph evidence chains; unverified links are always labelled. */
export function EvidenceList({ evidence }) {
  const chains = evidence?.chains || [];
  if (!chains.length) {
    return <p className="text-sm" style={{ color: COLORS.slate }}>No knowledge-graph links were triggered by these results.</p>;
  }
  return (
    <ul className="space-y-3">
      {chains.map((c, i) => (
        <li key={i} className="rounded-xl border p-3" style={{ borderColor: COLORS.line }}>
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="text-sm font-semibold" style={{ color: COLORS.ink }}>{c.finding}</span>
            <span className="text-xs" style={{ color: COLORS.slate }}>{c.relation === "AMPLIFIES" ? "may add to" : "can be linked with"}</span>
            <span className="text-sm font-semibold" style={{ color: COLORS.ink }}>{c.condition}</span>
          </div>
          {c.symptoms?.length > 0 && (
            <p className="text-xs mb-2" style={{ color: COLORS.slate }}>
              Can come with: {c.symptoms.map((s) => s.name.toLowerCase() + (s.reported ? " (you reported this)" : "")).join(", ")}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-2">
            {c.verified ? (
              <Pill tone="good" icon={BookOpen}>{c.edge.evidence_level.replace("_", " ")}</Pill>
            ) : (
              <Pill tone="warning" icon={HelpCircle}>Unverified link</Pill>
            )}
            <span className="text-[11px]" style={{ color: COLORS.slate }}>Source: {c.edge.source_title}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}

export default EvidenceList;
