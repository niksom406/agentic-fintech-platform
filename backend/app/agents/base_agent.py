from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.llm import call_llm

PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts/ directory."""
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()


def run_agent(
    *,
    agent_name: str,
    prompt_file: str,
    user_content: str,
    case_id: str,
    case_pk: int,
    db: Session,
    expect_json: bool = True,
    max_tokens: int = 1000,
) -> dict | str:
    """
    Runs a single LLM agent:
    1. Loads the system prompt from a file
    2. Calls the LLM with system + user message
    3. Parses JSON if expected
    4. Returns the result

    If the LLM returns invalid JSON, returns a safe fallback dict
    so the pipeline never crashes due to a bad LLM response.
    """
    system_prompt = load_prompt(prompt_file)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    raw = call_llm(
        messages=messages,
        agent_name=agent_name,
        case_id=case_id,
        case_pk=case_pk,
        db=db,
        max_tokens=max_tokens,
        response_format={"type": "json_object"} if expect_json else None,
    )

    if not expect_json:
        return raw

    # Parse JSON — with a safe fallback if the LLM misbehaves
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw_response": raw, "parse_error": True}
