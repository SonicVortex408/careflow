# Domain-mismatch inventory and disposition proposal (Step 0.2)

Nothing has been deleted or moved. This is a proposal for your approval.

Legend — **KEEP** (unchanged) · **ADAPT** (rewrite in-place for the lab/biomarker
domain) · **QUARANTINE** (move to `legacy/` or hide behind a feature flag) ·
**REMOVE**.

## A. E-commerce content in `ai-service/`

| Item | Disposition | Rationale |
|---|---|---|
| `sample_docs/knowledge-base/01-…-15-*.md` (returns, shipping, warranty, tumbler card, TrailPlus, internal notes) | **REMOVE** | 15 files, zero medical value. Replaced in Phase 1 by a 9-biomarker Markdown KB with cited sources. |
| `sample_docs/data/orders.json`, `orders-data-dictionary.md` | **REMOVE** | Only consumers are the two order tools, also removed. |
| `sample_docs/evaluation/visible-cases.json` | **ADAPT** | Good harness shape (`must_include` / `required_sources` / `forbidden_sources_as_authority` / `tool` / `handoff`). Rewrite the cases as lab-interpretation + guardrail cases; keep the schema. |
| `agent/tools.py::check_order_status`, `::calculate_return_eligibility` | **REMOVE** | Pure e-commerce. |
| `agent/tools.py::search_docs` | **ADAPT** | Keep as the vector-retrieval fallback required in Phase 3; add metadata filtering (see below). |
| `SYSTEM_PROMPT` first line "You are the Aster & Row customer support agent" + the "GLOBAL KNOWLEDGE SOURCE RULES" / "policy_authority" block | **ADAPT** | The medical-safety, privacy, and prompt-injection sections are genuinely good and should survive. The persona line and the policy-authority rules must be rewritten to "evidence_level / source" semantics. |
| `handoff_check` prose substring matching | **ADAPT** | Becomes the deterministic escalation rule engine in `guardrails.py` (`escalation_required`). |
| `src/ai_service/__init__.py` "Hello from ai-service!" + `[project.scripts]` | **REMOVE** | Dead scaffold pointing at a package that does not contain the app. |
| `app/core/config.py` (empty) | **ADAPT** | Fill it with a pydantic-settings `Settings` object; every new env var goes through it. |

## B. Queue-management UI in `frontend/`

The instruction is "Queue-management pages handled per Step 0 decision".
**Recommendation: QUARANTINE now, REMOVE in Phase 4** — this keeps the Vercel
deployment visually intact while PolyMarker pages are built, and avoids a large
delete landing in the same PR as new features.

Mechanism: move to `src/legacy/` and gate behind `VITE_ENABLE_LEGACY_QUEUE`
(default `false`), so `mockData.js` stops being bundled in the default build.

| Item | Disposition |
|---|---|
| `pages/{Dashboard,Patients,Departments,Doctors,Analytics,Alerts}.jsx` | **QUARANTINE → REMOVE in Phase 4** |
| `components/dashboard/*`, `components/doctors/*`, `components/patients/{AddPatientModal,PatientDetails,PatientRowActions,PatientTable,PriorityBadge}.jsx` | **QUARANTINE → REMOVE in Phase 4** |
| `data/mockData.js`, `utils/queueLogic.js` | **REMOVE in Phase 4** (explicitly required: "delete unused mockData") |
| `services/{patientService,doctorService,queueService,analyticsService}.js` | **REMOVE** — `Promise.resolve(MOCK)` stubs with no real backend behind them |
| `components/analytics/{ChartCard,PatientFlowChart,UtilizationChart,WaitingTimeChart,WorkloadChart}.jsx` | **ADAPT** — `ChartCard` is the reusable Recharts wrapper the biomarker gauges / radar / cohort-scatter should reuse; the four queue-specific charts go with the rest |
| `components/shared/{Card,Badges,ConfirmDialog,PulseDot,Brand}.jsx`, `styles/tokens.js` | **KEEP** — the design system, reused as-is |
| `components/layout/{Header,Sidebar}.jsx` | **ADAPT** — keep the shell, replace nav items; Sidebar becomes role-driven (patient / clinician) |
| `pages/{Login,Register,Settings}.jsx` | **KEEP / light ADAPT** — add the clinician role to the role selector |
| `components/patients/PatientPortal.jsx` | **ADAPT** — becomes the patient shell hosting upload, symptom intake, and the biomarker dashboard |
| `pages/AIAssistant.jsx` (1,211 lines) | **ADAPT** — explicitly "integrate with the existing AI assistant page rather than duplicating it". Also split it; it is far too large. |
| Hardcoded `https://careflow-gwxc.onrender.com/api` × 3 files | **ADAPT (blocking)** — single `src/services/apiClient.js` reading `import.meta.env.VITE_API_BASE_URL`. Required by "API base URLs must come from env". |
| `index.html` title "CareFlow — Smart Hospital Queue & Resource Management" | **ADAPT** — rebrand in Phase 4 |
| `package.json` dependency on `cors` | **REMOVE** — server-only package in a browser bundle |

