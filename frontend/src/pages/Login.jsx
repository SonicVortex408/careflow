import React, { useState } from "react";
import { Eye, EyeOff, Loader2, XCircle } from "lucide-react";

import { COLORS } from "../styles/tokens.js";
import { Card } from "../components/shared/Card.jsx";
import { Logo, Vitals } from "../components/shared/Brand.jsx";
import { loginAdmin, loginUser } from "../services/authService.js";

const TABS = [
  { key: "patient", label: "Patient", heading: "Patient sign in", blurb: "See your reviewed lab results and ask questions." },
  { key: "clinician", label: "Clinician", heading: "Clinician sign in", blurb: "Review and sign off lab interpretations." },
  { key: "admin", label: "Admin", heading: "Administrator sign in", blurb: "Manage clinician accounts." },
];

export function Login({ onLogin, onRegister }) {
  const [tab, setTab] = useState("patient");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [authError, setAuthError] = useState("");
  const current = TABS.find((t) => t.key === tab);

  const validate = () => {
    const errs = {};
    if (!email.trim()) errs.email = "Email is required.";
    else if (!/^\S+@\S+\.\S+$/.test(email)) errs.email = "Enter a valid email address.";
    if (!password) errs.password = "Password is required.";
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setAuthError("");
    if (!validate()) return;
    setLoading(true);
    try {
      // Patients and clinicians share one endpoint; the server returns the role.
      const account = tab === "admin" ? await loginAdmin(email, password) : await loginUser(email, password);
      onLogin(account);
    } catch (error) {
      setAuthError(error.message || "Incorrect email or password.");
    } finally {
      setLoading(false);
    }
  };

  const input = (id, props, err) => (
    <input
      id={id}
      {...props}
      aria-invalid={!!err}
      aria-describedby={err ? `${id}-error` : undefined}
      className="w-full rounded-xl border px-3.5 py-2.5 text-sm outline-none focus:ring-2 transition"
      style={{ borderColor: err ? COLORS.critical : COLORS.line, "--tw-ring-color": COLORS.teal }}
    />
  );

  return (
    <div className="min-h-screen w-full flex items-center justify-center px-4" style={{ backgroundColor: COLORS.bg }}>
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-8">
          <Logo size="lg" />
          <div className="mt-4"><Vitals w={140} h={24} /></div>
        </div>

        <Card className="p-7 sm:p-8">
          <div className="flex mb-6 rounded-xl p-1" style={{ backgroundColor: COLORS.bg }} role="tablist">
            {TABS.map((t) => (
              <button key={t.key} type="button" role="tab" aria-selected={tab === t.key}
                onClick={() => { setTab(t.key); setAuthError(""); setErrors({}); }}
                className="flex-1 rounded-lg py-2 text-sm font-medium transition"
                style={{ backgroundColor: tab === t.key ? COLORS.teal : "transparent", color: tab === t.key ? "white" : COLORS.slate }}>
                {t.label}
              </button>
            ))}
          </div>

          <h1 className="text-xl font-semibold mb-1" style={{ color: COLORS.ink }}>{current.heading}</h1>
          <p className="text-sm mb-6" style={{ color: COLORS.slate }}>{current.blurb}</p>

          {authError && (
            <div role="alert" className="mb-5 flex items-start gap-2 rounded-xl px-3.5 py-3 text-sm" style={{ backgroundColor: COLORS.criticalSoft, color: COLORS.critical }}>
              <XCircle className="w-4 h-4 mt-0.5 shrink-0" /> <span>{authError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="mb-4">
              <label htmlFor="email" className="block text-sm font-medium mb-1.5" style={{ color: COLORS.ink }}>Email</label>
              {input("email", { type: "email", value: email, onChange: (e) => setEmail(e.target.value), autoComplete: "email" }, errors.email)}
              {errors.email && <p id="email-error" className="mt-1.5 text-xs" style={{ color: COLORS.critical }}>{errors.email}</p>}
            </div>
            <div className="mb-6">
              <label htmlFor="password" className="block text-sm font-medium mb-1.5" style={{ color: COLORS.ink }}>Password</label>
              <div className="relative">
                {input("password", { type: showPw ? "text" : "password", value: password, onChange: (e) => setPassword(e.target.value), autoComplete: "current-password" }, errors.password)}
                <button type="button" onClick={() => setShowPw((v) => !v)} aria-label={showPw ? "Hide password" : "Show password"}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && <p id="password-error" className="mt-1.5 text-xs" style={{ color: COLORS.critical }}>{errors.password}</p>}
            </div>
            <button type="submit" disabled={loading} className="w-full flex items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-semibold text-white transition disabled:opacity-70" style={{ backgroundColor: COLORS.teal }}>
              {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Signing in…</> : "Sign in"}
            </button>
          </form>

          {tab === "patient" ? (
            <div className="mt-5 text-center">
              <p className="text-xs" style={{ color: COLORS.slate }}>New here?</p>
              <button type="button" onClick={onRegister} className="mt-1 text-sm font-semibold hover:underline" style={{ color: COLORS.teal }}>Create a patient account</button>
            </div>
          ) : (
            <p className="mt-5 text-center text-xs" style={{ color: COLORS.slate }}>
              {tab === "clinician" ? "Clinician accounts are created by an administrator." : "Administrator accounts are provisioned by the platform team."}
            </p>
          )}
        </Card>

        <p className="text-xs text-center mt-6" style={{ color: COLORS.slate }}>
          PolyMarker explains lab results in plain language. It does not diagnose or replace clinical judgement,
          and every interpretation is reviewed by a clinician before you see it.
        </p>
      </div>
    </div>
  );
}

export default Login;
