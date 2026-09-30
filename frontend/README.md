# CareFlow — Smart Hospital Queue & Resource Management

A React + Tailwind frontend prototype for intelligent hospital queue and
resource management. Mock auth, mock data, deterministic queue simulation —
no backend required.

## Structure

```
src/
├── components/
│   ├── layout/       Sidebar, Header
│   ├── dashboard/     StatCard, QueueOverview, WaitingPrediction,
│   │                  DepartmentWorkload, Recommendations, Alerts
│   ├── patients/      PatientTable, PatientDetails, AddPatientModal,
│   │                  PatientRowActions, PriorityBadge
│   ├── doctors/       DoctorCard, ResourceStatus
│   ├── analytics/     ChartCard + 4 Recharts-based charts
│   └── shared/        Card, Badges, Brand (logo/vitals mark), ConfirmDialog
├── data/mockData.js    all mock patients, doctors, departments, alerts…
├── utils/queueLogic.js priority scoring + wait-time prediction (deterministic)
├── services/           mock API abstractions, ready to swap for real HTTP calls
├── pages/               one file per top-level screen
├── App.jsx              app shell, state, routing (no react-router needed —
│                         simple key-based page switch), simulation loop
└── main.jsx              Vite/React entry point
```

## Run it

```bash
npm install
npm run dev
```

Login with any valid email and any password (use `wrong` as the password to
see the error state).

## Disclaimer

CareFlow provides operational estimates and queue-management recommendations.
It does not diagnose patients, determine medical treatment, or replace
clinical triage and professional medical judgment. All patient data is
fictional.
