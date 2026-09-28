import React from "react";
import { COLORS } from "../styles/tokens.js";
import { WAIT_TREND, FLOW_STAGES } from "../data/mockData.js";
import { WaitingTimeChart } from "../components/analytics/WaitingTimeChart.jsx";
import { WorkloadChart } from "../components/analytics/WorkloadChart.jsx";
import { PatientFlowChart } from "../components/analytics/PatientFlowChart.jsx";
import { UtilizationChart } from "../components/analytics/UtilizationChart.jsx";

export function Analytics({ departments, doctors }) {
  return (
    <div className="p-4 sm:p-6 space-y-6">
      <div>
        <h1 className="text-lg font-semibold" style={{ color: COLORS.ink }}>Analytics</h1>
        <p className="text-sm" style={{ color: COLORS.slate }}>Hospital performance trends over today</p>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <WaitingTimeChart data={WAIT_TREND} />
        <WorkloadChart departments={departments} />
        <PatientFlowChart data={FLOW_STAGES} />
        <UtilizationChart doctors={doctors} />
      </div>
    </div>
  );
}

export default Analytics;
