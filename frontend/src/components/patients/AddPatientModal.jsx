import React, { useState, useEffect } from "react";
import { X } from "lucide-react";
import { COLORS } from "../../styles/tokens.js";
import { PRIORITY_STYLE } from "../shared/Badges.jsx";

export function AddPatientModal({ open, onClose, onAdd, departments }) {
  const [form, setForm] = useState({ name: "", age: "", department: departments[0]?.name || "", appointment: "Walk-in", arrivalTime: "", priority: "Medium", symptoms: "" });
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (open) {
      const now = new Date();
      let h = now.getHours(); const m = now.getMinutes();
      const mer = h >= 12 ? "PM" : "AM"; h = h % 12 || 12;
      setForm((f) => ({ ...f, arrivalTime: `${h}:${String(m).padStart(2, "0")} ${mer}`, name: "", age: "", symptoms: "" }));
      setErrors({});
    }
  }, [open]);

  if (!open) return null;

  const validate = () => {
    const errs = {};
    if (!form.name.trim()) errs.name = "Full name is required.";
    if (!form.age || Number(form.age) <= 0 || Number(form.age) > 120) errs.age = "Enter a valid age.";
    if (!form.symptoms.trim()) errs.symptoms = "Please describe the reason for visit.";
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const submit = (e) => {
    e.preventDefault();
    if (!validate()) return;
    const newPatient = {
      id: `P${Math.floor(1050 + Math.random() * 900)}`,
      name: form.name.trim(),
      age: Number(form.age),
      department: form.department,
      priority: form.priority,
      appointment: form.appointment,
      arrivalTime: form.arrivalTime,
      waitTime: 1,
      doctor: "Unassigned",
      status: "Waiting",
      timeline: [{ time: form.arrivalTime, label: "Patient registered" }],
      symptoms: form.symptoms.trim(),
    };
    // eslint-disable-next-line no-console
    console.log("New patient submitted:", newPatient);
    onAdd(newPatient);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} aria-hidden="true" />
      <div role="dialog" aria-modal="true" aria-labelledby="add-patient-title" className="relative bg-white rounded-t-2xl sm:rounded-2xl w-full sm:max-w-lg max-h-[90vh] overflow-y-auto shadow-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b sticky top-0 bg-white" style={{ borderColor: COLORS.line }}>
          <h2 id="add-patient-title" className="text-base font-semibold" style={{ color: COLORS.ink }}>Add Patient</h2>
          <button onClick={onClose} aria-label="Close" className="p-1.5 rounded-lg hover:bg-slate-100"><X className="w-5 h-5" /></button>
        </div>
        <form onSubmit={submit} className="p-5 space-y-4" noValidate>
          <div>
            <label htmlFor="pname" className="block text-sm font-medium mb-1.5" style={{ color: COLORS.ink }}>Full Name</label>
            <input id="pname" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full rounded-xl border px-3.5 py-2.5 text-sm outline-none focus:ring-2" style={{ borderColor: errors.name ? COLORS.critical : COLORS.line, "--tw-ring-color": COLORS.teal }} />
            {errors.name && <p className="mt-1.5 text-xs" style={{ color: COLORS.critical }}>{errors.name}</p>}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="page" className="block text-sm font-medium mb-1.5" style={{ color: COLORS.ink }}>Age</label>
              <input id="page" type="number" value={form.age} onChange={(e) => setForm({ ...form, age: e.target.value })} className="w-full rounded-xl border px-3.5 py-2.5 text-sm outline-none focus:ring-2" style={{ borderColor: errors.age ? COLORS.critical : COLORS.line, "--tw-ring-color": COLORS.teal }} />
              {errors.age && <p className="mt-1.5 text-xs" style={{ color: COLORS.critical }}>{errors.age}</p>}
            </div>
            <div>
              <label htmlFor="ptime" className="block text-sm font-medium mb-1.5" style={{ color: COLORS.ink }}>Arrival Time</label>
              <input id="ptime" value={form.arrivalTime} onChange={(e) => setForm({ ...form, arrivalTime: e.target.value })} className="w-full rounded-xl border px-3.5 py-2.5 text-sm outline-none focus:ring-2" style={{ borderColor: COLORS.line, "--tw-ring-color": COLORS.teal }} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="pdept" className="block text-sm font-medium mb-1.5" style={{ color: COLORS.ink }}>Department</label>
              <select id="pdept" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} className="w-full rounded-xl border px-3.5 py-2.5 text-sm outline-none focus:ring-2 bg-white" style={{ borderColor: COLORS.line, "--tw-ring-color": COLORS.teal }}>
                {departments.map((d) => <option key={d.id} value={d.name}>{d.name}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="pappt" className="block text-sm font-medium mb-1.5" style={{ color: COLORS.ink }}>Appointment type</label>
              <select id="pappt" value={form.appointment} onChange={(e) => setForm({ ...form, appointment: e.target.value })} className="w-full rounded-xl border px-3.5 py-2.5 text-sm outline-none focus:ring-2 bg-white" style={{ borderColor: COLORS.line, "--tw-ring-color": COLORS.teal }}>
                <option>Walk-in</option>
                <option>Scheduled</option>
              </select>
            </div>
          </div>
          <div>
            <span className="block text-sm font-medium mb-1.5" style={{ color: COLORS.ink }}>Priority</span>
            <div className="flex flex-wrap gap-2">
              {["Critical", "High", "Medium", "Low"].map((p) => (
                <button type="button" key={p} onClick={() => setForm({ ...form, priority: p })} aria-pressed={form.priority === p}
                  className="px-3 py-1.5 rounded-full text-xs font-semibold border transition"
                  style={form.priority === p ? { backgroundColor: PRIORITY_STYLE[p].fg, color: "white", borderColor: PRIORITY_STYLE[p].fg } : { backgroundColor: "white", color: COLORS.slate, borderColor: COLORS.line }}>
                  {p}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label htmlFor="psymp" className="block text-sm font-medium mb-1.5" style={{ color: COLORS.ink }}>Symptoms / Reason for visit</label>
            <textarea id="psymp" rows={3} value={form.symptoms} onChange={(e) => setForm({ ...form, symptoms: e.target.value })} className="w-full rounded-xl border px-3.5 py-2.5 text-sm outline-none focus:ring-2 resize-none" style={{ borderColor: errors.symptoms ? COLORS.critical : COLORS.line, "--tw-ring-color": COLORS.teal }} />
            {errors.symptoms && <p className="mt-1.5 text-xs" style={{ color: COLORS.critical }}>{errors.symptoms}</p>}
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 rounded-xl py-2.5 text-sm font-semibold border" style={{ borderColor: COLORS.line, color: COLORS.slate }}>Cancel</button>
            <button type="submit" className="flex-1 rounded-xl py-2.5 text-sm font-semibold text-white" style={{ backgroundColor: COLORS.teal }}>Add to queue</button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AddPatientModal;
