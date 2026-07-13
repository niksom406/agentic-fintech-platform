"""
Intake Agent — Stage 1 of the LLM pipeline.

Receives the normalised case data, produces a human-readable summary
and flags key aspects for downstream agents to focus on.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.agents.base_agent import run_agent
from app.models import Case, CaseInput


def run(case: Case, db: Session) -> dict:
    """
    Runs the intake agent.

    Builds a structured user message from the case and its raw input,
    then calls the LLM for enrichment.
    """
    case_input: CaseInput | None = (
        db.query(CaseInput).filter(CaseInput.case_pk == case.id).first()
    )

    normalized = case_input.normalized_payload if case_input else {}
    derived = case_input.derived_fields if case_input else {}
    raw = case_input.raw_payload if case_input else {}

    payload = {
        "case_id": case.case_id,
        "customer_id": case.customer_id,
        "product": case.requested_product_type,
        "transaction_type": case.transaction_type,
        "model_recommendation": case.model_recommendation,
        "model_confidence": case.model_confidence,
        "evidence_completeness_score": case.evidence_completeness_score,
        "normalized_financial_data": normalized,
        "derived_ratios": derived,
        "raw_submission_keys": list(raw.keys()),
    }

    result = run_agent(
        agent_name="intake_agent",
        prompt_file="intake.txt",
        user_content=f"Analyse this financial case:\n\n{json.dumps(payload, indent=2)}",
        case_id=case.case_id,
        case_pk=case.id,
        db=db,
        max_tokens=600,
    )

    # Store the summary back on the case for the API to return
    if isinstance(result, dict) and "worker_summary" in result:
        case.llm_explanation = result["worker_summary"]
        db.flush()

    return result if isinstance(result, dict) else {}
