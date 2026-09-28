import React, { useState } from "react";
import { Info } from "lucide-react";
import { COLORS } from "../styles/tokens.js";
import { Card } from "../components/shared/Card.jsx";

function Toggle({ checked, onChange, label, description }) {
  return (
    <div className="flex items-center justify-between py-3.5">
      <div className="pr-4">
        <div className="text-sm font-medium" style={{ color: COLORS.ink }}>{label}</div>
        {description && <div className="text-xs mt-0.5" style={{ color: COLORS.slate }}>{description}</div>}
      </div>
      <button
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={() => onChange(!checked)}
        className="w-11 h-6 rounded-full transition shrink-0 relative"
        style={{ backgroundColor: checked ? COLORS.teal : COLORS.line }}
      >
        <span className="absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all" style={{ left: checked ? 22 : 2 }} />
      </button>
    </div>
  );
}

export function Settings({ user }) {
  const [notifEnabled, setNotifEnabled] = useState(true);
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [autoAssign, setAutoAssign] = useState(false);
  const [compactView, setCompactView] = useState(false);
  const [threshold, setThreshold] = useState(75);

  return (
    <div className="p-4 sm:p-6 max-w-2xl space-y-6">
      <div>
        <h1 className="text-lg font-semibold" style={{ color: COLORS.ink }}>Settings</h1>
        <p className="text-sm" style={{ color: COLORS.slate }}>Manage your account and CareFlow preferences</p>
      </div>

      <Card className="p-5">
        <h2 className="text-sm font-semibold mb-4" style={{ color: COLORS.ink }}>Account</h2>
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full flex items-center justify-center text-sm font-bold text-white" style={{ backgroundColor: COLORS.blue }}>
            {(user?.name || "A U").split(" ").map((s) => s[0]).join("").slice(0, 2)}
          </div>
          <div>
            <div className="text-sm font-semibold" style={{ color: COLORS.ink }}>{user?.name || "Admin User"}</div>
            <div className="text-xs" style={{ color: COLORS.slate }}>{user?.email || "admin@careflow.hospital"}</div>
          </div>
        </div>
      </Card>

      <Card className="p-5 divide-y" style={{ borderColor: COLORS.line }}>
        <h2 className="text-sm font-semibold pb-3" style={{ color: COLORS.ink }}>Notifications</h2>
        <Toggle checked={notifEnabled} onChange={setNotifEnabled} label="In-app notifications" description="Show live alerts and updates in the header bell" />
        <Toggle checked={emailAlerts} onChange={setEmailAlerts} label="Email alerts" description="Send critical alerts to your registered email" />
      </Card>

      <Card className="p-5 divide-y" style={{ borderColor: COLORS.line }}>
        <h2 className="text-sm font-semibold pb-3" style={{ color: COLORS.ink }}>Queue behavior</h2>
        <Toggle checked={autoAssign} onChange={setAutoAssign} label="Auto-assign available doctors" description="Automatically suggest a doctor when one becomes free" />
        <Toggle checked={compactView} onChange={setCompactView} label="Compact queue view" description="Show more rows per screen in the patient table" />
        <div className="py-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium" style={{ color: COLORS.ink }}>High-workload alert threshold</span>
            <span className="text-sm font-semibold" style={{ color: COLORS.teal }}>{threshold}%</span>
          </div>
          <input type="range" min={50} max={95} value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} className="w-full" style={{ accentColor: COLORS.teal }} aria-label="High-workload alert threshold" />
        </div>
      </Card>

      <Card className="p-5" style={{ backgroundColor: COLORS.tealSoft, borderColor: "transparent" }}>
        <div className="flex gap-3">
          <Info className="w-5 h-5 shrink-0" style={{ color: COLORS.teal }} />
          <p className="text-sm" style={{ color: COLORS.ink }}>
            CareFlow provides operational estimates and queue-management recommendations. It does not diagnose patients, determine medical treatment, or replace clinical triage and professional medical judgment.
          </p>
        </div>
      </Card>
    </div>
  );
}

export default Settings;
