import React from "react";
import { COLORS } from "../styles/tokens.js";
import { Card } from "../components/shared/Card.jsx";
import { WorkloadTag } from "../components/shared/Badges.jsx";
import { workloadStatus } from "../utils/queueLogic.js";

export function Departments({ departments, doctors }) {
  return (
    <div className="p-4 sm:p-6 space-y-5">
      <div>
        <h1 className="text-lg font-semibold" style={{ color: COLORS.ink }}>Departments</h1>
        <p className="text-sm" style={{ color: COLORS.slate }}>Workload and staffing across all departments</p>
      </div>
      <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {departments.map((d) => {
          const status = workloadStatus(d.workload);
          const deptDoctors = doctors.filter((doc) => doc.department === d.name);
          return (
            <Card key={d.id} className="p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold" style={{ color: COLORS.ink }}>{d.name}</h3>
                <WorkloadTag status={status} />
              </div>
              <div className="w-full h-2 rounded-full mb-4" style={{ backgroundColor: "#EEF2F1" }}>
                <div className="h-2 rounded-full" style={{ width: `${d.workload}%`, backgroundColor: d.workload >= 80 ? COLORS.critical : d.workload >= 60 ? COLORS.warning : COLORS.teal }} />
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm mb-4">
                <div><div className="text-xs" style={{ color: COLORS.slate }}>Queue</div><div className="font-semibold" style={{ color: COLORS.ink }}>{d.queue} patients</div></div>
                <div><div className="text-xs" style={{ color: COLORS.slate }}>Doctors</div><div className="font-semibold" style={{ color: COLORS.ink }}>{d.doctorsAvailable} / {d.doctorsTotal}</div></div>
                <div><div className="text-xs" style={{ color: COLORS.slate }}>Avg. wait</div><div className="font-semibold" style={{ color: COLORS.ink }}>{d.waitTime} min</div></div>
                <div><div className="text-xs" style={{ color: COLORS.slate }}>Workload</div><div className="font-semibold" style={{ color: COLORS.ink }}>{d.workload}%</div></div>
              </div>
              <div className="pt-3 border-t" style={{ borderColor: COLORS.line }}>
                <div className="text-xs mb-2" style={{ color: COLORS.slate }}>Staff on duty</div>
                <div className="flex flex-wrap gap-1.5">
                  {deptDoctors.map((doc) => (
                    <span key={doc.id} className="text-xs px-2 py-1 rounded-full" style={{ backgroundColor: "#F1F4F3", color: COLORS.ink }}>{doc.name}</span>
                  ))}
                  {deptDoctors.length === 0 && <span className="text-xs" style={{ color: COLORS.slate }}>No staff assigned</span>}
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

export default Departments;
