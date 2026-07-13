"""
Decision Agent — Stage 4 of the LLM pipeline.

Proposes a recommended decision WITH reasoning and drafts the
applicant-facing explanation. The deterministic policy engine
retains final authority — this agent advises, not decides.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.agents.base_agent import run_agent
from app.models import Case


def run(
    case: Case,
    policy_outcome: str,
    risk_result: dict,
    governance_result: dict,
    db: Session,
) -> dict:
    """
    Runs the decision agent.

    Receives the full picture: deterministic policy outcome, risk narrative,
    and governance findings. Drafts the recommendation and applicant explanation.
    """
    payload = {
        "case_id": case.case_id,
        "product": case.requested_product_type,
        "transaction_type": case.transaction_type,
        "model_recommendation": case.model_recommendation,
        "model_confidence": case.model_confidence,
        "evidence_completeness_score": case.evidence_completeness_score,
        "deterministic_policy_outcome": policy_outcome,
        "risk_score": case.risk_score,
        "risk_level": case.risk_level,
        "risk_tier": risk_result.get("risk_tier", "UNKNOWN"),
        "risk_narrative": risk_result.get("narrative", ""),
        "top_risk_factors": case.top_risk_factors or [],
        "governance_findings": {
            "explainability_score": governance_result.get("explainability_score"),
            "fairness_concerns": governance_result.get("fairness_concerns", []),
            "human_review_recommended": governance_result.get("human_review_recommended", False),
            "compliance_notes": governance_result.get("compliance_notes", []),
        },
    }

    result = run_agent(
        agent_name="decision_agent",
        prompt_file="decision.txt",
        user_content=f"Draft a decision recommendation for this case:\n\n{json.dumps(payload, indent=2)}",
        case_id=case.case_id,
        case_pk=case.id,
        db=db,
        max_tokens=800,
    )

    # Store the applicant explanation on the case
    if isinstance(result, dict) and "applicant_explanation" in result:
        existing = case.llm_explanation or ""
        case.llm_explanation = (
            f"{existing}\n\nDecision: {result['applicant_explanation']}"
        ).strip()
        db.flush()

    return result if isinstance(result, dict) else {}
