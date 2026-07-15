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

### High-level system

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NEXT.JS FRONTEND (Vercel)                            │
│  Landing · Dashboard · Evaluation · Cases · Reviews · Chat · Policies · Audit│
│  HTTP / SSE / WebSocket  →  NEXT_PUBLIC_API_BASE_URL                         │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND (Railway)                            │
│  routes/  →  services/  →  engines + agents  →  SQLite (+ optional Chroma)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Evaluation pipeline (per case)

Upstream bank/model inputs arrive as a case payload (`model_recommendation`, confidence, evidence). This app is the **guardrail layer** — it does not train the credit model; it governs the recommendation.

```text
                    ┌──────────────────┐
                    │  Case submission │
                    │  (intake API)    │
                    └────────┬─────────┘
                             ▼
              ┌──────────────────────────────┐
              │     DETERMINISTIC LAYER      │  ← always authoritative
              │  1. Policy engine            │     credit / DTI / evidence /
              │  2. Risk engine              │     confidence thresholds
              │  3. Governance engine        │     fairness / AML-style flags
              │  4. Final decision           │     APPROVE | REJECT | ESCALATE
              └──────────────┬───────────────┘
                             ▼
              ┌──────────────────────────────┐
              │   LANGGRAPH AGENT LAYER      │  ← enrichment only
              │  Phase 1 (parallel):         │     never overrides policy
              │    intake · risk · governance│
              │  Handoff → Phase 2:          │
              │    decision · audit          │
              │  + optional GraphRAG context │
              │  + optional LangSmith trace  │
              └──────────────┬───────────────┘
                             ▼
              ┌──────────────────────────────┐
              │  Persist + audit trail       │
              │  Human review queue if needed│
              └──────────────────────────────┘
```

### Request / runtime paths

| Path | How it works |
|------|----------------|
| **New Evaluation** | `POST /cases` → `POST …/evaluate` or `GET …/evaluate/stream` (SSE live stages) |
| **Dashboard** | Aggregates cases, reviews, flags, charts from SQLite |
| **Human Review** | Pending escalations → `POST /reviews/{id}/decision` (note ≥ 10 chars) |
| **AI Analyst chat** | REST session create + **WebSocket** token stream; tools can query cases/policies/RAG |
| **Policies** | Versioned rule sets with history + rollback |
| **Audit export** | Per-case JSON / TXT export |

### GraphRAG (optional)

```text
Case flags / query
       │
       ▼
 infer seed categories ──► NetworkX policy graph (hops)
       │
       ▼
 Chroma semantic search (filtered by category)
       │
       ▼
 Policy passages injected into governance / chat prompts
```

Policy text lives in `backend/app/rag/policy_documents.py` (hand-authored chunks). Set `INGEST_POLICIES_ON_STARTUP=true` to embed into Chroma on boot (memory-heavy on small hosts).

### Stack by layer

| Layer | Technology |
|-------|------------|
| Frontend | Next.js (App Router), TypeScript, Tailwind, Recharts |
| Backend API | FastAPI, Uvicorn, Pydantic Settings |
| Persistence | SQLAlchemy + SQLite |
| Deterministic engines | Custom policy / risk / governance services |
| Agents | LangGraph orchestrator + OpenAI (`gpt-4o-mini`), Groq fallback |
| RAG | ChromaDB, OpenAI `text-embedding-3-small`, NetworkX |
| Observability | LangSmith (optional), structured audit logs, LLM usage logs |
| Hosting | Railway (API container) + Vercel (frontend) |

---

## Repository layout

