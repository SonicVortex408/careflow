# Deploying PolyMarker Analytics (free tier)

```
Vercel (static)            Modal  (deploy/modal_app.py)                      Supabase
frontend ──HTTPS──► polymarker-api   Express gateway ──────────────────► Postgres (users, reports, …)
                          │                        └──────────────────► Storage (private bucket: uploads)
                          │ X-Internal-Key
                          ▼
                    polymarker-ai    FastAPI ai-service ──spawn──► run_job  (OCR + interpretation)
                                            └──── job state ────► modal.Dict
                                                                          optional: Neo4j Aura Free, Groq
```

| Piece | Service | Free tier used |
|---|---|---|
| Frontend | Vercel Hobby | static Vite build |
| Database + file storage | Supabase Free | Postgres 500 MB, Storage 1 GB |
| Backend, ai-service, jobs | Modal Starter | monthly free compute credits; every function scales to zero |
| Knowledge graph (optional) | Neo4j Aura Free | without it the ai-service uses the identical in-memory graph |
| LLM (optional) | Groq free key | without it summaries use the deterministic template |

Nothing here needs a credit card or a paid plan at demo scale. Limits change, so
check each provider's pricing page. Deploy in this order: **Supabase → Modal →
Vercel**, then come back to Modal once to set the Vercel URL.

You need Python 3.10+ locally (for the `modal` CLI) and this repository checked
out on `main`.

## 1. Supabase (database + storage)

1. Create a project at [supabase.com](https://supabase.com) and note the
   database password you choose.
2. **Connection string.** Click **Connect** (top bar) → **Transaction pooler** →
   copy the URI and fill in the password:
   `postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres`.
   Use the pooler, not the direct `db.<ref>.supabase.co` host: the direct host
   is IPv6-only on the free plan, and the pooler also suits scale-to-zero containers.
3. **API URL and secret key.** Project Settings → **API Keys**: copy a
   **secret** key (`sb_secret_…`; the legacy `service_role` key also works). The
   project URL is `https://<ref>.supabase.co`. The secret key stays on the
   backend; the frontend never talks to Supabase directly.

You do not create tables or buckets by hand. The backend applies
`backend/src/db/schema.sql` on start and creates the private `lab-reports`
bucket. Row level security is enabled on every table with no policies, so
Supabase's public Data API returns nothing even with the anon key. Only the
backend, which connects as the table owner, can read the data.

## 2. Modal (backend + ai-service + jobs)

```bash
pip install modal
modal setup                       # opens the browser to sign in

# Shared secret between backend and ai-service
modal secret create polymarker-shared INTERNAL_API_KEY=$(openssl rand -hex 32)

# ai-service. LLM_PROVIDER=none means deterministic template summaries; for an LLM use
#   LLM_PROVIDER=groq GROQ_API_KEY=gsk_...    and for Neo4j Aura add
#   NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io NEO4J_PASSWORD=...
modal secret create polymarker-ai LLM_PROVIDER=none

# Backend. FRONTEND_URL is a placeholder until step 3 gives you the Vercel URL.
modal secret create polymarker-backend \
  DATABASE_URL='postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres' \
  JWT_SECRET=$(openssl rand -hex 32) \
  FRONTEND_URL=https://example.vercel.app \
  SUPABASE_URL=https://<ref>.supabase.co \
  SUPABASE_SERVICE_KEY=sb_secret_... \
  SEED_ADMIN_EMAIL=you@example.com         SEED_ADMIN_PASSWORD='choose-a-strong-one' \
  SEED_CLINICIAN_EMAIL=doctor@example.com  SEED_CLINICIAN_PASSWORD='choose-a-strong-one'

modal deploy deploy/modal_app.py          # first build ~5 min (Tesseract + Python + Node deps)
modal run deploy/modal_app.py::seed       # schema + bucket + seed accounts (idempotent)
modal run deploy/modal_app.py::load_graph # only if you set NEO4J_URI
```

`modal deploy` prints two URLs:

* `https://<workspace>--polymarker-api.modal.run`: the backend. Check
  `…/api/health` → `{"success":true,"status":"ok"}`.
* `https://<workspace>--polymarker-ai.modal.run`: the ai-service. The backend
  finds this URL by itself, and every `/api` route rejects callers without the
  internal key.

## 3. Vercel (frontend)

1. Vercel → **Add New → Project** → import `SonicVortex408/careflow` →
   **Import single project** next to **frontend**. Root Directory `frontend`,
   preset Vite.
2. Environment Variables → `VITE_API_BASE_URL` =
   `https://<workspace>--polymarker-api.modal.run/api` (Production and Preview).
3. **Deploy.** The variable is read at build time; after changing it, redeploy.
4. Put the Vercel URL into the backend's CORS list and redeploy:

   ```bash
   modal secret create --force polymarker-backend ...same values... FRONTEND_URL=https://<your-app>.vercel.app
   modal deploy deploy/modal_app.py
   ```

   (or edit the secret in the Modal dashboard → Secrets, then redeploy).
   `FRONTEND_URL` accepts several comma-separated origins (e.g. production +
   a preview URL).

## 4. Smoke test

1. Sign in as the seeded clinician; the review queue should load.
2. Register a patient, complete the symptom check-in and upload a lab report
   (any PDF from `bda_engine`'s generator, or a text report).
3. The upload page shows "Waiting for clinician review" within about a minute
   (longer on the first upload while the ai-service cold-starts).
4. Approve it as the clinician; the patient dashboard then shows gauges, radar,
   cohort map and risk.

If uploads stay in "processing", open the Modal dashboard → app `polymarker` →
`run_job` logs. If the UI shows "Cannot reach the server", check
`VITE_API_BASE_URL` and the backend's `FRONTEND_URL`. If the API logs
"Postgres connection failed", check that `DATABASE_URL` is the pooler URL.

## Free-tier behaviour to know about

* **Cold starts.** Functions scale to zero after 5 idle minutes. The first
  request afterwards takes a few seconds for the API and 10–20 s for the
  ai-service. That keeps the deployment within the free credits; for a live
  demo, open the site a minute early.
* **Supabase pauses** free projects after about a week without activity.
  Restore it from the dashboard (data is kept).
* **Assistant memory** lives in the serving ai-service container (there is no
  Redis on Modal), so a conversation's earlier turns are forgotten after the
  container scales down. Messages themselves are stored in Postgres and stay
  visible in the UI.
* **Per-patient document index.** It is written in the job container and not
  kept. The assistant's answers use the clinician-approved results that the
  backend passes in, plus the knowledge graph and the medical knowledge base.
* **Uploads** are stored in the private Supabase bucket and sent to the
  ai-service with the job; deleting a report deletes the stored file.

## Local development

`docker compose up --build` runs the same code with plain Postgres, Redis +
Celery and Neo4j instead of Supabase and Modal (see the README). Backend tests
need a Postgres to create throwaway databases in:
`DATABASE_URL_TEST=postgres://postgres:postgres@localhost:5432/postgres npm test`.

## Retraining models

`models/` is baked into the ai-service image. To publish new artifacts, run
`uv run bda all` (or `docker compose --profile ml run --rm bda all`), commit
the updated `models/`, run `modal deploy deploy/modal_app.py`, and, with Neo4j,
`modal run deploy/modal_app.py::load_graph`.
