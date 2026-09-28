import React from "react";
import { COLORS } from "../../styles/tokens.js";
import { Card } from "../shared/Card.jsx";
import { WorkloadTag } from "../shared/Badges.jsx";
import { workloadStatus } from "../../utils/queueLogic.js";

export function DepartmentWorkload({ departments, onSelect }) {
  return (
    <Card className="p-5">
      <h3 className="text-sm font-semibold mb-4" style={{ color: COLORS.ink }}>Department Workload</h3>
      <div className="space-y-3">
        {departments.map((d) => (
          <button
            key={d.id}
            onClick={() => onSelect?.(d)}
            className="w-full text-left p-3 rounded-xl border hover:border-slate-300 transition focus:outline-none focus-visible:ring-2"
            style={{ borderColor: COLORS.line, "--tw-ring-color": COLORS.teal }}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold" style={{ color: COLORS.ink }}>{d.name}</span>
              <WorkloadTag status={workloadStatus(d.workload)} />
            </div>
            <div className="w-full h-1.5 rounded-full mb-2" style={{ backgroundColor: "#EEF2F1" }}>
              <div className="h-1.5 rounded-full transition-all" style={{ width: `${d.workload}%`, backgroundColor: d.workload >= 80 ? COLORS.critical : d.workload >= 60 ? COLORS.warning : COLORS.teal }} />
            </div>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs" style={{ color: COLORS.slate }}>
              <span>Queue: {d.queue}</span>
              <span>Doctors: {d.doctorsAvailable}/{d.doctorsTotal}</span>
              <span>Wait: {d.waitTime} min</span>
              <span>Workload: {d.workload}%</span>
            </div>
          </button>
        ))}
      </div>
    </Card>
  );
}

export default DepartmentWorkload;
