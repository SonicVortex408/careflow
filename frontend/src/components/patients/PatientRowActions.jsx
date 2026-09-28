import React, { useState, useRef, useEffect } from "react";
import { MoreVertical } from "lucide-react";
import { COLORS } from "../../styles/tokens.js";

export function PatientRowActions({ patient, onAction }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    function onClick(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false); }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);
  const actions = [
    { key: "serve", label: "Mark as being served" },
    { key: "complete", label: "Mark as completed" },
    { key: "escalate", label: "Escalate" },
    { key: "transfer", label: "Transfer department" },
  ];
  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen((v) => !v)} aria-label={`Actions for ${patient.name}`} aria-haspopup="menu" aria-expanded={open} className="p-1.5 rounded-lg hover:bg-slate-100">
        <MoreVertical className="w-4 h-4" style={{ color: COLORS.slate }} />
      </button>
      {open && (
        <div role="menu" className="absolute right-0 mt-1 w-52 bg-white rounded-xl border shadow-lg overflow-hidden z-10" style={{ borderColor: COLORS.line }}>
          {actions.map((a) => (
            <button key={a.key} role="menuitem" onClick={() => { onAction(a.key, patient); setOpen(false); }} className="w-full text-left px-3.5 py-2.5 text-sm hover:bg-slate-50" style={{ color: COLORS.ink }}>
              {a.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default PatientRowActions;
