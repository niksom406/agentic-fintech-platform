from __future__ import annotations

import logging
import traceback
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.agents import orchestrator
from app.models import AuditLog, Case, GovernanceFlag, HumanReview, PolicyResult, RiskResult
from app.services.governance_engine import evaluate_governance
from app.services.pipeline_progress import ProgressCallback, emit_progress
from app.services.policy_engine import evaluate_policy_rules, get_active_policy
from app.services.risk_engine import compute_risk

logger = logging.getLogger(__name__)


def get_case_with_relations(db: Session, case_id: str) -> Case | None:
    """Fetch a case with all its related data loaded in one query."""
    return db.execute(
        select(Case)
        .where(Case.case_id == case_id)
        .options(
            selectinload(Case.case_input),
            selectinload(Case.policy_results),
            selectinload(Case.risk_result),
            selectinload(Case.governance_flags),
            selectinload(Case.audit_logs),
            selectinload(Case.human_reviews),
            selectinload(Case.llm_usage_logs),
        )
    ).scalar_one_or_none()


def _determine_final_decision(
    policy_output: dict,
    governance_output: dict,
    risk_output: dict,
) -> tuple[str, bool]:
    """
    Deterministic decision logic — this is the guardrail that overrides everything.
    Order of precedence: REJECT > ESCALATE > APPROVE
    """
    if policy_output["has_rejection"]:
        return "REJECT", False

    needs_review = (
        policy_output["has_escalation"]
        or governance_output["requires_human_review"]
        or risk_output["risk_level"] == "Critical"
    )
    if needs_review:
        return "ESCALATE TO HUMAN REVIEW", True

    return "APPROVE", False


def _build_deterministic_explanation(case: Case) -> str:
    """Plain-English explanation built from structured data. No LLM."""
    rejects = [r.rule_name for r in case.policy_results if r.triggered and r.outcome == "REJECT"]
    escalations = [r.rule_name for r in case.policy_results if r.triggered and r.outcome == "ESCALATE"]
    gov_flags = [f.flag_name for f in case.governance_flags]
    top = ", ".join(f"{f['name']} ({f['score']})" for f in (case.top_risk_factors or []))

    return (
        f"Final decision: {case.final_decision}. "
        f"Policy {case.policy_version_used} evaluated with risk score {case.risk_score} ({case.risk_level}). "
        f"Rejection blockers: {rejects or ['none']}. "
        f"Escalation triggers: {escalations or ['none']}. "
        f"Governance flags: {gov_flags or ['none']}. "
        f"Top risk factors: {top or 'none'}."
    )


