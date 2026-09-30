import React from "react";
import { COLORS } from "../../styles/tokens.js";

export function ConfirmDialog({ open, title, message, confirmLabel = "Confirm", onConfirm, onCancel, danger }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/40" onClick={onCancel} aria-hidden="true" />
      <div role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" className="relative bg-white rounded-2xl w-full max-w-sm p-5 shadow-xl">
        <h2 id="confirm-title" className="text-base font-semibold mb-2" style={{ color: COLORS.ink }}>{title}</h2>
        <p className="text-sm mb-5" style={{ color: COLORS.slate }}>{message}</p>
        <div className="flex gap-3">
          <button onClick={onCancel} className="flex-1 rounded-xl py-2.5 text-sm font-semibold border" style={{ borderColor: COLORS.line, color: COLORS.slate }}>Cancel</button>
          <button onClick={onConfirm} className="flex-1 rounded-xl py-2.5 text-sm font-semibold text-white" style={{ backgroundColor: danger ? COLORS.critical : COLORS.teal }}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmDialog;
