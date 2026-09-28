import React, { useState, useMemo } from "react";
import { UserPlus, Filter, ChevronDown, ChevronRight, ArrowUpDown } from "lucide-react";
import { COLORS } from "../styles/tokens.js";
import { Card } from "../components/shared/Card.jsx";
import { PatientTable } from "../components/patients/PatientTable.jsx";
import { AddPatientModal } from "../components/patients/AddPatientModal.jsx";

export function Patients({ patients, departments, search, onSelect, onAction, onAdd }) {
  const [deptFilter, setDeptFilter] = useState("All");
  const [priorityFilter, setPriorityFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [sortBy, setSortBy] = useState("priority");
  const [addOpen, setAddOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);

  const filtered = useMemo(() => {
    let list = patients.filter((p) => {
      const matchesSearch = !search || p.name.toLowerCase().includes(search.toLowerCase()) || p.id.toLowerCase().includes(search.toLowerCase());
      const matchesDept = deptFilter === "All" || p.department === deptFilter;
      const matchesPriority = priorityFilter === "All" || p.priority === priorityFilter;
      const matchesStatus = statusFilter === "All" || p.status === statusFilter;
      return matchesSearch && matchesDept && matchesPriority && matchesStatus;
    });
    if (sortBy === "priority") {
      const order = { Critical: 0, High: 1, Medium: 2, Low: 3 };
      list = [...list].sort((a, b) => order[a.priority] - order[b.priority]);
    } else if (sortBy === "wait") {
      list = [...list].sort((a, b) => b.waitTime - a.waitTime);
    }
    return list;
  }, [patients, search, deptFilter, priorityFilter, statusFilter, sortBy]);

  return (
    <div className="p-4 sm:p-6 space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold" style={{ color: COLORS.ink }}>Patient Queue</h1>
          <p className="text-sm" style={{ color: COLORS.slate }}>{filtered.length} of {patients.length} patients shown</p>
        </div>
        <button onClick={() => setAddOpen(true)} className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white" style={{ backgroundColor: COLORS.teal }}>
          <UserPlus className="w-4 h-4" /> Add Patient
        </button>
      </div>

      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-3">
          <button onClick={() => setFiltersOpen((v) => !v)} className="flex items-center gap-2 text-sm font-medium px-3 py-2 rounded-lg border sm:hidden" style={{ borderColor: COLORS.line, color: COLORS.ink }}>
            <Filter className="w-4 h-4" /> Filters {filtersOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
          <div className={`flex-wrap items-center gap-3 ${filtersOpen ? "flex" : "hidden"} sm:flex w-full sm:w-auto`}>
            <select value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)} aria-label="Filter by department" className="rounded-lg border px-3 py-2 text-sm bg-white" style={{ borderColor: COLORS.line, color: COLORS.ink }}>
              <option value="All">All departments</option>
              {departments.map((d) => <option key={d.id} value={d.name}>{d.name}</option>)}
            </select>
            <select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)} aria-label="Filter by priority" className="rounded-lg border px-3 py-2 text-sm bg-white" style={{ borderColor: COLORS.line, color: COLORS.ink }}>
              <option value="All">All priorities</option>
              {["Critical", "High", "Medium", "Low"].map((p) => <option key={p}>{p}</option>)}
            </select>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="Filter by status" className="rounded-lg border px-3 py-2 text-sm bg-white" style={{ borderColor: COLORS.line, color: COLORS.ink }}>
              <option value="All">All statuses</option>
              {["Waiting", "Being evaluated", "Completed", "Escalated"].map((s) => <option key={s}>{s}</option>)}
            </select>
            <div className="flex items-center gap-1.5 text-sm ml-0 sm:ml-2">
              <ArrowUpDown className="w-4 h-4" style={{ color: COLORS.slate }} />
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} aria-label="Sort by" className="rounded-lg border px-3 py-2 text-sm bg-white" style={{ borderColor: COLORS.line, color: COLORS.ink }}>
                <option value="priority">Sort: Priority</option>
                <option value="wait">Sort: Waiting time</option>
              </select>
            </div>
          </div>
        </div>
      </Card>

      <Card className="p-0 overflow-hidden">
        <PatientTable patients={filtered} departments={departments} onSelect={onSelect} onAction={onAction} />
      </Card>

      <AddPatientModal open={addOpen} onClose={() => setAddOpen(false)} onAdd={onAdd} departments={departments} />
    </div>
  );
}

export default Patients;