```text
agentic-fintech-platform/
├── README.md
├── DEPLOY.md                      # Railway + Vercel hosting walkthrough
├── docker-compose.yml             # Local full-stack containers
├── .env.example                   # Root env template for Compose
├── .gitignore
│
├── backend/                       # FastAPI guardrail API
│   ├── Dockerfile
│   ├── railway.toml
│   ├── requirements.txt
│   ├── run.py                     # Local uvicorn entry (respects PORT)
│   ├── .env.example
│   │
│   └── app/
│       ├── main.py                # FastAPI app, CORS, lifespan, routers
│       ├── seed.py                # Demo policies + cases on startup
│       │
│       ├── core/
│       │   ├── config.py          # Env / settings
│       │   ├── database.py        # SQLAlchemy engine + sessions
│       │   └── llm.py             # OpenAI / Groq client helpers
│       │
│       ├── models/                # ORM tables
│       │   ├── case.py
│       │   ├── case_input.py
│       │   ├── policy_version.py
│       │   ├── policy_result.py
│       │   ├── risk_result.py
│       │   ├── governance_flag.py
│       │   ├── human_review.py
│       │   ├── audit_log.py
│       │   ├── llm_usage_log.py
│       │   ├── chat_session.py
│       │   └── chat_message.py
│       │
│       ├── schemas/               # Pydantic request/response models
│       │   ├── cases.py
│       │   ├── reviews.py
│       │   ├── policies.py
│       │   └── chat.py
│       │
│       ├── routes/                # HTTP / SSE / WebSocket endpoints
│       │   ├── health.py
│       │   ├── dashboard.py
│       │   ├── cases.py           # CRUD + evaluate + SSE stream
│       │   ├── reviews.py
│       │   ├── policies.py
│       │   ├── chat.py            # Sessions + WS streaming
│       │   └── audit.py           # Export JSON / TXT
│       │
│       ├── services/              # Business logic
│       │   ├── intake_service.py
│       │   ├── policy_engine.py   # Deterministic policy rules
│       │   ├── risk_engine.py     # Deterministic risk score
│       │   ├── governance_engine.py
│       │   ├── evaluation_service.py   # Full evaluate pipeline
│       │   ├── pipeline_progress.py    # SSE stage events
│       │   ├── review_service.py
│       │   ├── policy_service.py       # Versioning / rollback
│       │   ├── audit_export.py
│       │   ├── langsmith_links.py
│       │   ├── chat_agent.py           # Streaming chat LLM
│       │   └── chat_tools.py           # Tool calls (cases, RAG, …)
│       │
│       ├── agents/                # LangGraph multi-agent layer
│       │   ├── base_agent.py
│       │   ├── orchestrator.py    # Graph: phase 1 → phase 2
│       │   ├── intake_agent.py
│       │   ├── risk_agent.py
│       │   ├── governance_agent.py
│       │   ├── decision_agent.py
│       │   └── audit_agent.py
│       │
│       └── rag/                   # GraphRAG knowledge layer
│           ├── policy_documents.py    # Curated policy chunks
│           ├── chroma_store.py        # Persistent Chroma + embeddings
│           ├── ingest.py              # Embed + upsert documents
│           ├── graph_reasoner.py      # Category graph expansion
│           └── retriever.py           # Public retrieve_policy_context()
│
└── frontend/                      # Next.js control panel
    ├── Dockerfile
    ├── vercel.json
    ├── package.json
    ├── next.config.ts
    ├── tailwind.config.ts
    ├── tsconfig.json
    ├── .env.example
    │
    ├── app/                       # App Router pages
    │   ├── layout.tsx
    │   ├── page.tsx               # Marketing / landing
    │   ├── globals.css
    │   ├── dashboard/page.tsx
    │   ├── evaluation/page.tsx    # New Review + live pipeline UI
    │   ├── cases/
    │   │   ├── page.tsx
    │   │   └── [id]/page.tsx     # Case detail + explainability
    │   ├── reviews/page.tsx
    │   ├── chat/page.tsx          # AI Analyst (WebSocket)
    │   ├── policies/page.tsx
    │   └── audit/page.tsx
    │
    ├── components/
    │   ├── layout/
    │   │   ├── app-shell.tsx
    │   │   ├── sidebar-nav.tsx    # Desktop nav
    │   │   └── top-nav.tsx        # Top bar + mobile hamburger menu
    │   ├── cases/
    │   │   ├── agent-pipeline-progress.tsx
    │   │   ├── explainability-panel.tsx
    │   │   └── case-history-timeline.tsx
    │   ├── dashboard/             # KPI cards + charts + activity
    │   ├── reviews/
    │   │   └── review-decision-dialog.tsx
    │   ├── policies/
    │   │   └── policy-table.tsx
    │   ├── ui/                    # Shared primitives (button, card, …)
    │   ├── theme-provider.tsx
    │   └── theme-toggle.tsx
    │
    └── lib/
        ├── api.ts                 # Backend client (HTTP + WS URL helper)
        ├── types.ts               # Shared TypeScript types
        └── utils.ts
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