def evaluate_case(
    db: Session,
    case_id: str,
    on_progress: ProgressCallback | None = None,
) -> Case:
    """
    Runs the full evaluation pipeline for a case.
    Optionally streams stage progress via on_progress (used by SSE).
    """
    case = get_case_with_relations(db, case_id)
    if case is None:
        raise ValueError(f"Case {case_id} not found.")
    if case.case_input is None:
        raise ValueError("Case input data missing.")

    # Clear any previous evaluation (allows re-evaluation)
    db.execute(delete(PolicyResult).where(PolicyResult.case_pk == case.id))
    db.execute(delete(GovernanceFlag).where(GovernanceFlag.case_pk == case.id))
    db.execute(delete(HumanReview).where(HumanReview.case_pk == case.id))
    db.execute(delete(RiskResult).where(RiskResult.case_pk == case.id))
    case.langsmith_run_id = None
    case.langsmith_trace_url = None
    db.flush()

    normalised = case.case_input.normalized_payload
    derived = case.case_input.derived_fields

    # ── Step 1: Policy engine ─────────────────────────────────────────────────
    emit_progress(on_progress, stage="policy", status="running", message="Applying policy rules…")
    active_policy = get_active_policy(db)
    policy_output = evaluate_policy_rules(
        normalised, derived, active_policy.rules_json, active_policy.version
    )

    for result in policy_output["results"]:
        db.add(PolicyResult(case_pk=case.id, **result))

    db.add(AuditLog(
        case_pk=case.id,
        event_type="POLICY_EVALUATION",
        actor="policy-engine",
        summary=f"Policy v{active_policy.version} evaluated. "
                f"Rejections: {policy_output['has_rejection']}, "
                f"Escalations: {policy_output['has_escalation']}.",
        details_json={"version": active_policy.version, "results": policy_output["results"]},
    ))
    emit_progress(
        on_progress,
        stage="policy",
        status="done",
        message=f"Policy v{active_policy.version} complete",
    )

    # ── Step 2: Risk engine ───────────────────────────────────────────────────
    emit_progress(on_progress, stage="risk", status="running", message="Computing risk score…")
    risk_output = compute_risk(normalised, derived)

    db.add(RiskResult(
        case_pk=case.id,
        overall_score=risk_output["overall_score"],
        risk_level=risk_output["risk_level"],
        credit_risk=risk_output["credit_risk"],
        debt_to_income_risk=risk_output["debt_to_income_risk"],
        transaction_anomaly_risk=risk_output["transaction_anomaly_risk"],
        evidence_weakness_risk=risk_output["evidence_weakness_risk"],
        model_confidence_penalty=risk_output["model_confidence_penalty"],
        breakdown=risk_output["breakdown"],
        llm_narrative=None,
    ))

    db.add(AuditLog(
        case_pk=case.id,
        event_type="RISK_SCORING",
        actor="risk-engine",
        summary=f"Risk score: {risk_output['overall_score']} ({risk_output['risk_level']}).",
        details_json=risk_output,
    ))
    emit_progress(
        on_progress,
        stage="risk",
        status="done",
        message=f"Risk {risk_output['overall_score']} ({risk_output['risk_level']})",
    )

    # ── Step 3: Governance engine ─────────────────────────────────────────────
    emit_progress(on_progress, stage="governance", status="running", message="Checking fairness flags…")
    governance_output = evaluate_governance(normalised, derived, policy_output["results"], risk_output)

    for flag in governance_output["flags"]:
        db.add(GovernanceFlag(case_pk=case.id, **flag))

    db.add(AuditLog(
        case_pk=case.id,
        event_type="GOVERNANCE_REVIEW",
        actor="governance-engine",
        summary=governance_output["governance_status"],
        details_json={"flags": governance_output["flags"]},
    ))
    emit_progress(
        on_progress,
        stage="governance",
        status="done",
        message=governance_output["governance_status"],
    )

    # ── Step 4: Final decision ────────────────────────────────────────────────
    emit_progress(on_progress, stage="decision", status="running", message="Applying guardrail decision…")
    final_decision, requires_review = _determine_final_decision(
        policy_output, governance_output, risk_output
    )

    case.final_decision = final_decision
    case.case_status = "pending_human_review" if requires_review else "completed"
    case.risk_score = risk_output["overall_score"]
    case.risk_level = risk_output["risk_level"]
    case.overall_confidence = risk_output["overall_confidence"]
    case.policy_version_used = active_policy.version
    case.requires_human_review = requires_review
    case.was_escalated = case.was_escalated or requires_review
    case.fairness_flag_count = governance_output["fairness_flag_count"]
    case.governance_status = governance_output["governance_status"]
    case.top_risk_factors = risk_output["top_risk_factors"]
    case.blocker_rules = [
        {"rule_name": r["rule_name"], "outcome": r["outcome"], "severity": r["severity"]}
        for r in policy_output["results"] if r["triggered"] and r["outcome"] in {"REJECT", "ESCALATE"}
    ]
    case.evaluated_at = datetime.utcnow()
    case.updated_at = datetime.utcnow()

    if requires_review:
        db.add(HumanReview(
            case_pk=case.id,
            review_status="pending",
            previous_decision=final_decision,
        ))
        db.add(AuditLog(
            case_pk=case.id,
            event_type="HUMAN_REVIEW_REQUIRED",
            actor="review-layer",
            summary="Case escalated to human review queue.",
            details_json={"final_decision": final_decision},
        ))
    else:
        db.add(AuditLog(
            case_pk=case.id,
            event_type="DECISION_FINALIZED",
            actor="decision-engine",
            summary=f"Case finalised as {final_decision}.",
            details_json={"final_decision": final_decision},
        ))

    db.flush()

    # ── Step 5: Build deterministic explanation ────────────────────────────────
    db.refresh(case)
    explanation = _build_deterministic_explanation(case)
    case.deterministic_explanation = explanation
    case.final_explanation = explanation
    case.explanation_mode = "deterministic"
    emit_progress(on_progress, stage="decision", status="done", message=f"Decision: {final_decision}")

    db.commit()

    # ── Step 6: LangGraph LLM agent pipeline ──────────────────────────────────
    case = get_case_with_relations(db, case_id)

    try:
        policy_outcome_str = (
            "REJECT" if policy_output["has_rejection"] else
            "ESCALATE" if policy_output["has_escalation"] else
            "APPROVE"
        )
        logger.info("Starting LLM pipeline for case %s (policy outcome: %s)", case_id, policy_outcome_str)

        llm_outputs = orchestrator.run_pipeline(
            case=case,
            db=db,
            policy_outcome=policy_outcome_str,
            final_decision=final_decision,
            on_progress=on_progress,
        )

        if llm_outputs:
            llm_rec = llm_outputs.get("decision", {}).get("llm_recommendation", "")
            if llm_rec and llm_rec != final_decision.split()[0]:
                logger.info(
                    "Case %s: LLM recommended %s, policy enforced %s",
                    case_id, llm_rec, final_decision,
                )
            case.explanation_mode = "llm_augmented"
            case.langsmith_run_id = llm_outputs.get("langsmith_run_id")
            case.langsmith_trace_url = llm_outputs.get("langsmith_trace_url")
            db.commit()
            logger.info("LLM pipeline complete for case %s", case_id)
        else:
            logger.info("LLM pipeline skipped for case %s (agents disabled)", case_id)

    except Exception as exc:
        logger.error(
            "LangGraph pipeline failed for case %s: %s\n%s",
            case_id, exc, traceback.format_exc(),
        )
        db.rollback()

    return get_case_with_relations(db, case_id)
