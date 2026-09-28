import React, { useState } from "react";

import {
  CalendarDays,
  ClipboardList,
  FileText,
  User,
  LogOut,
  Clock,
  Stethoscope,
  Menu,
  X,
  Bot,
} from "lucide-react";

import { COLORS } from "../../styles/tokens.js";
import AIAssistant from "../../pages/AIAssistant.jsx";

export function PatientPortal({ user, onLogout }) {
  const [page, setPage] = useState("dashboard");
  const [mobileOpen, setMobileOpen] = useState(false);

  const navigation = [
    {
      id: "dashboard",
      label: "Dashboard",
      icon: ClipboardList,
    },
    {
      id: "appointments",
      label: "Appointments",
      icon: CalendarDays,
    },
    {
      id: "records",
      label: "Medical Records",
      icon: FileText,
    },
    {
      id: "ai-assistant",
      label: "CareFlow AI",
      icon: Bot,
    },
    {
      id: "profile",
      label: "My Profile",
      icon: User,
    },
  ];

  const handleNavigation = (pageName) => {
    setPage(pageName);
    setMobileOpen(false);
  };

  return (
    <div
      className="min-h-screen w-full flex"
      style={{ backgroundColor: COLORS.bg }}
    >
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/30 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-50
          w-64 border-r
          transform transition-transform duration-200
          ${mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
        `}
        style={{
          backgroundColor: COLORS.surface,
          borderColor: COLORS.line,
        }}
      >
        <div className="h-full flex flex-col">
          {/* Logo / Brand */}
          <div
            className="h-20 flex items-center justify-between px-6 border-b"
            style={{ borderColor: COLORS.line }}
          >
            <div>
              <h1
                className="text-xl font-bold"
                style={{ color: COLORS.teal }}
              >
                CareFlow
              </h1>

              <p
                className="text-xs mt-0.5"
                style={{ color: COLORS.slate }}
              >
                Patient Portal
              </p>
            </div>

            <button
              onClick={() => setMobileOpen(false)}
              className="lg:hidden"
              style={{ color: COLORS.slate }}
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              const active = page === item.id;

              return (
                <button
                  key={item.id}
                  onClick={() => handleNavigation(item.id)}
                  className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition"
                  style={{
                    backgroundColor: active
                      ? COLORS.teal
                      : "transparent",
                    color: active ? "white" : COLORS.slate,
                  }}
                >
                  <Icon className="w-5 h-5" />
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* User section */}
          <div
            className="p-4 border-t"
            style={{ borderColor: COLORS.line }}
          >
            <div className="flex items-center gap-3 mb-4">
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center font-semibold"
                style={{
                  backgroundColor: COLORS.tealSoft,
                  color: COLORS.teal,
                }}
              >
                {user?.name?.charAt(0)?.toUpperCase() || "P"}
              </div>

              <div className="min-w-0">
                <p
                  className="text-sm font-semibold truncate"
                  style={{ color: COLORS.ink }}
                >
                  {user?.name || "Patient"}
                </p>

                <p
                  className="text-xs truncate"
                  style={{ color: COLORS.slate }}
                >
                  {user?.email || ""}
                </p>
              </div>
            </div>

            <button
              onClick={onLogout}
              className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition hover:bg-gray-100"
              style={{ color: COLORS.slate }}
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 min-w-0">
        {/* Header */}
        <header
          className="h-20 border-b flex items-center justify-between px-4 sm:px-6 lg:px-8"
          style={{
            backgroundColor: COLORS.surface,
            borderColor: COLORS.line,
          }}
        >
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileOpen(true)}
              className="lg:hidden"
              style={{ color: COLORS.ink }}
            >
              <Menu className="w-6 h-6" />
            </button>

            <div>
              <h2
                className="text-lg font-semibold"
                style={{ color: COLORS.ink }}
              >
                {page === "dashboard" && "Patient Dashboard"}
                {page === "appointments" && "Appointments"}
                {page === "records" && "Medical Records"}
                {page === "ai-assistant" && "CareFlow AI"}
                {page === "profile" && "My Profile"}
              </h2>

              <p
                className="text-xs hidden sm:block"
                style={{ color: COLORS.slate }}
              >
                {page === "ai-assistant"
                  ? "Your private AI-powered medical assistant"
                  : "Manage your CareFlow information"}
              </p>
            </div>
          </div>

          <div
            className="w-9 h-9 rounded-full flex items-center justify-center"
            style={{
              backgroundColor: COLORS.tealSoft,
              color: COLORS.teal,
            }}
          >
            <User className="w-4 h-4" />
          </div>
        </header>

        {/* Page content */}
        <main
          className={
            page === "ai-assistant"
              ? "p-0"
              : "p-4 sm:p-6 lg:p-8"
          }
        >
          {page === "dashboard" && (
            <DashboardContent
              user={user}
              onNavigate={handleNavigation}
            />
          )}

          {page === "appointments" && (
            <AppointmentsContent />
          )}

          {page === "records" && (
            <RecordsContent />
          )}

          {page === "ai-assistant" && (
            <AIAssistant />
          )}

          {page === "profile" && (
            <ProfileContent user={user} />
          )}
        </main>
      </div>
    </div>
  );
}

/* ============================================================
   Dashboard
============================================================ */

function DashboardContent({ user, onNavigate }) {
  return (
    <div className="max-w-7xl mx-auto">
      {/* Welcome */}
      <div className="mb-8">
        <h1
          className="text-2xl font-bold"
          style={{ color: COLORS.ink }}
        >
          Welcome, {user?.name || "Patient"}!
        </h1>

        <p
          className="mt-1 text-sm"
          style={{ color: COLORS.slate }}
        >
          Here's an overview of your CareFlow activity.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        <StatCard
          icon={CalendarDays}
          title="Upcoming Appointment"
          value="Sep 2, 2026"
          subtitle="10:30 AM"
        />

        <StatCard
          icon={Clock}
          title="Estimated Waiting Time"
          value="15 min"
          subtitle="Current estimate"
        />

        <StatCard
          icon={FileText}
          title="Medical Records"
          value="4"
          subtitle="Available records"
        />
      </div>

      {/* Appointment card */}
      <div
        className="rounded-2xl border p-5 mb-6"
        style={{
          backgroundColor: COLORS.surface,
          borderColor: COLORS.line,
        }}
      >
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2
              className="text-base font-semibold"
              style={{ color: COLORS.ink }}
            >
              Upcoming Appointment
            </h2>

            <p
              className="text-sm mt-1"
              style={{ color: COLORS.slate }}
            >
              Your next scheduled visit
            </p>
          </div>

          <CalendarDays
            className="w-5 h-5"
            style={{ color: COLORS.teal }}
          />
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center"
              style={{
                backgroundColor: COLORS.tealSoft,
                color: COLORS.teal,
              }}
            >
              <Stethoscope className="w-6 h-6" />
            </div>

            <div>
              <p
                className="font-semibold"
                style={{ color: COLORS.ink }}
              >
                General Consultation
              </p>

              <p
                className="text-sm"
                style={{ color: COLORS.slate }}
              >
                Dr. Sarah Johnson
              </p>
            </div>
          </div>

          <div className="text-sm sm:text-right">
            <p
              className="font-medium"
              style={{ color: COLORS.ink }}
            >
              September 2, 2026
            </p>

            <p style={{ color: COLORS.slate }}>
              10:30 AM
            </p>
          </div>
        </div>
      </div>

      {/* Quick actions */}
      <div>
        <h2
          className="text-base font-semibold mb-4"
          style={{ color: COLORS.ink }}
        >
          Quick Actions
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <QuickAction
            icon={CalendarDays}
            title="Appointments"
            description="View your appointments"
            onClick={() => onNavigate("appointments")}
          />

          <QuickAction
            icon={FileText}
            title="Medical Records"
            description="View your records"
            onClick={() => onNavigate("records")}
          />

          <QuickAction
            icon={Bot}
            title="CareFlow AI"
            description="Ask questions about your health"
            onClick={() => onNavigate("ai-assistant")}
          />

          <QuickAction
            icon={User}
            title="My Profile"
            description="Manage your information"
            onClick={() => onNavigate("profile")}
          />
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   Appointments
============================================================ */

function AppointmentsContent() {
  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-6">
        <h1
          className="text-2xl font-bold"
          style={{ color: COLORS.ink }}
        >
          My Appointments
        </h1>

        <p
          className="text-sm mt-1"
          style={{ color: COLORS.slate }}
        >
          View your upcoming and previous appointments.
        </p>
      </div>

      <div
        className="rounded-2xl border p-5"
        style={{
          backgroundColor: COLORS.surface,
          borderColor: COLORS.line,
        }}
      >
        <Appointment
          date="September 2, 2026"
          time="10:30 AM"
          doctor="Dr. Sarah Johnson"
          department="General Medicine"
          status="Upcoming"
        />

        <Appointment
          date="August 15, 2026"
          time="2:00 PM"
          doctor="Dr. Michael Smith"
          department="Cardiology"
          status="Completed"
        />
      </div>
    </div>
  );
}

/* ============================================================
   Medical Records
============================================================ */

function RecordsContent() {
  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-6">
        <h1
          className="text-2xl font-bold"
          style={{ color: COLORS.ink }}
        >
          Medical Records
        </h1>

        <p
          className="text-sm mt-1"
          style={{ color: COLORS.slate }}
        >
          Access your available medical records.
        </p>
      </div>

      <div
        className="rounded-2xl border p-5"
        style={{
          backgroundColor: COLORS.surface,
          borderColor: COLORS.line,
        }}
      >
        <Record
          title="General Consultation"
          doctor="Dr. Sarah Johnson"
          date="September 2, 2026"
        />

        <Record
          title="Blood Test Report"
          doctor="CareFlow Diagnostics"
          date="August 15, 2026"
        />

        <Record
          title="Cardiology Consultation"
          doctor="Dr. Michael Smith"
          date="July 28, 2026"
        />
      </div>
    </div>
  );
}

/* ============================================================
   Profile
============================================================ */

function ProfileContent({ user }) {
  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6">
        <h1
          className="text-2xl font-bold"
          style={{ color: COLORS.ink }}
        >
          My Profile
        </h1>

        <p
          className="text-sm mt-1"
          style={{ color: COLORS.slate }}
        >
          View your account information.
        </p>
      </div>

      <div
        className="rounded-2xl border p-6"
        style={{
          backgroundColor: COLORS.surface,
          borderColor: COLORS.line,
        }}
      >
        <div className="flex items-center gap-4 mb-8">
          <div
            className="w-16 h-16 rounded-full flex items-center justify-center text-xl font-bold"
            style={{
              backgroundColor: COLORS.tealSoft,
              color: COLORS.teal,
            }}
          >
            {user?.name?.charAt(0)?.toUpperCase() || "P"}
          </div>

          <div>
            <h2
              className="text-lg font-semibold"
              style={{ color: COLORS.ink }}
            >
              {user?.name || "Patient"}
            </h2>

            <p
              className="text-sm"
              style={{ color: COLORS.slate }}
            >
              Patient
            </p>
          </div>
        </div>

        <div className="space-y-5">
          <ProfileField
            label="Full Name"
            value={user?.name || "Not available"}
          />

          <ProfileField
            label="Email"
            value={user?.email || "Not available"}
          />

          <ProfileField
            label="Account Type"
            value="Patient"
          />
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   Reusable Components
============================================================ */

function StatCard({ icon: Icon, title, value, subtitle }) {
  return (
    <div
      className="rounded-2xl border p-5"
      style={{
        backgroundColor: COLORS.surface,
        borderColor: COLORS.line,
      }}
    >
      <div className="flex items-start justify-between">
        <div>
          <p
            className="text-sm"
            style={{ color: COLORS.slate }}
          >
            {title}
          </p>

          <p
            className="text-xl font-bold mt-2"
            style={{ color: COLORS.ink }}
          >
            {value}
          </p>

          <p
            className="text-xs mt-1"
            style={{ color: COLORS.slate }}
          >
            {subtitle}
          </p>
        </div>

        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{
            backgroundColor: COLORS.tealSoft,
            color: COLORS.teal,
          }}
        >
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}

function QuickAction({ icon: Icon, title, description, onClick }) {
  return (
    <button
      onClick={onClick}
      className="text-left rounded-2xl border p-5 transition hover:shadow-sm"
      style={{
        backgroundColor: COLORS.surface,
        borderColor: COLORS.line,
      }}
    >
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center mb-4"
        style={{
          backgroundColor: COLORS.tealSoft,
          color: COLORS.teal,
        }}
      >
        <Icon className="w-5 h-5" />
      </div>

      <h3
        className="font-semibold text-sm"
        style={{ color: COLORS.ink }}
      >
        {title}
      </h3>

      <p
        className="text-xs mt-1"
        style={{ color: COLORS.slate }}
      >
        {description}
      </p>
    </button>
  );
}

function Appointment({
  date,
  time,
  doctor,
  department,
  status,
}) {
  const completed = status === "Completed";

  return (
    <div
      className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 py-4 border-b last:border-b-0"
      style={{ borderColor: COLORS.line }}
    >
      <div className="flex items-center gap-4">
        <div
          className="w-11 h-11 rounded-xl flex items-center justify-center"
          style={{
            backgroundColor: COLORS.tealSoft,
            color: COLORS.teal,
          }}
        >
          <CalendarDays className="w-5 h-5" />
        </div>

        <div>
          <p
            className="font-semibold text-sm"
            style={{ color: COLORS.ink }}
          >
            {department}
          </p>

          <p
            className="text-xs mt-1"
            style={{ color: COLORS.slate }}
          >
            {doctor}
          </p>

          <p
            className="text-xs mt-1"
            style={{ color: COLORS.slate }}
          >
            {date} · {time}
          </p>
        </div>
      </div>

      <span
        className="text-xs font-medium px-3 py-1.5 rounded-full self-start sm:self-auto"
        style={{
          backgroundColor: completed
            ? "#e5e7eb"
            : COLORS.tealSoft,
          color: completed
            ? COLORS.slate
            : COLORS.teal,
        }}
      >
        {status}
      </span>
    </div>
  );
}

function Record({ title, doctor, date }) {
  return (
    <div
      className="flex items-center justify-between gap-4 py-4 border-b last:border-b-0"
      style={{ borderColor: COLORS.line }}
    >
      <div className="flex items-center gap-4">
        <div
          className="w-11 h-11 rounded-xl flex items-center justify-center"
          style={{
            backgroundColor: COLORS.tealSoft,
            color: COLORS.teal,
          }}
        >
          <FileText className="w-5 h-5" />
        </div>

        <div>
          <p
            className="text-sm font-semibold"
            style={{ color: COLORS.ink }}
          >
            {title}
          </p>

          <p
            className="text-xs mt-1"
            style={{ color: COLORS.slate }}
          >
            {doctor} · {date}
          </p>
        </div>
      </div>

      <button
        className="text-xs font-medium hover:underline"
        style={{ color: COLORS.teal }}
      >
        View
      </button>
    </div>
  );
}

function ProfileField({ label, value }) {
  return (
    <div>
      <p
        className="text-xs font-medium mb-1"
        style={{ color: COLORS.slate }}
      >
        {label}
      </p>

      <p
        className="text-sm"
        style={{ color: COLORS.ink }}
      >
        {value}
      </p>
    </div>
  );
}

export default PatientPortal;