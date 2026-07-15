"""
Pipeline progress helpers — shared stage definitions for SSE streaming.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

# Deterministic engines first, then LLM agents
PIPELINE_STAGES: list[dict[str, str]] = [
    {"id": "policy", "label": "Policy Engine", "group": "deterministic"},
    {"id": "risk", "label": "Risk Engine", "group": "deterministic"},
    {"id": "governance", "label": "Governance Engine", "group": "deterministic"},
    {"id": "decision", "label": "Decision Engine", "group": "deterministic"},
    {"id": "llm_intake", "label": "Intake Agent", "group": "llm"},
    {"id": "llm_risk", "label": "Risk Agent", "group": "llm"},
    {"id": "llm_governance", "label": "Governance Agent", "group": "llm"},
    {"id": "llm_decision", "label": "Decision Agent", "group": "llm"},
    {"id": "llm_audit", "label": "Audit Agent", "group": "llm"},
]

STAGE_LABELS = {s["id"]: s["label"] for s in PIPELINE_STAGES}

ProgressCallback = Callable[[dict[str, Any]], None]


def emit_progress(
    on_progress: ProgressCallback | None,
    *,
    stage: str,
    status: str,
    message: str = "",
    **extra: Any,
) -> None:
    """Send a stage update to the SSE consumer (no-op if no callback)."""
    if on_progress is None:
        return
    on_progress(
        {
            "type": "stage",
            "stage": stage,
            "label": STAGE_LABELS.get(stage, stage),
            "status": status,
            "message": message,
            **extra,
        }
    )
