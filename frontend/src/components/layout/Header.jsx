import React, { useState, useEffect, useRef } from "react";
import { Menu, Search, Bell, X } from "lucide-react";
import { COLORS } from "../../styles/tokens.js";
import { PulseDot } from "../shared/PulseDot.jsx";

export function Header({ setMobileOpen, notifications, onMarkAllRead, onDismissNotif, search, setSearch, user }) {
  const [notifOpen, setNotifOpen] = useState(false);
  const unread = notifications.filter((n) => !n.read).length;
  const ref = useRef(null);

  useEffect(() => {
    function onClick(e) { if (ref.current && !ref.current.contains(e.target)) setNotifOpen(false); }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <header className="sticky top-0 z-30 bg-white border-b" style={{ borderColor: COLORS.line }}>
      <div className="flex items-center gap-3 px-4 sm:px-6 py-3">
        <button onClick={() => setMobileOpen(true)} aria-label="Open menu" className="lg:hidden p-2 -ml-2 rounded-lg hover:bg-slate-100">
          <Menu className="w-5 h-5" />
        </button>

        <div className="hidden sm:block">
          <div className="text-sm font-semibold" style={{ color: COLORS.ink }}>Smart Hospital Operations</div>
          <div className="flex items-center gap-1.5 text-xs" style={{ color: COLORS.success }}>
            <PulseDot color={COLORS.success} /> System Status: Operational
          </div>
        </div>

        <div className="flex-1 max-w-md ml-auto">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2" style={{ color: COLORS.slate }} />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search patients, doctors, IDs…"
              aria-label="Search"
              className="w-full rounded-xl border pl-9 pr-3 py-2 text-sm outline-none focus:ring-2 transition"
              style={{ borderColor: COLORS.line, "--tw-ring-color": COLORS.teal }}
            />
          </div>
        </div>

        <div className="relative" ref={ref}>
          <button
            onClick={() => setNotifOpen((v) => !v)}
            aria-label={`Notifications, ${unread} unread`}
            className="relative p-2 rounded-xl hover:bg-slate-100 transition"
          >
            <Bell className="w-5 h-5" style={{ color: COLORS.ink }} />
            {unread > 0 && (
              <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center text-[10px] font-bold rounded-full text-white" style={{ backgroundColor: COLORS.critical, minWidth: 16, height: 16 }}>
                {unread}
              </span>
            )}
          </button>
          {notifOpen && (
            <div role="menu" className="absolute right-0 mt-2 w-80 bg-white rounded-2xl border shadow-lg overflow-hidden" style={{ borderColor: COLORS.line }}>
              <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: COLORS.line }}>
                <span className="text-sm font-semibold" style={{ color: COLORS.ink }}>Notifications</span>
                <button onClick={onMarkAllRead} className="text-xs font-medium hover:underline" style={{ color: COLORS.teal }}>Mark all read</button>
              </div>
              <div className="max-h-80 overflow-y-auto">
                {notifications.length === 0 && <p className="px-4 py-6 text-sm text-center" style={{ color: COLORS.slate }}>You're all caught up.</p>}
                {notifications.map((n) => (
                  <div key={n.id} className="flex items-start gap-2 px-4 py-3 border-b last:border-0 hover:bg-slate-50" style={{ borderColor: COLORS.line }}>
                    {!n.read && <span className="mt-1.5 w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: COLORS.blue }} />}
                    <p className={`flex-1 text-sm ${n.read ? "" : "font-medium"}`} style={{ color: COLORS.ink }}>{n.text}
                      <span className="block text-xs mt-0.5" style={{ color: COLORS.slate }}>{n.time}</span>
                    </p>
                    <button onClick={() => onDismissNotif(n.id)} aria-label="Dismiss notification" className="p-1 rounded hover:bg-slate-200 shrink-0">
                      <X className="w-3.5 h-3.5" style={{ color: COLORS.slate }} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="hidden sm:flex items-center gap-2 pl-3 border-l" style={{ borderColor: COLORS.line }}>
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white" style={{ backgroundColor: COLORS.blue }}>
            {(user?.name || "A U").split(" ").map((s) => s[0]).join("").slice(0, 2)}
          </div>
          <span className="text-sm font-medium" style={{ color: COLORS.ink }}>{user?.name || "Admin User"}</span>
        </div>
      </div>
    </header>
  );
}

export default Header;
