import React, { useState } from "react";
import { COLORS } from "../styles/tokens.js";
import { DoctorCard } from "../components/doctors/DoctorCard.jsx";

export function Doctors({ doctors, search }) {
  const [statusFilter, setStatusFilter] = useState("All");
  const filtered = doctors.filter((d) => {
    const matchesSearch = !search || d.name.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "All" || d.status === statusFilter;
    return matchesSearch && matchesStatus;
  });
  const counts = ["Available", "Consulting", "On Break", "Unavailable"].map((s) => ({ status: s, n: doctors.filter((d) => d.status === s).length }));

  return (
    <div className="p-4 sm:p-6 space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold" style={{ color: COLORS.ink }}>Doctors &amp; Resources</h1>
          <p className="text-sm" style={{ color: COLORS.slate }}>{filtered.length} of {doctors.length} doctors shown</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {counts.map((c) => (
            <button key={c.status} onClick={() => setStatusFilter(statusFilter === c.status ? "All" : c.status)} aria-pressed={statusFilter === c.status}
              className="text-xs font-medium px-3 py-1.5 rounded-full border" style={statusFilter === c.status ? { backgroundColor: COLORS.teal, color: "white", borderColor: COLORS.teal } : { borderColor: COLORS.line, color: COLORS.slate }}>
              {c.status} ({c.n})
            </button>
          ))}
        </div>
      </div>
      <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((d) => <DoctorCard key={d.id} doctor={d} />)}
        {filtered.length === 0 && <p className="text-sm col-span-full text-center py-10" style={{ color: COLORS.slate }}>No doctors match this filter.</p>}
      </div>
    </div>
  );
}

export default Doctors;
