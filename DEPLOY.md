# Short-lived demo hosting (Railway + Vercel)

Use this for a temporary public demo. Tear down when done to avoid API spend.

## 0. Push to GitHub first

Your local repo has no remote yet. Create a private GitHub repo, then:

```bash
cd /Users/nikitasomani/agentic-fintech-platform
git remote add origin https://github.com/YOUR_USER/agentic-fintech-platform.git
git add -A
git status   # confirm backend/.env is NOT listed
git commit -m "Prepare demo for short-lived hosting"
git push -u origin master
```

**Never commit `backend/.env`.** Put secrets only in the host dashboards.

---

## 1. Backend → Railway (~5 min)

1. Go to [railway.app](https://railway.app) → login with GitHub.
2. **New Project** → **Deploy from GitHub** → select this repo.
3. Open the service → **Settings** (this is the usual cause of a 7s “Build image” failure):
   - **Root Directory:** `backend` ← required for this monorepo
   - **Builder:** Dockerfile (auto-detects `backend/Dockerfile` + `backend/railway.toml`)
   - Do **not** leave Root Directory as `/` — there is no Dockerfile at the repo root
4. **Variables** → add (copy from your local `.env`, do not commit them):

| Variable | Example |
|----------|---------|
| `APP_ENV` | `production` |
| `ENABLE_LLM_AGENTS` | `true` |
| `SEED_ON_STARTUP` | `true` |
| `OPENAI_API_KEY` | your key |
| `GROQ_API_KEY` | your key (optional) |
| `PRIMARY_LLM_MODEL` | `gpt-4o-mini` |
| `FALLBACK_LLM_MODEL` | `llama-3.1-8b-instant` |
| `LLM_MAX_TOKENS` | `1500` |
| `CORS_ORIGINS` | `http://localhost:3000` for now; update to Vercel URL in step 5 below |
| `LANGCHAIN_TRACING_V2` | `false` (optional; set `true` + key if you want traces) |

5. **Settings → Networking → Generate Domain** → copy the HTTPS URL  
   e.g. `https://agentic-fintech-platform-production.up.railway.app`

6. Hit `/health` in the browser to confirm the API is up.

> SQLite + Chroma live on the container disk. Fine for a short demo; data may reset on redeploy.

---

## 2. Frontend → Vercel (~5 min)

1. Go to [vercel.com](https://vercel.com) → **Add New Project** → import the same GitHub repo.
2. Configure:
   - **Root Directory:** `frontend`
   - Framework: Next.js (auto)
3. **Environment Variables:**

| Name | Value |
|------|--------|
| `NEXT_PUBLIC_API_BASE_URL` | your Railway HTTPS URL (no trailing slash) |

4. Deploy → copy the Vercel URL  
   e.g. `https://agentic-fintech-platform.vercel.app`

5. Back in Railway, set:

```text
CORS_ORIGINS=https://YOUR-APP.vercel.app,http://localhost:3000
```

Redeploy the backend (or restart) so CORS picks up the change.

---

## 3. Smoke test

- Open the Vercel URL
- Run an evaluation / open a case
- Open Chat and confirm streaming works
- Submit a human review (note ≥ 10 characters)

---

## Tear down (when the demo is over)

1. Railway → delete the project (or remove the service).
2. Vercel → delete the project.
3. Optional: revoke/rotate API keys if the demo URL was widely shared.

---

## Local reminder

Run each service directly:

```bash
# backend
cd backend && source .venv/bin/activate && python run.py

# frontend
cd frontend && npm run dev
```

Frontend expects `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` locally.

### Or run both with Docker Compose

```bash
cp .env.example .env   # fill in OPENAI_API_KEY etc.
docker compose up --build
```

This builds `backend/Dockerfile` and `frontend/Dockerfile` and starts both
services together (frontend on `:3000`, backend on `:8000`), reading config
from the root `.env`. Useful for verifying the containerized setup before
deploying to Railway/Vercel.
