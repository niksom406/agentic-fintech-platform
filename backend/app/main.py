from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings

# ── LangSmith tracing — must be set as OS env vars before LangGraph imports ──
# pydantic-settings loads .env into Python objects, but LangSmith reads
# os.environ directly at import time. We bridge them here.
def _configure_langsmith() -> None:
    s = get_settings()
    if s.langchain_tracing_v2 and s.langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = s.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = s.langchain_project
        logging.getLogger(__name__).info(
            "LangSmith tracing enabled → project: %s", s.langchain_project
        )

_configure_langsmith()
from app.core.database import Base, SessionLocal, engine
from app.routes.audit import router as audit_router
from app.routes.cases import router as cases_router
from app.routes.chat import router as chat_router
from app.routes.dashboard import router as dashboard_router
from app.routes.health import router as health_router
from app.routes.policies import router as policies_router
from app.routes.reviews import router as reviews_router
from app.seed import seed_demo_data


def _ensure_sqlite_columns() -> None:
    """Add new columns on existing SQLite DBs (create_all does not alter tables)."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "cases" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("cases")}
    alters: list[str] = []
    if "langsmith_run_id" not in existing:
        alters.append("ALTER TABLE cases ADD COLUMN langsmith_run_id VARCHAR(64)")
    if "langsmith_trace_url" not in existing:
        alters.append("ALTER TABLE cases ADD COLUMN langsmith_trace_url VARCHAR(500)")
    if not alters:
        return
    with engine.begin() as conn:
        for stmt in alters:
            conn.execute(text(stmt))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup (before yield) and shutdown (after yield).
    Keep startup fast so the server binds quickly on Railway.
    """
    import asyncio
    import logging

    # Import all models so SQLAlchemy knows about them before create_all
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns()

    settings = get_settings()
    if settings.seed_on_startup:
        db = SessionLocal()
        try:
            seed_demo_data(db)
        finally:
            db.close()

    ingest_task: asyncio.Task | None = None

    # Lazy-import RAG so chromadb cannot block / crash process boot
    if settings.enable_llm_agents:

        async def _ingest_in_background() -> None:
            try:
                from app.rag.ingest import ingest_policy_documents

                await asyncio.to_thread(ingest_policy_documents)
            except Exception as exc:
                logging.getLogger(__name__).warning("Chroma ingest failed (non-fatal): %s", exc)

        ingest_task = asyncio.create_task(_ingest_in_background())

    yield

    if ingest_task and not ingest_task.done():
        ingest_task.cancel()
        try:
            await ingest_task
        except asyncio.CancelledError:
            pass


settings = get_settings()

app = FastAPI(
    title="Agentic FinTech Platform",
    description="Real LLM agents with deterministic guardrails for financial decision governance.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allows the frontend (localhost:3000) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(cases_router)
app.include_router(reviews_router)
app.include_router(policies_router)
app.include_router(chat_router)
app.include_router(audit_router)
