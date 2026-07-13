"""
Risk Agent — Stage 2 of the LLM pipeline.

Takes the deterministic risk score and factors, then reasons about
risk holistically in plain language. Adds narrative depth beyond numbers.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.agents.base_agent import run_agent
from app.models import Case, RiskResult


def run(case: Case, db: Session) -> dict:
    """
    Runs the risk agent.

    Provides the case + deterministic risk results so the LLM can reason
    about the full picture, not just the score.
    """
    risk: RiskResult | None = (
        db.query(RiskResult).filter(RiskResult.case_pk == case.id).first()
    )

    risk_data = {}
    if risk:
        risk_data = {
            "overall_score": risk.overall_score,
            "risk_level": risk.risk_level,
            "credit_risk": risk.credit_risk,
            "dti_risk": risk.debt_to_income_risk,
            "transaction_anomaly_risk": risk.transaction_anomaly_risk,
            "evidence_weakness_risk": risk.evidence_weakness_risk,
            "model_confidence_penalty": risk.model_confidence_penalty,
            "breakdown": risk.breakdown,
            "top_risk_factors": case.top_risk_factors or [],
        }

    payload = {
        "case_id": case.case_id,
        "product": case.requested_product_type,
        "transaction_type": case.transaction_type,
        "model_recommendation": case.model_recommendation,
        "model_confidence": case.model_confidence,
        "evidence_completeness_score": case.evidence_completeness_score,
        "risk_assessment": risk_data,
    }

    result = run_agent(
        agent_name="risk_agent",
        prompt_file="risk.txt",
        user_content=f"Provide a holistic risk assessment for this case:\n\n{json.dumps(payload, indent=2)}",
        case_id=case.case_id,
        case_pk=case.id,
        db=db,
        max_tokens=700,
    )

    # Persist the narrative back to the risk result row
    if risk and isinstance(result, dict) and "narrative" in result:
        risk.llm_narrative = result["narrative"]
        db.flush()

    return result if isinstance(result, dict) else {}
