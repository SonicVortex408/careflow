import React, { useState } from "react";
import {
  Users,
  Clock,
  Stethoscope,
  ShieldAlert,
  Building2,
} from "lucide-react";

import { COLORS } from "../styles/tokens.js";
import { Card } from "../components/shared/Card.jsx";
import { StatCard } from "../components/dashboard/StatCard.jsx";
import {
  QueueOverview,
  QueueTimeline,
} from "../components/dashboard/QueueOverview.jsx";
import { WaitingPrediction } from "../components/dashboard/WaitingPrediction.jsx";
import { DepartmentWorkload } from "../components/dashboard/DepartmentWorkload.jsx";
import { RecommendationCard } from "../components/dashboard/Recommendations.jsx";


export function Dashboard({
  patients,
  departments,
  doctors,
  alerts,
  onSelectPatient,
  onNavigate,
}) {
  const waiting = patients.filter(
    (p) => p.status !== "Completed"
  );

  const avgWait = Math.round(
    waiting.reduce((s, p) => s + p.waitTime, 0) /
      (waiting.length || 1)
  );

  const doctorsAvailable = doctors.filter(
    (d) => d.status === "Available"
  ).length;

  const criticalCount = patients.filter(
    (p) =>
      p.priority === "Critical" &&
      p.status !== "Completed"
  ).length;

  const highLoadDepts = departments.filter(
    (d) => d.workload >= 60
  ).length;

  const topDept = [...departments].sort(
    (a, b) => b.workload - a.workload
  )[0];

  const recAlert = alerts.find(
    (a) =>
      a.type === "recommendation" &&
      a.status === "active"
  );

  const [recDismissed, setRecDismissed] =
    useState(false);

  return (
    <div className="p-4 sm:p-6 space-y-6">

      {/* =========================
          DASHBOARD HEADER
      ========================= */}

      <Card
        className="p-5 sm:p-6"
        style={{
          backgroundColor: COLORS.ink,
        }}
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">

          <div>
            <h1 className="text-xl font-semibold text-white mb-1">
              Good morning, Admin.
            </h1>

            <p
              className="text-sm"
              style={{ color: "#B7C4C2" }}
            >
              Hospital flow is currently{" "}
              {highLoadDepts >= 3
                ? "under strain"
                : "stable"}
              .
            </p>
          </div>

          <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-white">
            <span>
              <strong>{waiting.length}</strong>{" "}
              patients waiting
            </span>

            <span>
              <strong>{avgWait} min</strong>{" "}
              average wait
            </span>

            <span>
              <strong>{doctorsAvailable} doctors</strong>{" "}
              available
            </span>

            <span>
              <strong>{highLoadDepts}</strong>{" "}
              departments under high load
            </span>
          </div>

        </div>
      </Card>


      {/* =========================
          STAT CARDS
      ========================= */}

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">

        <StatCard
          icon={Users}
          label="Patients waiting"
          value={waiting.length}
          trend="8%"
          trendDir="up"
          accent={{
            soft: COLORS.blueSoft,
            fg: COLORS.blue,
          }}
        />

        <StatCard
          icon={Clock}
          label="Average wait"
          value={`${avgWait} min`}
          trend="12%"
          trendDir="down"
          accent={{
            soft: COLORS.tealSoft,
            fg: COLORS.teal,
          }}
        />

        <StatCard
          icon={Stethoscope}
          label="Doctors available"
          value={`${doctorsAvailable} / ${doctors.length}`}
          accent={{
            soft: COLORS.successSoft,
            fg: COLORS.success,
          }}
        />

        <StatCard
          icon={ShieldAlert}
          label="Critical patients"
          value={criticalCount}
          sub="Require priority attention"
          accent={{
            soft: COLORS.criticalSoft,
            fg: COLORS.critical,
          }}
        />

        <StatCard
          icon={Building2}
          label="Departments under load"
          value={highLoadDepts}
          sub="High workload"
          accent={{
            soft: COLORS.warningSoft,
            fg: COLORS.warning,
          }}
        />

      </div>


      {/* =========================
          RECOMMENDATION
      ========================= */}

      {recAlert && !recDismissed && (
        <RecommendationCard
          recommendation={recAlert}
          onDismiss={() => setRecDismissed(true)}
        />
      )}


      {/* =========================
          QUEUE
      ========================= */}

      <div className="grid lg:grid-cols-3 gap-6">

        <div className="lg:col-span-2">
          <QueueOverview
            patients={patients}
            departments={departments}
            onSelectPatient={onSelectPatient}
            onNavigate={onNavigate}
          />
        </div>

        <QueueTimeline
          patients={patients}
        />

      </div>


      {/* =========================
          PREDICTION + DEPARTMENTS
      ========================= */}

      <div className="grid lg:grid-cols-2 gap-6">

        <WaitingPrediction
          dept={topDept}
        />

        <DepartmentWorkload
          departments={departments}
          onSelect={() =>
            onNavigate("departments")
          }
        />

      </div>

    </div>
  );
}

export default Dashboard;

