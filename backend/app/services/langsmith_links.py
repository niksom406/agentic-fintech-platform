"""
LangSmith trace URL helpers.
"""
from __future__ import annotations

import logging
import time
from uuid import UUID

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def build_langsmith_trace_url(run_id: UUID | str) -> str | None:
    """
    Resolve a deep-link to the LangSmith UI for this pipeline run.

    Tries the official SDK URL first (needs the run to have flushed),
    then falls back to a constructed project URL.
    """
    settings = get_settings()
    if not settings.langchain_tracing_v2 or not settings.langchain_api_key:
        return None

    run_id_str = str(run_id)

    try:
        from langsmith import Client

        client = Client(api_key=settings.langchain_api_key)
        run = None
        for attempt in range(4):
            try:
                run = client.read_run(run_id_str)
                break
            except Exception:
                time.sleep(0.35 * (attempt + 1))

        if run is not None:
            return client.get_run_url(run=run, project_name=settings.langchain_project)
    except Exception as exc:
        logger.warning("Could not resolve LangSmith URL via SDK: %s", exc)

    # Fallback deep-link used by LangSmith UI for a specific run
    project = settings.langchain_project
    return f"https://smith.langchain.com/o/default/projects/p/{project}/r/{run_id_str}"
