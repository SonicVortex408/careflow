import React, { useRef } from "react";
import { Loader2, Paperclip, Send } from "lucide-react";

import { COLORS } from "../../styles/tokens.js";

export function Composer({ value, onChange, onSend, disabled, canUpload, onUpload, uploading, uploadStatus }) {
  const fileRef = useRef(null);

  return (
    <div className="border-t p-3" style={{ borderColor: COLORS.line }}>
      {uploadStatus && (
        <p className="text-xs mb-2" style={{ color: uploadStatus.type === "error" ? COLORS.critical : COLORS.success }}>{uploadStatus.message}</p>
      )}
      <form onSubmit={(e) => { e.preventDefault(); onSend(); }} className="flex items-end gap-2">
        {canUpload && (
          <>
            <button type="button" onClick={() => fileRef.current?.click()} disabled={uploading} aria-label="Attach a medical document"
              className="p-2.5 rounded-xl border disabled:opacity-60" style={{ borderColor: COLORS.line, color: COLORS.slate }}>
              {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Paperclip className="w-4 h-4" />}
            </button>
            <input ref={fileRef} type="file" accept=".pdf,.txt,application/pdf,text/plain" className="sr-only"
              onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; if (f) onUpload(f); }} />
          </>
        )}
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onSend(); } }}
          rows={1}
          maxLength={4000}
          placeholder="Ask a question about your results…"
          aria-label="Message"
          className="flex-1 resize-none rounded-xl border px-3 py-2.5 text-sm max-h-40"
          style={{ borderColor: COLORS.line }}
        />
        <button type="submit" disabled={disabled || !value.trim()} aria-label="Send"
          className="p-2.5 rounded-xl text-white disabled:opacity-60" style={{ backgroundColor: COLORS.teal }}>
          <Send className="w-4 h-4" />
        </button>
      </form>
      <p className="text-[11px] mt-1.5" style={{ color: COLORS.slate }}>Answers are checked by automatic safety rules and are not medical advice.</p>
    </div>
  );
}

export default Composer;
