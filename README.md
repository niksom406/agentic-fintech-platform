# Agentic FinTech Platform

**Deterministic guardrails + agentic AI control for financial decisioning.**

A governance layer that sits between an upstream model recommendation and final action. It validates cases with policy rules, risk scoring, fairness checks, multi-agent LLM enrichment, human review, and audit trails.

---

## Live demo

| Surface | URL |
|---------|-----|
| **Frontend (demo)** | [https://agentic-fintech-platform.vercel.app](https://agentic-fintech-platform.vercel.app) |
| Backend API | [https://agentic-fintech-platform-production.up.railway.app](https://agentic-fintech-platform-production.up.railway.app) |
| API health | [https://agentic-fintech-platform-production.up.railway.app/health](https://agentic-fintech-platform-production.up.railway.app/health) |
| API docs | [https://agentic-fintech-platform-production.up.railway.app/docs](https://agentic-fintech-platform-production.up.railway.app/docs) |

> The live demo uses a short-lived Railway + Vercel deployment. The backend may sleep or reset demo data after redeploys (SQLite + container disk).

**Try on the demo:**
1. Open the [dashboard](https://agentic-fintech-platform.vercel.app/dashboard)
2. Run a **New Review** / evaluation
3. Inspect a case (pipeline, explanations, LangSmith link when available)
4. Resolve an item in **Human Review** (reviewer note must be ≥ 10 characters)
5. Ask the **AI Analyst** chat about policies or cases  
   On mobile: use the **hamburger menu** to navigate

---

## What this project does

Financial institutions increasingly use AI for credit / lending recommendations. This platform is the **control plane** around those recommendations:

- **Deterministic engines** enforce hard rules (credit score floors, DTI caps, evidence thresholds) — LLMs cannot override them
- **LLM agents** (LangGraph) enrich explanations, fairness narrative, and audit language
- **GraphRAG** retrieves related policy passages for the governance agent (optional; needs Chroma ingest)
- **Human review** queue for escalations / overrides with audit notes
- **Audit export** and dashboard analytics for model-risk style oversight

---

## Architecture

```text
Next.js frontend  ──HTTP/WS──►  FastAPI backend
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              Policy engine    Risk engine    Governance engine
                    │               │               │
                    └───────► Final decision (deterministic) ◄───┘
                                      │
                                      ▼
                         LangGraph LLM agent pipeline
                         (enrichment only — never overrides)
                                      │
                                      ▼
                         SQLite + optional Chroma (RAG)
```

| Layer | Stack |
|-------|--------|
| Frontend | Next.js, TypeScript, Tailwind |
| Backend | FastAPI, SQLAlchemy, SQLite |
| Agents | LangGraph, OpenAI (+ Groq fallback) |
| RAG | ChromaDB + OpenAI embeddings + NetworkX graph expansion |
| Tracing | LangSmith (optional) |
| Deploy | Railway (API) + Vercel (UI) |

---

## Repository layout

```text
agentic-fintech-platform/
├── backend/                 # FastAPI app
│   ├── app/
│   │   ├── agents/          # LangGraph orchestrator + agents
│   │   ├── rag/             # Chroma + GraphRAG retriever
│   │   ├── routes/          # HTTP / WS / SSE endpoints
│   │   ├── services/        # Policy, risk, evaluation, chat, audit
│   │   └── ...
│   ├── Dockerfile
│   ├── railway.toml
│   ├── requirements.txt
│   └── .env.example
├── frontend/                # Next.js app
│   ├── app/                 # Pages (dashboard, cases, chat, …)
│   ├── components/
│   └── .env.example
├── docker-compose.yml
├── DEPLOY.md                # Railway + Vercel hosting notes
└── README.md
```

---

## Prerequisites

- **Python** 3.11+ (3.12 recommended)
- **Node.js** 20+ (22 recommended)
- **OpenAI API key** (required for LLM agents + embeddings)
- Optional: **Groq** API key (fallback model), **LangSmith** API key (tracing)
- Optional: **Docker** / Docker Compose for containerized local run

---

## Local setup

### 1. Clone

```bash
git clone https://github.com/niksom406/agentic-fintech-platform.git
cd agentic-fintech-platform
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — set at least OPENAI_API_KEY
# For full agents: ENABLE_LLM_AGENTS=true
```

Important `.env` values:

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Primary LLM + embeddings |
| `GROQ_API_KEY` | Optional fallback LLM |
| `ENABLE_LLM_AGENTS` | `true` to run LangGraph agents |
| `SEED_ON_STARTUP` | `true` seeds demo cases + policies |
| `CORS_ORIGINS` | Frontend origins (local: `http://localhost:3000`) |
| `INGEST_POLICIES_ON_STARTUP` | `true` to embed policies into Chroma on boot (memory-heavy; leave `false` on small hosts) |
| `LANGCHAIN_API_KEY` / `LANGCHAIN_TRACING_V2` | Optional LangSmith tracing |

Start the API:

```bash
python run.py
# → http://localhost:8000
# → docs at http://localhost:8000/docs
```

### 3. Frontend

```bash
cd frontend
npm install

cp .env.example .env.local
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

```bash
npm run dev
# → http://localhost:3000
```

Open [http://localhost:3000/dashboard](http://localhost:3000/dashboard).

---

## Docker Compose (optional)

Runs API + UI together:

```bash
cp .env.example .env
# Fill OPENAI_API_KEY (and other secrets) in .env

docker compose up --build
```

- Frontend: http://localhost:3000  
- Backend: http://localhost:8000  

See root `.env.example` for the compose-oriented template.

---

## Key product flows

### New evaluation
`/evaluation` → submit applicant payload → live agent pipeline (SSE) → deterministic decision + LLM enrichment → case detail.

### Cases & explainability
`/cases` and `/cases/[id]` → risk, policy hits, governance flags, pipeline progress, optional LangSmith deep-link.

### Human review
`/reviews` → approve/reject escalations. **Reviewer note must be at least 10 characters** (audit requirement).

### AI Analyst chat
`/chat` → policy / case Q&A over WebSocket streaming. On small screens use the **hamburger menu**.

### Policies
`/policies` → version history and rollback.

### Audit
`/audit` + per-case JSON/TXT export endpoints.

---

## API quick reference

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/health` | Liveness |
| `GET` | `/dashboard/summary` | KPIs + activity |
| `POST` | `/cases` | Create case |
| `POST` | `/cases/{id}/evaluate` | Run evaluation |
| `GET` | `/cases/{id}/evaluate/stream` | SSE pipeline progress |
| `GET` | `/reviews/pending` | Human review queue |
| `POST` | `/reviews/{id}/decision` | Submit review |
| `WS` | `/chat/sessions/{id}/stream` | Chat streaming |

Full interactive docs: `/docs` on the backend.

---

## Deploying your own instance

Short guide: see **[DEPLOY.md](./DEPLOY.md)**.

Summary:

1. **Railway** — root directory `backend`, use Dockerfile, set secrets + `PORT=8000`, generate public domain  
2. **Vercel** — root directory `frontend`, set  
   `NEXT_PUBLIC_API_BASE_URL=https://your-railway-url`  
   (no trailing slash; **redeploy** after changing this — it is baked in at build time)  
3. Set Railway `CORS_ORIGINS` to your Vercel URL, e.g.  
   `https://agentic-fintech-platform.vercel.app,http://localhost:3000`

**Do not commit** `.env` / `.env.local` or real API keys.

---

## Design principles (interview-ready)

1. **Deterministic guardrails win** — reject / escalate rules are code-enforced; LLMs only enrich  
2. **Human-in-the-loop** — escalations require documented reviewer decisions  
3. **Auditability** — structured logs, exports, optional LangSmith traces  
4. **Separation of concerns** — policy / risk / governance engines vs agent orchestration vs UI  

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Frontend “Failed to fetch” | Backend down or wrong API URL | Hit `/health`; check `NEXT_PUBLIC_API_BASE_URL`; redeploy Vercel after env changes |
| CORS errors in browser | Origin not allowed | Add exact frontend origin to `CORS_ORIGINS` (no quotes) |
| Railway 502 after boot | Memory pressure (Chroma / heavy seed) | Keep `INGEST_POLICIES_ON_STARTUP=false`; seed uses deterministic path |
| Review submit validation error | Note too short | Reviewer note ≥ 10 characters |
| Agents skipped | Flag off or missing key | `ENABLE_LLM_AGENTS=true` + valid `OPENAI_API_KEY` |

---

## License

For portfolio / demo use. Add a license file if you redistribute commercially.

---

## Author

Built as an agentic AI guardrail engine for FinTech model-risk and governance demos.

- Live UI: [agentic-fintech-platform.vercel.app](https://agentic-fintech-platform.vercel.app)  
- Repo: [github.com/niksom406/agentic-fintech-platform](https://github.com/niksom406/agentic-fintech-platform)
