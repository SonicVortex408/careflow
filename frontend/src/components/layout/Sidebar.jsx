import React from "react";
import { LogOut, X } from "lucide-react";

import { COLORS } from "../../styles/tokens.js";
import { Logo } from "../shared/Brand.jsx";
import { NAV_BY_ROLE } from "./navigation.js";

const ROLE_LABEL = { patient: "Patient", clinician: "Clinician", admin: "Administrator" };

export function Sidebar({ role, page, setPage, mobileOpen, setMobileOpen, onLogout, user, badges = {} }) {
  const items = NAV_BY_ROLE[role] || [];

  const content = (
    <div className="flex flex-col h-full">
      <div className="px-5 py-5">
        <Logo />
        <div className="mt-1 text-xs" style={{ color: COLORS.slate }}>{ROLE_LABEL[role]} workspace</div>
      </div>

      <nav className="flex-1 px-3 space-y-1" aria-label="Main navigation">
        {items.map((item) => {
          const Icon = item.icon;
          const active = page === item.key;
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => { setPage(item.key); setMobileOpen(false); }}
              aria-current={active ? "page" : undefined}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition focus:outline-none focus-visible:ring-2"
              style={{
                backgroundColor: active ? COLORS.tealSoft : "transparent",
                color: active ? COLORS.teal : COLORS.slate,
                "--tw-ring-color": COLORS.teal,
              }}
            >
              <Icon style={{ width: 18, height: 18 }} aria-hidden="true" />
              <span className="flex-1 text-left">{item.label}</span>
              {badges[item.key] > 0 && (
                <span className="text-xs font-semibold rounded-full px-1.5 py-0.5 text-white" style={{ backgroundColor: COLORS.critical }}>
                  {badges[item.key]}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="p-3 border-t" style={{ borderColor: COLORS.line }}>
        <div className="px-3 pb-2 text-xs truncate" style={{ color: COLORS.slate }}>{user?.email}</div>
        <button
          type="button"
          onClick={onLogout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium hover:bg-slate-50 transition"
          style={{ color: COLORS.slate }}
        >
          <LogOut style={{ width: 18, height: 18 }} aria-hidden="true" /> Log out
        </button>
      </div>
    </div>
  );

  return (
    <>
      <aside className="hidden lg:block w-64 shrink-0 border-r bg-white h-screen sticky top-0" style={{ borderColor: COLORS.line }}>
        {content}
      </aside>
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-40">
          <div className="absolute inset-0 bg-black/40" onClick={() => setMobileOpen(false)} aria-hidden="true" />
          <div className="absolute left-0 top-0 h-full w-72 bg-white shadow-xl" role="dialog" aria-modal="true" aria-label="Navigation menu">
            <div className="flex justify-end p-3">
              <button type="button" onClick={() => setMobileOpen(false)} aria-label="Close menu" className="p-2 rounded-lg hover:bg-slate-100">
                <X className="w-5 h-5" />
              </button>
            </div>
            {content}
          </div>
        </div>
      )}
    </>
  );
}

export default Sidebar;
