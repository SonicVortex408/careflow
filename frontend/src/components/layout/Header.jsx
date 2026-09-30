import React from "react";
import { Menu } from "lucide-react";

import { COLORS } from "../../styles/tokens.js";
import { SyntheticDataNotice } from "../shared/Badges.jsx";

const ROLE_LABEL = { patient: "Patient", clinician: "Clinician", admin: "Admin" };

export function Header({ setMobileOpen, user, role }) {
  const initials = (user?.name || "?").split(" ").map((s) => s[0]).join("").slice(0, 2).toUpperCase();
  return (
    <header className="sticky top-0 z-30 bg-white border-b print:hidden" style={{ borderColor: COLORS.line }}>
      <div className="flex items-center gap-3 px-4 sm:px-6 py-3">
        <button type="button" onClick={() => setMobileOpen(true)} aria-label="Open menu" className="lg:hidden p-2 -ml-2 rounded-lg hover:bg-slate-100">
          <Menu className="w-5 h-5" />
        </button>
        <div className="hidden sm:block text-sm font-semibold" style={{ color: COLORS.ink }}>PolyMarker Analytics</div>
        <div className="ml-auto flex items-center gap-3">
          <SyntheticDataNotice compact />
          <div className="flex items-center gap-2 pl-3 border-l" style={{ borderColor: COLORS.line }}>
            <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white" style={{ backgroundColor: COLORS.teal }}>{initials}</div>
            <div className="hidden sm:block leading-tight">
              <div className="text-sm font-medium" style={{ color: COLORS.ink }}>{user?.name}</div>
              <div className="text-xs" style={{ color: COLORS.slate }}>{ROLE_LABEL[role]}</div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Header;
