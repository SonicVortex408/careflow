import React, { useState } from "react";
import { COLORS } from "../styles/tokens.js";
import { AlertsList } from "../components/dashboard/Alerts.jsx";

export function Alerts({ alerts, onResolve, onDismiss }) {
  const [tab, setTab] = useState("active");

  return (
    <div className="p-4 sm:p-6 space-y-5">
      <div>
        <h1 className="text-lg font-semibold" style={{ color: COLORS.ink }}>Alerts &amp; Recommendations</h1>
        <p className="text-sm" style={{ color: COLORS.slate }}>Operational alerts generated from live queue and resource data</p>
      </div>

      <div className="flex gap-2 border-b" style={{ borderColor: COLORS.line }}>
        {[{ key: "active", label: "Active" }, { key: "resolved", label: "Resolved" }].map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)} className="px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition"
            style={{ borderColor: tab === t.key ? COLORS.teal : "transparent", color: tab === t.key ? COLORS.teal : COLORS.slate }}>
            {t.label}
          </button>
        ))}
      </div>

      <AlertsList alerts={alerts} tab={tab} onResolve={onResolve} onDismiss={onDismiss} />
    </div>
  );
}

export default Alerts;
