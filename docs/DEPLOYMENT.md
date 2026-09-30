# Deploying PolyMarker Analytics

```
Vercel                 Render (render.yaml)                          Managed
frontend  ──HTTPS──►  polymarker-backend (web) ──private──► polymarker-ai (private) ──► Neo4j Aura
                             │                                    │
                             └──► MongoDB Atlas      polymarker-redis (Key Value) ◄── polymarker-worker (Celery)
```

The frontend is a static Vite build (Vercel). The ai-service cannot run on
Vercel: it needs a long-running Celery worker, Tesseract and Redis, so the back
end runs on Render from the blueprint in [`render.yaml`](../render.yaml).
Deploy in this order: **databases → Render → Vercel**.

## 1. Managed databases

| Service | What to create | Value you will need |
|---|---|---|
| **MongoDB Atlas** | Free M0 cluster, a database user, Network Access `0.0.0.0/0` (Render has no fixed egress IP on starter plans) | `mongodb+srv://USER:PASS@cluster.xxxx.mongodb.net/polymarker` |
| **Neo4j Aura** (optional) | Free AuraDB instance | `neo4j+s://xxxx.databases.neo4j.io` + password |

Without Neo4j the ai-service uses the in-memory copy of the same knowledge
graph (identical evidence chains), so Aura can be added later.

## 2. Render (backend, ai-service, worker, Redis)

1. Render dashboard → **New → Blueprint** → select `SonicVortex408/careflow`,
   branch `main`.
2. Render reads `render.yaml` and asks for the `sync: false` values:

   | Variable | Service | Value |
   |---|---|---|
   | `MONGO_URI` | polymarker-backend | Atlas connection string |
   | `FRONTEND_URL` | polymarker-backend | your Vercel URL, e.g. `https://careflow.vercel.app` (comma-separate several) |
   | `SEED_*_EMAIL` / `SEED_*_PASSWORD` | polymarker-backend | first admin + demo clinician (created on deploy, idempotent) |
   | `NEO4J_URI`, `NEO4J_PASSWORD` | polymarker-ai-env group | Aura values, or leave blank |
   | `GROQ_API_KEY` | polymarker-ai-env group | optional; blank = deterministic template summaries |

   `JWT_SECRET` and the backend↔ai-service `INTERNAL_API_KEY` are generated
   automatically; the ai-service is a private service reachable only from the
   backend.
3. **Apply.** The first build takes ~10 minutes (Tesseract + Python deps).
   The ai-service pre-deploy step loads the knowledge graph into Neo4j when
   `NEO4J_URI` is set; the backend pre-deploy step creates the seed accounts.
4. Check `https://polymarker-backend.onrender.com/api/health` → `{"status":"ok"}`.

**Cost.** The private service, background worker and pre-deploy commands need
paid instances (`starter`, about $7/month each at the time of writing); Key
Value runs on the free plan. To try it for free you can change
`polymarker-backend` to `plan: free` and remove its `preDeployCommand` (then
run `node src/scripts/seed.js` once from the Render shell), but the worker and
private ai-service remain paid.

**Differences from docker-compose, by design:**

* Render services do not share a disk. Uploads are handed from the ai-service to
  the worker through Redis (`polymarker:file:<job>`, 10 MB cap, 1 h TTL).
* Render Key Value has no RedisJSON/RediSearch, so assistant conversation memory
  falls back to in-process memory (it resets on redeploy). For persistent memory
  point `REDIS_URL` of polymarker-ai at a Redis Stack instance (e.g. Redis Cloud)
  and set `CHECKPOINTER=redis`.
* The per-patient document index is written by the worker; the assistant's
  answers rely on the clinician-approved results passed by the backend and on
  the knowledge graph/KB, not on that index.

## 3. Vercel (frontend)

1. Merge the release branch into `main`.
2. Vercel → **Add New → Project** → import `SonicVortex408/careflow` →
   click **Import single project** next to **frontend** (do not use the
   multi-service option). Root Directory `frontend`, preset Vite.
3. Environment Variables → `VITE_API_BASE_URL` =
   `https://polymarker-backend.onrender.com/api` (Production and Preview).
4. **Deploy**, then add the resulting URL to the backend's `FRONTEND_URL` on
   Render (CORS) and redeploy the backend.

The variable is read at build time; after changing it, redeploy the frontend.

## 4. Smoke test

1. Sign in as the seeded clinician; the review queue should load.
2. Register a patient, complete the symptom check-in and upload a lab report
   (any PDF from `bda_engine`'s generator, or a text report).
3. The upload page shows "Waiting for clinician review" within about a minute.
4. Approve it as the clinician; the patient dashboard then shows gauges, radar,
   cohort map and risk.

If uploads stay in "processing", check the **polymarker-worker** logs; if the
UI shows "Cannot reach the server", check `VITE_API_BASE_URL` and the backend's
`FRONTEND_URL`.

## Retraining models

`models/` is baked into the ai-service image. To publish new artifacts, run
`uv run bda all` (or `docker compose --profile ml run --rm bda all`), commit
the updated `models/`, and redeploy; the pre-deploy step reloads the
synthetic-derived bands into Neo4j.
