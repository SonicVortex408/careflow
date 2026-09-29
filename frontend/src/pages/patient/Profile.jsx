import React, { useState } from "react";
import { CheckCircle2 } from "lucide-react";

import { COLORS } from "../../styles/tokens.js";
import { updateProfile } from "../../services/authService.js";
import { Card } from "../../components/shared/Card.jsx";

export function Profile({ user, onUpdated }) {
  const [sex, setSex] = useState(user?.sex || "");
  const [birthYear, setBirthYear] = useState(user?.birthYear || "");
  const [status, setStatus] = useState("");

  const save = async (e) => {
    e.preventDefault();
    setStatus("");
    try {
      const updated = await updateProfile({ sex: sex || null, birthYear: birthYear ? Number(birthYear) : null });
      onUpdated?.(updated);
      setStatus("saved");
    } catch (err) {
      setStatus(err.message);
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-xl mx-auto space-y-5">
      <h1 className="text-2xl font-bold" style={{ color: COLORS.ink }}>My profile</h1>
      <Card className="p-6">
        <dl className="text-sm mb-5 space-y-1" style={{ color: COLORS.ink }}>
          <div><dt className="inline font-semibold">Name: </dt><dd className="inline">{user?.name}</dd></div>
          <div><dt className="inline font-semibold">Email: </dt><dd className="inline">{user?.email}</dd></div>
        </dl>
        <form onSubmit={save} className="space-y-4">
          <p className="text-xs" style={{ color: COLORS.slate }}>Sex and birth year are used for sex-specific lab ranges (for example ferritin) and cohort comparisons.</p>
          <div>
            <label htmlFor="sex" className="block text-sm font-medium mb-1" style={{ color: COLORS.ink }}>Sex recorded on lab reports</label>
            <select id="sex" value={sex} onChange={(e) => setSex(e.target.value)} className="w-full rounded-xl border px-3 py-2 text-sm" style={{ borderColor: COLORS.line }}>
              <option value="">Prefer not to say</option>
              <option value="F">Female</option>
              <option value="M">Male</option>
            </select>
          </div>
          <div>
            <label htmlFor="by" className="block text-sm font-medium mb-1" style={{ color: COLORS.ink }}>Birth year</label>
            <input id="by" type="number" min={1900} max={new Date().getFullYear()} value={birthYear} onChange={(e) => setBirthYear(e.target.value)}
              className="w-full rounded-xl border px-3 py-2 text-sm" style={{ borderColor: COLORS.line }} />
          </div>
          <button type="submit" className="rounded-xl px-4 py-2.5 text-sm font-semibold text-white" style={{ backgroundColor: COLORS.teal }}>Save</button>
          {status === "saved" && <p className="flex items-center gap-1.5 text-sm" style={{ color: COLORS.success }}><CheckCircle2 className="w-4 h-4" /> Saved</p>}
          {status && status !== "saved" && <p role="alert" className="text-sm" style={{ color: COLORS.critical }}>{status}</p>}
        </form>
      </Card>
    </div>
  );
}

export default Profile;
