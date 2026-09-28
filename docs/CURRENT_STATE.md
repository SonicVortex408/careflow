# careFlow — Current State Audit (Step 0)

Audit performed on the `careFlow-master.zip` snapshot supplied on 2026-09-28.
No code was changed. Everything below was verified by reading the source and by
running the services locally unless explicitly marked as an inference.

**Important:** the archive contains **no `.git` directory**, so git history could
not be inspected (commit-level secret scanning, blame, and branch state are
unavailable). See "Secrets" below.

---

## 1. Repository layout

```
careFlow-master/
├── .gitignore
├── ai-service/     Python 3.11, FastAPI + LangGraph + FAISS (uv project)
├── backend/        Node.js ESM, Express 5 + Mongoose 8 (API gateway)
└── frontend/       Vite 5 + React 18 (JSX) + Tailwind 3
```

There is no root `package.json`, no `docker-compose.yml`, no CI config, no
`.env.example`, and no `docs/` directory.

---

## 2. Service-by-service

### 2.1 `ai-service/` (Python)

| Item | Value |
|---|---|
| Python | `>=3.11` (`.python-version` = 3.11) |
| Package manager | `uv` (`uv.lock` present), build backend `uv_build` |
| Web framework | FastAPI `>=0.141.1`, served by `uvicorn[standard]` |
| Agent framework | `langgraph>=1.2.11`, `langchain>=1.3.18` |
| LLM | **Groq**, hardcoded model `groq:openai/gpt-oss-20b` (`app/agent/nodes.py:27`) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` via `langchain-huggingface` (local, CPU) |
| Vector store | FAISS (`faiss-cpu`), on-disk directories |
| Container port | `EXPOSE 8080`, `CMD ... --port ${PORT:-8080}` |

**Routes**

| Method | Path | Handler |
|---|---|---|
| GET | `/` | liveness stub |
| POST | `/api/chat/` | `app/api/chat.py` — body `{message, thread_id, patient_id}` → `{response}` |
| POST | `/api/documents/process` | `app/api/documents.py` — multipart `file`, `patient_id`, `document_id` |

**Agent graph** (`app/agent/graph.py`) — compiled with an `InMemorySaver`
checkpointer (conversation memory is **lost on restart** and is **not shared
across replicas**):

```
START → llm_call → (tool_calls?) → tool_node → llm_call
                 → (no tool_calls) → handoff_check → (handoff?) → handoff → END
                                                    → END
