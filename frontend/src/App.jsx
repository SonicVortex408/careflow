import React, { useState, useEffect, useCallback, useRef } from "react";

import { COLORS } from "./styles/tokens.js";

import {
  PATIENTS_BASE,
  DEPARTMENTS_BASE,
  DOCTORS_BASE,
  ALERTS_BASE,
  NOTIFICATIONS_BASE,
} from "./data/mockData.js";

import {
  getToken,
  getStoredUser,
  getRole,
  getCurrentUser,
  logout,
} from "./services/authService.js";

// =========================
// LAYOUT
// =========================

import { Sidebar } from "./components/layout/Sidebar.jsx";
import { Header } from "./components/layout/Header.jsx";

// =========================
// SHARED COMPONENTS
// =========================

import { PatientDetails } from "./components/patients/PatientDetails.jsx";
import { ConfirmDialog } from "./components/shared/ConfirmDialog.jsx";

// =========================
// ADMIN / STAFF PAGES
// =========================

import { Dashboard } from "./pages/Dashboard.jsx";
import { Patients } from "./pages/Patients.jsx";
import { Departments } from "./pages/Departments.jsx";
import { Doctors } from "./pages/Doctors.jsx";
import { Analytics } from "./pages/Analytics.jsx";
import { Alerts } from "./pages/Alerts.jsx";
import { Settings } from "./pages/Settings.jsx";
import { Register } from "./pages/Register.jsx";

// =========================
// AI ASSISTANT
// =========================

import AIAssistant from "./pages/AIAssistant.jsx";

// =========================
// AUTH / PATIENT
// =========================

import { Login } from "./pages/Login.jsx";
import { PatientPortal } from "./components/patients/PatientPortal.jsx";

