import React from "react";

import {
  LayoutDashboard,
  Users,
  Building2,
  Stethoscope,
  BarChart3,
  Bell,
  Settings,
  LogOut,
  X,
  Bot,
} from "lucide-react";

import { COLORS } from "../../styles/tokens.js";
import { Logo } from "../shared/Brand.jsx";


/* =========================
   NAVIGATION ITEMS
========================= */

export const NAV_ITEMS = [
  {
    key: "dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
  },

  {
    key: "patients",
    label: "Patient Queue",
    icon: Users,
  },

  {
    key: "departments",
    label: "Departments",
    icon: Building2,
  },

  {
    key: "doctors",
    label: "Doctors & Resources",
    icon: Stethoscope,
  },

  {
    key: "analytics",
    label: "Analytics",
    icon: BarChart3,
  },

  {
    key: "alerts",
    label: "Alerts",
    icon: Bell,
  },

  {
    key: "ai-assistant",
    label: "AI Assistant",
    icon: Bot,
  },

  {
    key: "settings",
    label: "Settings",
    icon: Settings,
  },
];


/* =========================
   SIDEBAR
========================= */

export function Sidebar({
  page,
  setPage,
  mobileOpen,
  setMobileOpen,
  onLogout,
  alertCount,
}) {

  const content = (
    <div className="flex flex-col h-full">

      {/* =========================
          LOGO
      ========================= */}

      <div className="px-5 py-5">
        <Logo />
      </div>


      {/* =========================
          NAVIGATION
      ========================= */}

      <nav
        className="flex-1 px-3 space-y-1"
        aria-label="Main navigation"
      >

        {NAV_ITEMS.map((item) => {

          const Icon = item.icon;

          const active =
            page === item.key;


          return (
            <button
              key={item.key}

              onClick={() => {
                setPage(item.key);
                setMobileOpen(false);
              }}

              aria-current={
                active
                  ? "page"
                  : undefined
              }

              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition focus:outline-none focus-visible:ring-2"

              style={{
                backgroundColor:
                  active
                    ? COLORS.tealSoft
                    : "transparent",

                color:
                  active
                    ? COLORS.teal
                    : COLORS.slate,

                "--tw-ring-color":
                  COLORS.teal,
              }}
            >

              <Icon
                style={{
                  width: 18,
                  height: 18,
                }}
              />


              <span className="flex-1 text-left">
                {item.label}
              </span>


              {/* Alert badge */}

              {item.key === "alerts" &&
                alertCount > 0 && (

                  <span
                    className="text-xs font-semibold rounded-full px-1.5 py-0.5"

                    style={{
                      backgroundColor:
                        COLORS.critical,

                      color: "white",
                    }}
                  >
                    {alertCount}
                  </span>

                )}

            </button>
          );

        })}

      </nav>


      {/* =========================
          LOGOUT
      ========================= */}

      <div
        className="p-3 border-t"
        style={{
          borderColor:
            COLORS.line,
        }}
      >

        <button
          onClick={onLogout}

          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium hover:bg-slate-50 transition"

          style={{
            color:
              COLORS.slate,
          }}
        >

          <LogOut
            style={{
              width: 18,
              height: 18,
            }}
          />

          Logout

        </button>

      </div>

    </div>
  );


  /* =========================
     DESKTOP SIDEBAR
  ========================= */

  return (
    <>

      <aside
        className="hidden lg:block w-64 shrink-0 border-r bg-white h-screen sticky top-0"

        style={{
          borderColor:
            COLORS.line,
        }}
      >

        {content}

      </aside>


      {/* =========================
         MOBILE SIDEBAR
      ========================= */}

      {mobileOpen && (

        <div className="lg:hidden fixed inset-0 z-40">

          {/* Overlay */}

          <div
            className="absolute inset-0 bg-black/40"

            onClick={() =>
              setMobileOpen(false)
            }

            aria-hidden="true"
          />


          {/* Sidebar */}

          <div
            className="absolute left-0 top-0 h-full w-72 bg-white shadow-xl"

            role="dialog"

            aria-modal="true"

            aria-label="Navigation menu"
          >

            {/* Close button */}

            <div className="flex justify-end p-3">

              <button
                onClick={() =>
                  setMobileOpen(false)
                }

                aria-label="Close menu"

                className="p-2 rounded-lg hover:bg-slate-100"
              >

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