## C. `backend/`

| Item | Disposition |
|---|---|
| auth / users / conversations / messages / documents | **KEEP** |
| `Admin` model + `adminOnly` middleware | **ADAPT** — becomes the `clinician` role. Proposal: add `role: "patient" \| "clinician"` to `User` and keep `Admin` for platform administration, rather than a third collection. |
| `POST /api/auth/admin/register` (unauthenticated) | **REMOVE** the public route; seed the first clinician via a script, then invite-only |
| `console.log(token)` in `authController.loginUser` | **REMOVE** |
| `src/middleware/errorMiddleware.js` (empty, never mounted) | **ADAPT** — implement and mount it |
| Synchronous `readFileSync` + blocking proxy in `documentController` | **ADAPT** — becomes "enqueue job, return `job_id`, poll status" in Phase 1 |

## D. Cross-cutting, not domain-mismatched but blocking

| Gap | Where it lands |
|---|---|
| No `.env.example` anywhere | Phase 1 |
| No `docker-compose.yml` | Phase 1 (required by the acceptance criteria) |
| No test runner in any service | Phase 1 — add `pytest` + `ruff` to ai-service, `vitest` to frontend, `node:test` or vitest to backend |
| Retrieval returns `status: internal` documents as the top hit | Phase 1/3 — enforce metadata filtering in the retriever, not only in the prompt |
| `init_chat_model` at import time crashes the app without a key | Phase 1 — lazy/`@lru_cache` provider factory, `LLM_PROVIDER` env-configurable |
| In-memory LangGraph checkpointer | Phase 3 — Redis/Mongo checkpointer once Redis exists |

## Status after implementation

Approved as "APPROVE and ADAPT" (queue-management shell repurposed rather than quarantined).

| Item | Outcome |
|---|---|
| E-commerce KB, orders data, order tools, `src/ai_service` scaffold | Removed; medical knowledge base in `ai-service/knowledge_base/` |
| `visible-cases.json` | Adapted: schema kept in `evaluation/cases/assistant_cases.json` (10 lab-interpretation / safety cases, all passing) |
| `search_docs` | Adapted into `search_knowledge_base` with metadata filtering in code |
| System prompt | Rewritten for PolyMarker; safety, privacy and injection rules kept; policy-authority rules replaced by evidence levels |
| `handoff_check` | Replaced by deterministic escalation rules in `guardrails.py` |
| `app/core/config.py` | pydantic-settings `Settings` |
| Queue pages, dashboard/doctor/patient components, `mockData.js`, `queueLogic.js`, mock services | Removed; replaced by patient / clinician / admin pages |
| `ChartCard`, shared components, tokens | Kept and reused |
| Sidebar / Header | Role-driven |
| `PatientPortal.jsx` | Superseded by the role-driven shell and patient pages |
| `AIAssistant.jsx` | Split into `components/assistant/*` |
| Hardcoded Render URL ×3 | Removed; `services/apiClient.js` + `VITE_API_BASE_URL` (CI guard) |
| `index.html` title, `cors` dependency | Rebranded; removed |
| Admin model / public admin register / `console.log(token)` | Admin kept for platform admins; public route removed (seed + admin-created clinicians); log removed |
| `errorMiddleware.js` | Implemented and mounted |
| Synchronous document proxy | Async jobs (`202` + polling) for reports and documents |
| `.env.example`, docker-compose, test runners, CI | Added |
| Retrieval returning internal docs | Fixed in code; evaluated (0 leaks) |
| Import-time LLM construction | Lazy factory |
| In-memory checkpointer | Redis Stack checkpointer (memory fallback) |
