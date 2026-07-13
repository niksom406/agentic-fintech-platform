from __future__ import annotations

import time
from typing import Any

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import LLMUsageLog

# Cost per 1000 tokens in USD (approximate, update as pricing changes)
COST_PER_1K = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "llama-3.1-8b-instant": {"input": 0.00005, "output": 0.00008},
}


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = COST_PER_1K.get(model, {"input": 0.0, "output": 0.0})
    return round(
        (prompt_tokens / 1000) * pricing["input"] +
        (completion_tokens / 1000) * pricing["output"],
        6,
    )


def call_llm(
    *,
    messages: list[dict],
    agent_name: str,
    case_id: str,
    case_pk: int,
    db: Session,
    model: str | None = None,
    max_tokens: int | None = None,
    response_format: dict | None = None,
) -> str:
    """
    Central LLM caller for all agents.

    - Calls OpenAI API
    - Measures latency
    - Logs token usage + cost to llm_usage_logs table
    - Returns the text content of the response

    All agents call this function — token tracking is automatic.
    """
    settings = get_settings()
    model = model or settings.primary_llm_model
    max_tokens = max_tokens or settings.llm_max_tokens

    client = OpenAI(api_key=settings.openai_api_key)

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,  # low temperature = consistent, deterministic-leaning output
    }
    if response_format:
        kwargs["response_format"] = response_format

    start = time.time()
    response = client.chat.completions.create(**kwargs)
    latency_ms = int((time.time() - start) * 1000)

    usage = response.usage
    cost = _estimate_cost(model, usage.prompt_tokens, usage.completion_tokens)

    # Write token usage to database — this is your differentiator
    db.add(LLMUsageLog(
        case_pk=case_pk,
        agent_name=agent_name,
        model=model,
        provider="openai",
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
        estimated_cost_usd=cost,
        latency_ms=latency_ms,
    ))
    db.flush()

    content = response.choices[0].message.content or ""
    return content.strip()
