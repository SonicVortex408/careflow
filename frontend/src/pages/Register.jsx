import React, { useState } from "react";
import { ArrowLeft, Loader2, XCircle } from "lucide-react";

import { COLORS } from "../styles/tokens.js";
import { Card } from "../components/shared/Card.jsx";
import { Logo } from "../components/shared/Brand.jsx";
import { registerUser } from "../services/authService.js";

export function Register({ onLogin, onBackToLogin }) {
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "", sex: "", birthYear: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (!form.name.trim() || !form.email.trim()) return setError("Name and email are required.");
    if (form.password.length < 8) return setError("Password must be at least 8 characters.");
    if (form.password !== form.confirm) return setError("Passwords do not match.");
    setLoading(true);
    try {
      onLogin(await registerUser(form));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const field = (k, label, props = {}) => (
    <div>
      <label htmlFor={k} className="block text-sm font-medium mb-1.5" style={{ color: COLORS.ink }}>{label}</label>
      <input id={k} value={form[k]} onChange={set(k)} {...props} className="w-full rounded-xl border px-3.5 py-2.5 text-sm" style={{ borderColor: COLORS.line }} />
    </div>
  );

  return (
    <div className="min-h-screen w-full flex items-center justify-center px-4 py-10" style={{ backgroundColor: COLORS.bg }}>
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-6"><Logo size="lg" /></div>
        <Card className="p-7 sm:p-8">
          <button type="button" onClick={onBackToLogin} className="inline-flex items-center gap-1 text-sm font-medium mb-4" style={{ color: COLORS.teal }}>
            <ArrowLeft className="w-4 h-4" /> Back to sign in
          </button>
          <h1 className="text-xl font-semibold mb-1" style={{ color: COLORS.ink }}>Create a patient account</h1>
          <p className="text-sm mb-6" style={{ color: COLORS.slate }}>Clinicians: ask your administrator for an account.</p>
          {error && (
            <div role="alert" className="mb-5 flex items-start gap-2 rounded-xl px-3.5 py-3 text-sm" style={{ backgroundColor: COLORS.criticalSoft, color: COLORS.critical }}>
              <XCircle className="w-4 h-4 mt-0.5 shrink-0" /> <span>{error}</span>
            </div>
          )}
          <form onSubmit={submit} className="space-y-4" noValidate>
            {field("name", "Full name", { autoComplete: "name" })}
            {field("email", "Email", { type: "email", autoComplete: "email" })}
            {field("password", "Password (8+ characters)", { type: "password", autoComplete: "new-password" })}
            {field("confirm", "Confirm password", { type: "password", autoComplete: "new-password" })}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="sex" className="block text-sm font-medium mb-1.5" style={{ color: COLORS.ink }}>Sex (optional)</label>
                <select id="sex" value={form.sex} onChange={set("sex")} className="w-full rounded-xl border px-3 py-2.5 text-sm" style={{ borderColor: COLORS.line }}>
                  <option value="">Prefer not to say</option>
                  <option value="F">Female</option>
                  <option value="M">Male</option>
                </select>
              </div>
              {field("birthYear", "Birth year (optional)", { type: "number", min: 1900, max: new Date().getFullYear() })}
            </div>
            <button type="submit" disabled={loading} className="w-full flex items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-semibold text-white disabled:opacity-70" style={{ backgroundColor: COLORS.teal }}>
              {loading && <Loader2 className="w-4 h-4 animate-spin" />} Create account
            </button>
          </form>
        </Card>
      </div>
    </div>
  );
}

export default Register;
