import React, { useEffect, useState } from "react";

import { COLORS } from "./styles/tokens.js";
import { getCurrentUser, getStoredUser, getToken, logout } from "./services/authService.js";

import { Sidebar } from "./components/layout/Sidebar.jsx";
import { Header } from "./components/layout/Header.jsx";
import { DEFAULT_PAGE } from "./components/layout/navigation.js";

import { Login } from "./pages/Login.jsx";
import { Register } from "./pages/Register.jsx";
import AIAssistant from "./pages/AIAssistant.jsx";

import { PatientDashboard } from "./pages/patient/PatientDashboard.jsx";
import { LabUpload } from "./pages/patient/LabUpload.jsx";
import { SymptomIntake } from "./pages/patient/SymptomIntake.jsx";
import { MyReports } from "./pages/patient/MyReports.jsx";
import { Profile } from "./pages/patient/Profile.jsx";

import { ReviewQueue } from "./pages/clinician/ReviewQueue.jsx";
import { ReviewDetail } from "./pages/clinician/ReviewDetail.jsx";
import { CohortAnalytics } from "./pages/clinician/CohortAnalytics.jsx";

import { Clinicians } from "./pages/admin/Clinicians.jsx";

export default function App() {
  const [user, setUser] = useState(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [authPage, setAuthPage] = useState("login");
  const [page, setPage] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  const role = user?.role;

  useEffect(() => {
    if (!getToken() || !getStoredUser()) {
      setCheckingAuth(false);
      return;
    }
    getCurrentUser()
      .then((u) => setUser(u))
      .catch(() => logout())
      .finally(() => setCheckingAuth(false));
  }, []);

  useEffect(() => {
    const expire = () => { logout(); setUser(null); };
    window.addEventListener("auth:expired", expire);
    return () => window.removeEventListener("auth:expired", expire);
  }, []);

  const navigate = (next, id = null) => {
    setPage(next);
    setSelectedId(id);
    window.scrollTo?.(0, 0);
  };

  const handleLogin = (account) => {
    setUser(account);
    navigate(DEFAULT_PAGE[account.role] || "dashboard");
  };

  const handleLogout = () => {
    logout();
    setUser(null);
    setAuthPage("login");
    setPage(null);
  };

  if (checkingAuth) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: COLORS.bg }}>
        <div className="text-sm" style={{ color: COLORS.slate }}>Checking your session…</div>
      </div>
    );
  }

  if (!user) {
    return authPage === "register"
      ? <Register onLogin={handleLogin} onBackToLogin={() => setAuthPage("login")} />
      : <Login onLogin={handleLogin} onRegister={() => setAuthPage("register")} />;
  }

  const current = page || DEFAULT_PAGE[role];

  const renderPage = () => {
    if (role === "patient") {
      switch (current) {
        case "upload": return <LabUpload onNavigate={navigate} />;
        case "symptoms": return <SymptomIntake onNavigate={navigate} />;
        case "reports": return <MyReports selectedId={selectedId} onSelect={(id) => navigate("reports", id)} />;
        case "assistant": return <AIAssistant role="patient" />;
        case "profile": return <Profile user={user} onUpdated={setUser} />;
        default: return <PatientDashboard user={user} onNavigate={navigate} />;
      }
    }
    switch (current) {
      case "clinicians": return role === "admin" ? <Clinicians /> : null;
      case "analytics": return <CohortAnalytics />;
      case "assistant": return <AIAssistant role={role} />;
      case "escalations":
      case "reviews":
        return selectedId
          ? <ReviewDetail reportId={selectedId} onBack={() => navigate(current)} />
          : <ReviewQueue escalationsOnly={current === "escalations"} onOpen={(id) => navigate(current, id)} />;
      default: return null;
    }
  };

  return (
    <div className="flex min-h-screen w-full" style={{ backgroundColor: COLORS.bg }}>
      <Sidebar role={role} page={current} setPage={(p) => navigate(p)} mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} onLogout={handleLogout} user={user} />
      <div className="flex-1 min-w-0">
        <Header setMobileOpen={setMobileOpen} user={user} role={role} />
        <main>{renderPage()}</main>
      </div>
    </div>
  );
}
