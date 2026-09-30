import React from "react";
import { MessageSquare, Plus } from "lucide-react";

import { COLORS } from "../../styles/tokens.js";

export function ConversationList({ conversations, selectedId, onSelect, onNew, disabled }) {
  return (
    <aside className="lg:w-64 shrink-0 border-b lg:border-b-0 lg:border-r flex flex-col" style={{ borderColor: COLORS.line }}>
      <div className="p-3">
        <button type="button" onClick={onNew} disabled={disabled}
          className="w-full inline-flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
          style={{ backgroundColor: COLORS.teal }}>
          <Plus className="w-4 h-4" /> New chat
        </button>
      </div>
      <nav className="flex lg:flex-col gap-1 overflow-x-auto lg:overflow-y-auto px-3 pb-3 max-h-none lg:max-h-[70vh]" aria-label="Conversations">
        {conversations.length === 0 && <p className="text-xs px-1" style={{ color: COLORS.slate }}>No conversations yet.</p>}
        {conversations.map((c) => {
          const active = c.id === selectedId;
          return (
            <button key={c.id} type="button" onClick={() => onSelect(c)} aria-current={active ? "true" : undefined}
              className="flex items-center gap-2 rounded-lg px-3 py-2 text-left text-sm shrink-0 lg:shrink"
              style={{ backgroundColor: active ? COLORS.tealSoft : "transparent", color: active ? COLORS.teal : COLORS.ink }}>
              <MessageSquare className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span className="truncate max-w-[180px]">{c.title}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}

export default ConversationList;
