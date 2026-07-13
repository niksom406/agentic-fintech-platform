"""
Audit Agent — Final stage of the LLM pipeline.

Writes the permanent, compliance-grade audit narrative that records
what happened in this pipeline run. This is stored in the audit log.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.agents.base_agent import run_agent
from app.models import AuditLog, Case


def run(
    case: Case,
    final_decision: str,
    intake_result: dict,
    risk_result: dict,
    governance_result: dict,
    decision_result: dict,
    db: Session,
) -> dict:
    """
    Runs the audit agent.

    Receives a complete picture of the entire pipeline run and produces
    a compliance-grade narrative audit record.
    """
    payload = {
        "case_id": case.case_id,
        "final_decision": final_decision,
        "product": case.requested_product_type,
        "intake_summary": intake_result.get("worker_summary", ""),
        "intake_attention_flags": intake_result.get("attention_flags", []),
        "risk_tier": risk_result.get("risk_tier", ""),
        "risk_narrative": risk_result.get("narrative", ""),
        "risk_score_confidence": risk_result.get("score_confidence", ""),
        "governance_explainability": governance_result.get("explainability_score", ""),
        "governance_fairness_concerns": governance_result.get("fairness_concerns", []),
        "human_review_recommended": governance_result.get("human_review_recommended", False),
        "llm_recommendation": decision_result.get("llm_recommendation", ""),
        "llm_vs_policy_match": decision_result.get("llm_recommendation", "") == final_decision,
        "decision_reasoning": decision_result.get("reasoning", ""),
    }

    result = run_agent(
        agent_name="audit_agent",
        prompt_file="audit.txt",
        user_content=f"Write the audit narrative for this completed case:\n\n{json.dumps(payload, indent=2)}",
        case_id=case.case_id,
        case_pk=case.id,
        db=db,
        max_tokens=900,
    )

    # Write the narrative as an immutable audit log entry
    if isinstance(result, dict) and "audit_narrative" in result:
        narrative = result.get("audit_narrative", "")
        db.add(AuditLog(
            case_pk=case.id,
            event_type="LLM_AUDIT_NARRATIVE",
            actor="audit_agent",
            summary=narrative[:500] if narrative else "LLM audit narrative generated.",
            details_json={
                "narrative": narrative,
                "decision_factors": result.get("decision_factors", []),
                "pipeline_integrity": result.get("pipeline_integrity"),
                "pipeline_integrity_notes": result.get("pipeline_integrity_notes"),
                "regulatory_keywords": result.get("regulatory_keywords", []),
            },
        ))
        db.flush()

    return result if isinstance(result, dict) else {}
