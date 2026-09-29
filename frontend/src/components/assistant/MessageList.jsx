import React, { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { AlertOctagon, Bot, Loader2 } from "lucide-react";

import { COLORS } from "../../styles/tokens.js";

const SUGGESTIONS = [
  "What does a low ferritin level mean?",
  "How are TSH and free T4 read together?",
  "Could my results be linked to tiredness?",
];

export function MessageList({ messages, loading, loadingMessages, onSuggestion }) {
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  if (loadingMessages) {
    return <div className="flex-1 flex items-center justify-center"><Loader2 className="w-5 h-5 animate-spin" style={{ color: COLORS.slate }} /></div>;
  }

  if (!messages.length) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
        <Bot className="w-10 h-10 mb-3" style={{ color: COLORS.teal }} aria-hidden="true" />
        <p className="text-sm font-semibold" style={{ color: COLORS.ink }}>Ask about your thyroid and micronutrient results</p>
        <p className="text-xs mt-1 mb-4 max-w-sm" style={{ color: COLORS.slate }}>Answers use reviewed reference material and your clinician-approved results. They are not a diagnosis.</p>
        <div className="flex flex-wrap justify-center gap-2">
          {SUGGESTIONS.map((s) => (
            <button key={s} type="button" onClick={() => onSuggestion(s)} className="rounded-full border px-3 py-1.5 text-xs" style={{ borderColor: COLORS.line, color: COLORS.ink }}>{s}</button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4" aria-live="polite">
      {messages.map((m) => {
        const mine = m.role === "user";
        const urgent = !mine && ["urgent", "emergency"].includes(m.escalation?.level);
        return (
          <div key={m._id || m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
            <div className="max-w-[85%] space-y-2">
              {urgent && (
                <div role="alert" className="flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold" style={{ backgroundColor: COLORS.criticalSoft, color: COLORS.critical }}>
                  <AlertOctagon className="w-4 h-4" aria-hidden="true" /> Please seek prompt care: see the first paragraph below.
                </div>
              )}
              <div
                className="rounded-2xl px-4 py-3 text-sm leading-relaxed prose prose-sm max-w-none"
                style={{ backgroundColor: mine ? COLORS.teal : COLORS.bg, color: mine ? "white" : COLORS.ink }}
              >
                {mine ? m.content : <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>}
              </div>
            </div>
          </div>
        );
      })}
      {loading && (
        <div className="flex items-center gap-2 text-sm" style={{ color: COLORS.slate }}>
          <Loader2 className="w-4 h-4 animate-spin" /> Checking reference material…
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}

export default MessageList;
