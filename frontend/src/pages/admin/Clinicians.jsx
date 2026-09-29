import React, { useEffect, useState } from "react";
import { UserPlus } from "lucide-react";

import { COLORS } from "../../styles/tokens.js";
import { createClinician, listClinicians } from "../../services/adminService.js";
import { Card } from "../../components/shared/Card.jsx";

export function Clinicians() {
  const [list, setList] = useState([]);
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [msg, setMsg] = useState("");

  useEffect(() => { listClinicians().then(setList).catch((e) => setMsg(e.message)); }, []);

  const submit = async (e) => {
    e.preventDefault();
    setMsg("");
    try {
      const c = await createClinician(form);
      setList((l) => [c, ...l]);
      setForm({ name: "", email: "", password: "" });
      setMsg(`Created ${c.email}`);
    } catch (err) {
      setMsg(err.message);
    }
  };

  const field = (k, label, type = "text") => (
    <div>
      <label htmlFor={k} className="block text-sm font-medium mb-1" style={{ color: COLORS.ink }}>{label}</label>
      <input id={k} type={type} value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} required minLength={k === "password" ? 8 : undefined}
        className="w-full rounded-xl border px-3 py-2 text-sm" style={{ borderColor: COLORS.line }} />
    </div>
  );

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto space-y-5">
      <h1 className="text-2xl font-bold" style={{ color: COLORS.ink }}>Clinician accounts</h1>
      <p className="text-sm" style={{ color: COLORS.slate }}>Clinician accounts are invite-only. Share the temporary password securely.</p>
      <Card className="p-6">
        <form onSubmit={submit} className="grid gap-4 sm:grid-cols-3 items-end">
          {field("name", "Name")}
          {field("email", "Email", "email")}
          {field("password", "Temporary password", "password")}
          <button type="submit" className="sm:col-span-3 inline-flex w-fit items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white" style={{ backgroundColor: COLORS.teal }}>
            <UserPlus className="w-4 h-4" /> Create clinician
          </button>
        </form>
        {msg && <p className="mt-3 text-sm" style={{ color: COLORS.slate }}>{msg}</p>}
      </Card>
      <Card className="p-5">
        <ul className="divide-y" style={{ borderColor: COLORS.line }}>
          {list.map((c) => (
            <li key={c.id} className="py-2.5 text-sm flex justify-between" style={{ color: COLORS.ink }}>
              <span className="font-medium">{c.name}</span><span style={{ color: COLORS.slate }}>{c.email}</span>
            </li>
          ))}
          {list.length === 0 && <li className="py-2 text-sm" style={{ color: COLORS.slate }}>No clinicians yet.</li>}
        </ul>
      </Card>
    </div>
  );
}

export default Clinicians;