```

`MessagesState` = `{messages, llm_calls, handoff_required, patient_id}`.

**Tools** (`app/agent/tools.py`) — three, two of which are e-commerce:
`search_docs` (FAISS over `sample_docs/`), `check_order_status`, and
`calculate_return_eligibility` (both read `sample_docs/data/orders.json`).

**Retrieval**
- Global KB: `app/retrieval/ingest.py` reads `sample_docs/**/*.md` and `**/*.pdf`,
  parses YAML-ish front matter into metadata, chunks Markdown to ~500 chars by
  paragraph accumulation and PDFs by a naive 500-char slice, writes
  `faiss_index/`. Run via `python -m app.retrieval.ingest` (also baked into the
  Docker image build).
- Per-patient KB: `app/retrieval/patient_ingest.py` uses
  `RecursiveCharacterTextSplitter(500/100)` and writes **one FAISS index per
  patient** under `patient_faiss/<patient_id>/`; raw files land in
  `patient_documents/<patient_id>/`. `patient_retriever.get_patient_retriever`
  returns `k=5`, or `None` when the patient has no index.
- Both indexes are loaded with `allow_dangerous_deserialization=True`.

**System prompt** (`app/agent/nodes.py`) — the first line still says
*"You are the Aster & Row customer support agent"*, then contains a long block
of medical-safety, patient-privacy, prompt-injection and source-authority rules.
It is a **hybrid of the e-commerce original and a medical retrofit**.

### 2.2 `backend/` (Node/Express)

| Item | Value |
|---|---|
| Runtime | Node ESM (`"type": "module"`), no engines field |
| Framework | Express `^5.1.0` |
| DB | MongoDB via Mongoose `^8.18.0` |
| Auth | JWT (`jsonwebtoken`), bcryptjs, 7-day expiry |
| Uploads | `multer` disk storage → `uploads/medical-documents/`, 10 MB cap, PDF + `text/plain` only |
| Default port | `5000` |

**Env vars** (`src/config/env.js`): `PORT`, `MONGO_URI`, `JWT_SECRET`,
`AI_SERVICE_URL` (default `http://localhost:8000`), `NODE_ENV`, plus
`FRONTEND_URL` read directly in `src/app.js` for CORS.

**Routes**

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/auth/register` | — | user |
| POST | `/api/auth/login` | — | user |
| POST | `/api/auth/admin/register` | — | **unprotected admin self-registration** |
| POST | `/api/auth/admin/login` | — | admin |
| GET | `/api/users/profile` | JWT | |
| GET | `/api/admin/profile` | JWT + adminOnly | |
| POST | `/api/ai/chat` | JWT | persists messages, proxies to ai-service |
| POST | `/api/ai/documents` | JWT (role `user` only) | multer → forwards to ai-service |
| GET/POST | `/api/conversations` | JWT | list / create |
| GET | `/api/conversations/:id/messages` | JWT | |

**Models**: `User{name,email,password}`, `Admin{name,email,password}` (two
separate collections, not one role field), `Conversation{user,title,threadId}`,
`Message{conversation,role,content}`,
`Document{user,originalName,filename,mimeType,size,storagePath,status}` with
status enum `uploaded|processing|ready|failed`.

**Auth model**: `generateToken(id, role)` signs `{id, role}` where role is
literally `"user"` or `"admin"`; `authMiddleware` looks the account up in the
matching collection and sets `req.account` / `req.role`. There is **no
clinician role**.

### 2.3 `frontend/` (React + Vite)

| Item | Value |
|---|---|
| Build | Vite `^5.2.0`, `@vitejs/plugin-react` |
| UI | React 18 JSX, Tailwind `^3.4.3`, `lucide-react` icons |
| Charts | **Recharts `^2.12.0`** (used in `components/analytics/*`) |
| Markdown | `react-markdown` + `remark-gfm` (AI assistant bubbles) |
| Routing | **None** — no `react-router`; `App.jsx` switches on a `page` string |
| Design tokens | `src/styles/tokens.js` → `COLORS` object (teal/blue/slate palette) |

`App.jsx` is a single ~700-line component holding all admin state. Role
branching: `role === "user"` renders `PatientPortal` (its own sidebar:
Dashboard / Appointments / Medical Records / CareFlow AI / My Profile);
`role === "admin"` renders the queue-management shell (Dashboard / Patient Queue
/ Departments / Doctors & Resources / Analytics / Alerts / AI Assistant /
Settings).

`pages/AIAssistant.jsx` (1,211 lines) is the only page wired to the real
backend: conversation list, message history, streaming-free chat, and a document
upload control. Everything else reads `src/data/mockData.js` through
`services/{patient,doctor,queue,analytics}Service.js`, which are `Promise.resolve`
stubs.

---

## 3. How the services communicate

```
Browser ──HTTPS──> backend (Express)  ──HTTP──> ai-service (FastAPI)
                        │
                        └──> MongoDB
```

- Frontend → backend: **hardcoded** `https://careflow-gwxc.onrender.com/api`,
  duplicated verbatim in `services/authService.js`, `services/aiService.js`, and
  `services/conversationService.js`. **No `import.meta.env` usage anywhere** —
  this directly blocks the "API base URLs must come from env" requirement.
- Backend → ai-service: `AI_SERVICE_URL`, defaulting to `http://localhost:8000`
  while the ai-service Dockerfile exposes **8080**. The default is wrong for the
  containerised setup.
- CORS: ai-service hardcodes three origins (localhost:5173 and two Vercel
  deployment URLs) in `app/main.py`; backend builds its list from
  `FRONTEND_URL`.
- Deployment (inferred from the URLs, not from config in the repo): frontend on
  Vercel (`careflow-pearl-pi.vercel.app`), backend on Render
  (`careflow-gwxc.onrender.com`), ai-service location unknown. There are no
  `vercel.json`, `render.yaml`, or Procfiles in the archive.

---

## 4. Verification performed

| Check | Result |
|---|---|
| `npm install && npm run build` (frontend) | **Passes.** 2,500 modules, 766 kB JS bundle (chunk-size warning). |
| `npm install` + `import ./src/app.js` (backend) | **Passes.** Server start not attempted — needs a live `MONGO_URI`. |
| `uv sync` (ai-service) | **Passes** (installs torch + transformers, ~large). |
| `python -m app.retrieval.ingest` | **Passes** — 48 chunks, FAISS index written. |
| `python -m app.retrieval.test_retriever` | Runs. Top hit for *"What is the return policy?"* is **`15-internal-notes.md`** — an internal doc the system prompt forbids using. Retrieval does **no metadata filtering**; the guardrail is prompt-only. |
| `python -c "import app.agent.graph"` | **Fails** without `GROQ_API_KEY`: `groq.GroqError: The api_key client option must be set`. The model is constructed at import time, so a missing key takes down the whole FastAPI app including `GET /`. |
| `pytest` | **Not installed and not a dependency.** |

### Test status: there is no test suite

The three `test_*.py` files are **manual scripts, not tests**: no `pytest`
dependency, no assertions, no test functions.

- `app/test_agent.py` — infinite `while True: input()` REPL loop.
- `app/retrieval/test_retriever.py` — module-level prints; the query is the
  e-commerce *"What is the return policy?"*.
- `app/retrieval/test_patient_ingest.py` / `test_patient_retrieval.py` —
  module-level scripts hardcoding a patient id
  (`6a9d17d6b74cef0c8858926a`) and a `test-report.txt` that is **gitignored and
  absent**, so they cannot run.

Backend and frontend have **no test tooling at all** (no jest/vitest, no lint
config, no `test` script).

---

## 5. What works vs. stubbed vs. broken

**Works**
- User/admin registration, login, JWT session restore, logout.
- Conversation create/list/message-history, persisted in MongoDB.
- Chat round trip browser → Express → FastAPI → LangGraph → Groq (with a key).
- Patient document upload → multer → forward to ai-service → per-patient FAISS
  index → retrieved into the system prompt on subsequent chats.
- Frontend production build.

**Stubbed / mock**
- Every queue-management page: patients, departments, doctors, analytics,
  alerts, notifications, "waiting prediction", "recommendations". All driven by
  `mockData.js` plus a 5-second `setInterval` that jitters numbers in state.
- `services/{patient,doctor,queue,analytics}Service.js` — `Promise.resolve(MOCK)`.
- `PatientPortal` Appointments / Medical Records / Profile tabs — static markup.
- `Settings.jsx` toggles — local `useState`, never persisted.
- `adminController.getAdminProfile` — echoes `req.account`.
- `src/ai_service/__init__.py` — `print("Hello from ai-service!")` scaffold.

**Broken / risky**
1. `GROQ_API_KEY` absent ⇒ **ai-service will not import**, so every endpoint
   including the health check 500s at startup.
2. `retriever.py` loads `faiss_index/` **at import time**; if the index has not
   been built the service crashes on import. (The Dockerfile builds it; a local
   run without `ingest` does not.)
3. `POST /api/auth/admin/register` is completely unauthenticated — **anyone can
   create an admin account**.
4. `authController.loginUser` does `console.log(token)` — JWTs in server logs.
5. `documentController` does `fs.readFileSync` of the whole upload into memory
   and forwards synchronously; a slow OCR/ingest blocks the Express request.
6. `api/documents.py` returns HTTP **200 with `success: false`** on failure,
   so the backend's `aiResponse.ok` check does catch it only via the
   `result.success` test — fragile contract.
7. FAISS `allow_dangerous_deserialization=True` on a path derived from a
   user-controlled `patient_id`; no sanitisation of `patient_id` or
   `file.filename` before joining paths (path-traversal surface).
8. `src/middleware/errorMiddleware.js`, `app/core/config.py`,
   `ai-service/README.md`, and `components/doctors/ResourceStatus.jsx` are
   **empty files**.
9. `pyproject.toml` declares `ai-service = "ai_service:main"` against the
   `src/` layout, while all real code lives in `app/` — the packaged
   distribution does not contain the application.
10. `frontend/package.json` depends on `cors`, a server-only package.
11. `handoff_check` detects handoff by substring-matching the model's own prose
    (`"human review"`, `"contact support"`) — trivially both false-positive and
    false-negative.
12. `AI_SERVICE_URL` default (8000) ≠ ai-service container port (8080).
13. No rate limiting, no helmet, no request validation library, no structured
    logging, no health/readiness endpoints beyond `/`.

---

## 6. Secrets

- **No secrets are committed in the working tree.** The only key reference is
  `os.getenv("GROQ_API_KEY")`; no `.env` file is present. A regex sweep for
  `sk-`, `gsk_`, `AIza`, `mongodb+srv`, and literal password assignments found
  nothing.
- **Git history could not be scanned** — the archive has no `.git`. If the
  upstream GitHub repository has history, `GROQ_API_KEY`, `MONGO_URI`, and
  `JWT_SECRET` should still be checked there (e.g. `gitleaks detect`), and
  rotated if the deployed Render/Vercel instances ever had them in-tree.
- Both `.gitignore` files correctly exclude `.env`, `faiss_index/`,
  `patient_documents/`, `patient_faiss/`, and `backend/uploads/`.
- Two live deployment hostnames are hardcoded in source
  (`careflow-gwxc.onrender.com`, `careflow-pearl-pi.vercel.app`). Not secrets,
  but they pin the frontend to one environment.

---

## 7. How to run each service (as it stands today)

```bash
# ai-service
cd ai-service
uv sync
echo "GROQ_API_KEY=..." > .env
uv run python -m app.retrieval.ingest        # REQUIRED once, or import fails
uv run uvicorn app.main:app --reload --port 8000

# backend  (needs a reachable MongoDB)
cd backend
npm install
cat > .env <<'EOF'
PORT=5000
MONGO_URI=mongodb://localhost:27017/careflow
JWT_SECRET=dev-secret
AI_SERVICE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173
EOF
npm run dev

# frontend  (will still call the Render URL — the base URL is hardcoded)
cd frontend
npm install
npm run dev
```

---

## 8. Corrections to the assumptions in the brief

| Brief said | Reality |
|---|---|
| "FastAPI-style app" | It is genuinely FastAPI. ✔ |
| "plus tests" in ai-service | No tests exist; the `test_*.py` files are print scripts and `pytest` is not a dependency. |
| "services/aiService.js presumably proxies to ai-service" | Confirmed, plus `documentController.js` proxies uploads separately. |
| "Pages/components are mostly a hospital queue management dashboard" | Confirmed, and they are entirely mock-data driven. |
| "No lab upload … exists" | A generic **medical document** upload exists inside the AI Assistant page (PDF/TXT → per-patient FAISS). There is no lab-specific parsing, no symptom intake, no biomarker view. |
| `agent/state.py` | Exists, but it is a plain `TypedDict`, not a reducer-annotated LangGraph state. |
| Frontend is on Vercel | Consistent with the hardcoded CORS origins, but **no Vercel config is in the repo**. |
| Roles are patient/clinician-ready | There are only `user` and `admin`, in two separate Mongo collections. |
