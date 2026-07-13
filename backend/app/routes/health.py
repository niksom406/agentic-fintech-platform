from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    """Simple liveness check. Returns app status and environment."""
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_env,
        "llm_agents_enabled": settings.enable_llm_agents,
        "primary_model": settings.primary_llm_model,
    }
