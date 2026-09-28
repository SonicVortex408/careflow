import React from "react";
import { Activity } from "lucide-react";
import { COLORS } from "../../styles/tokens.js";

/* Brand mark: a small heartbeat / vitals line, the app's signature motif */
export function Vitals({ w = 64, h = 20, color = COLORS.teal, animated = true }) {
  return (
    <svg width={w} height={h} viewBox="0 0 120 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <polyline
        points="0,16 22,16 30,4 38,28 46,10 54,16 120,16"
        stroke={color}
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
        style={animated ? { strokeDasharray: 200, strokeDashoffset: 200, animation: "vitals-draw 2.4s ease-in-out infinite" } : {}}
      />
      <style>{`@keyframes vitals-draw { 0% { stroke-dashoffset: 200; } 55% { stroke-dashoffset: 0; } 100% { stroke-dashoffset: 0; } }`}</style>
    </svg>
  );
}

export function Logo({ size = "md" }) {
  const big = size === "lg";
  return (
    <div className="flex items-center gap-2.5">
      <div
        className="flex items-center justify-center rounded-xl shrink-0"
        style={{ width: big ? 44 : 34, height: big ? 44 : 34, backgroundColor: COLORS.teal }}
      >
        <Activity className="text-white" style={{ width: big ? 24 : 18, height: big ? 24 : 18 }} strokeWidth={2.4} />
      </div>
      <div>
        <div className={`font-bold tracking-tight ${big ? "text-2xl" : "text-lg"}`} style={{ color: COLORS.ink }}>CareFlow</div>
        {big && <div className="text-sm" style={{ color: COLORS.slate }}>Smart Hospital Queue &amp; Resource Management</div>}
      </div>
    </div>
  );
}