export default function App() {
  // =========================
  // AUTH STATE
  // =========================

  const [authed, setAuthed] = useState(false);
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(null);
  const [checkingAuth, setCheckingAuth] = useState(true);

  // =========================
  // ADMIN STATE
  // =========================

  const [page, setPage] = useState("dashboard");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [search, setSearch] = useState("");

  const [patients, setPatients] = useState(PATIENTS_BASE);
  const [departments, setDepartments] = useState(DEPARTMENTS_BASE);
  const [doctors, setDoctors] = useState(DOCTORS_BASE);
  const [alerts, setAlerts] = useState(ALERTS_BASE);

  const [notifications, setNotifications] = useState(
    NOTIFICATIONS_BASE
  );

  const [selectedPatient, setSelectedPatient] = useState(null);
  const [confirmAction, setConfirmAction] = useState(null);

  // =========================
  // AUTH PAGE STATE
  // =========================

  const [authPage, setAuthPage] = useState("login");
  const [registerRole, setRegisterRole] = useState("user");

  // =========================
  // RESTORE LOGIN
  // =========================

  useEffect(() => {
    const restoreSession = async () => {
      const token = getToken();
      const storedUser = getStoredUser();
      const storedRole = getRole();

      if (!token || !storedUser || !storedRole) {
        setCheckingAuth(false);
        return;
      }

      try {
        const currentUser = await getCurrentUser();

        if (currentUser) {
          const actualUser =
            currentUser.user ||
            currentUser.admin ||
            currentUser;

          setUser({
            ...actualUser,
            role: storedRole,
          });

          setRole(storedRole);
          setAuthed(true);
        } else {
          logout();

          setUser(null);
          setRole(null);
          setAuthed(false);
        }
      } catch (error) {
        console.error("Session restore failed:", error);

        logout();

        setUser(null);
        setRole(null);
        setAuthed(false);
      } finally {
        setCheckingAuth(false);
      }
    };

    restoreSession();
  }, []);

  // =========================
  // LOGIN
  // =========================

  const handleLogin = (loggedInUser) => {
    const loggedInRole = loggedInUser.role;

    setUser(loggedInUser);
    setRole(loggedInRole);
    setAuthed(true);

    setPage("dashboard");
  };

  // =========================
  // LOGOUT
  // =========================

  const handleLogout = () => {
    logout();

    setAuthed(false);
    setUser(null);
    setRole(null);

    setPage("dashboard");
    setAuthPage("login");
  };

  // =========================
  // DETERMINISTIC SIMULATION
  // =========================

  const tickRef = useRef(0);

  useEffect(() => {
    if (!authed || role !== "admin") {
      return;
    }

    const id = setInterval(() => {
      tickRef.current += 1;

      const t = tickRef.current;

      // Patient wait time
      setPatients((prev) =>
        prev.map((p, i) => {
          if (p.status === "Completed") {
            return p;
          }

          const delta =
            (i + t) % 3 === 0
              ? -1
              : 1;

          const nextWait = Math.max(
            1,
            p.waitTime + delta
          );

          return {
            ...p,
            waitTime: nextWait,
          };
        })
      );

      // Department workload
      setDepartments((prev) =>
        prev.map((d, i) => {
          const delta =
            (i + t) % 4 === 0
              ? -2
              : (i + t) % 3 === 0
              ? 2
              : 0;

          const workload = Math.min(
            96,
            Math.max(
              15,
              d.workload + delta
            )
          );

          return {
            ...d,
            workload,
          };
        })
      );
    }, 5000);

    return () => clearInterval(id);
  }, [authed, role]);

  // =========================
  // ADD PATIENT
  // =========================

  const handleAddPatient = useCallback(
    (newPatient) => {
      setPatients((prev) => [
        newPatient,
        ...prev,
      ]);

      setDepartments((prev) =>
        prev.map((d) =>
          d.name === newPatient.department
            ? {
                ...d,
                queue: d.queue + 1,
              }
            : d
        )
      );

      setNotifications((prev) => [
        {
          id: `N${Date.now()}`,
          text: `${newPatient.name} added to ${newPatient.department} queue.`,
          time: "Just now",
          read: false,
        },
        ...prev,
      ]);
    },
    []
  );

  // =========================
  // APPLY PATIENT ACTION
  // =========================

  const applyPatientAction = useCallback(
    (key, patient) => {
      const updates = {
        serve: {
          status: "Being evaluated",
        },

        complete: {
          status: "Completed",
          waitTime: 0,
        },

        escalate: {
          status: "Escalated",
          priority: "Critical",
        },

        transfer: {},
      };

      if (key === "transfer") {
        const idx = departments.findIndex(
          (d) => d.name === patient.department
        );

        const next =
          departments[
            (idx + 1) % departments.length
          ];

        if (!next) {
          return;
        }

        setPatients((prev) =>
          prev.map((p) =>
            p.id === patient.id
              ? {
                  ...p,
                  department: next.name,
                  doctor: "Unassigned",
                }
              : p
          )
        );
      } else {
        setPatients((prev) =>
          prev.map((p) =>
            p.id === patient.id
              ? {
                  ...p,
                  ...updates[key],
                }
              : p
          )
        );
      }

      setSelectedPatient((sp) =>
        sp && sp.id === patient.id
          ? null
          : sp
      );
    },
    [departments]
  );

  // =========================
  // PATIENT ACTION
  // =========================

  const handlePatientAction = useCallback(
    (key, patient) => {
      if (key === "escalate") {
        setConfirmAction({
          title: "Escalate patient",

          message:
            `Escalate ${patient.name} (#${patient.id}) ` +
            `to critical priority? This will notify the assigned care team.`,

          danger: true,

          onConfirm: () => {
            applyPatientAction(
              "escalate",
              patient
            );

            setConfirmAction(null);
          },
        });

        return;
      }

      if (key === "complete") {
        setConfirmAction({
          title: "Mark as completed",

          message:
            `Mark ${patient.name}'s (#${patient.id}) ` +
            `visit as completed?`,

          onConfirm: () => {
            applyPatientAction(
              "complete",
              patient
            );

            setConfirmAction(null);
          },
        });

        return;
      }

      applyPatientAction(
        key,
        patient
      );
    },
    [applyPatientAction]
  );

  // =========================
  // ALERTS
  // =========================

  const resolveAlert = (id) =>
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === id
          ? {
              ...a,
              status: "resolved",
            }
          : a
      )
    );

  const dismissAlert = (id) =>
    setAlerts((prev) =>
      prev.filter(
        (a) => a.id !== id
      )
    );

  // =========================
  // NOTIFICATIONS
  // =========================

  const markAllRead = () =>
    setNotifications((prev) =>
      prev.map((n) => ({
        ...n,
        read: true,
      }))
    );

  const dismissNotif = (id) =>
    setNotifications((prev) =>
      prev.filter(
        (n) => n.id !== id
      )
    );

  // =========================
  // AUTH LOADING
  // =========================

  if (checkingAuth) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{
          backgroundColor: COLORS.bg,
        }}
      >
        <div
          className="text-sm"
          style={{
            color: COLORS.slate,
          }}
        >
          Checking your session...
        </div>
      </div>
    );
  }

  // =========================
  // NOT LOGGED IN
  // =========================

  if (!authed) {
    if (authPage === "register") {
      return (
        <Register
          role={registerRole}
          onLogin={handleLogin}
          onBackToLogin={() =>
            setAuthPage("login")
          }
        />
      );
    }

    return (
      <Login
        onLogin={handleLogin}
        onRegister={(selectedRole) => {
          setRegisterRole(selectedRole);
          setAuthPage("register");
        }}
      />
    );
  }

  // =========================
  // PATIENT PORTAL
  // =========================

  if (role === "user") {
    return (
      <PatientPortal
        user={user}
        onLogout={handleLogout}
      />
    );
  }

  // =========================
  // ADMIN / STAFF
  // =========================

  const activeAlertCount =
    alerts.filter(
      (a) => a.status === "active"
    ).length;

  return (
    <div
      className="flex min-h-screen w-full"
      style={{
        backgroundColor: COLORS.bg,
      }}
    >
      {/* =========================
          SIDEBAR
      ========================= */}

      <Sidebar
        page={page}
        setPage={setPage}
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
        onLogout={handleLogout}
        alertCount={activeAlertCount}
      />

      {/* =========================
          MAIN CONTENT
      ========================= */}

      <div className="flex-1 min-w-0">

        {/* HEADER */}

        <Header
          setMobileOpen={setMobileOpen}
          notifications={notifications}
          onMarkAllRead={markAllRead}
          onDismissNotif={dismissNotif}
          search={search}
          setSearch={setSearch}
          user={user}
        />

        {/* =========================
            DASHBOARD
        ========================= */}

        {page === "dashboard" && (
          <Dashboard
            patients={patients}
            departments={departments}
            doctors={doctors}
            alerts={alerts}
            onSelectPatient={setSelectedPatient}
            onNavigate={setPage}
          />
        )}

        {/* =========================
            PATIENTS
        ========================= */}

        {page === "patients" && (
          <Patients
            patients={patients}
            departments={departments}
            search={search}
            onSelect={setSelectedPatient}
            onAction={handlePatientAction}
            onAdd={handleAddPatient}
          />
        )}

        {/* =========================
            DEPARTMENTS
        ========================= */}

        {page === "departments" && (
          <Departments
            departments={departments}
            doctors={doctors}
          />
        )}

        {/* =========================
            DOCTORS
        ========================= */}

        {page === "doctors" && (
          <Doctors
            doctors={doctors}
            search={search}
          />
        )}

        {/* =========================
            ANALYTICS
        ========================= */}

        {page === "analytics" && (
          <Analytics
            departments={departments}
            doctors={doctors}
          />
        )}

        {/* =========================
            ALERTS
        ========================= */}

        {page === "alerts" && (
          <Alerts
            alerts={alerts}
            onResolve={resolveAlert}
            onDismiss={dismissAlert}
          />
        )}

        {/* =========================
            AI ASSISTANT
        ========================= */}

        {page === "ai-assistant" && (
          <AIAssistant />
        )}

        {/* =========================
            SETTINGS
        ========================= */}

        {page === "settings" && (
          <Settings
            user={user}
          />
        )}
      </div>

      {/* =========================
          PATIENT DETAILS
      ========================= */}

      <PatientDetails
        patient={selectedPatient}
        departments={departments}
        onClose={() =>
          setSelectedPatient(null)
        }
        onAction={handlePatientAction}
      />

      {/* =========================
          CONFIRM DIALOG
      ========================= */}

      <ConfirmDialog
        open={!!confirmAction}
        title={confirmAction?.title}
        message={confirmAction?.message}
        danger={confirmAction?.danger}
        confirmLabel="Confirm"
        onConfirm={
          confirmAction?.onConfirm
        }
        onCancel={() =>
          setConfirmAction(null)
        }
      />
    </div>
  );
}

