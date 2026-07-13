"""
Human Review Service — Phase 4.

Manages the queue of escalated cases waiting for human decisions.

Key concepts:
- Only cases with requires_human_review=True appear in the queue
- A reviewer submits APPROVE or REJECT (they can override the system)
- Every decision is written to audit_logs — permanent, immutable record
- If the human overrides the system, override_reason is required
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Case, HumanReview
from app.schemas.reviews import ReviewDecisionRequest


def get_review_queue(db: Session, status: str | None = None) -> list[dict]:
    """
    Returns all cases in the human review queue.

    Joins HumanReview with Case to return the full context a reviewer needs.
    Optionally filter by status: pending, approved, rejected, overridden.
    """
    stmt = (
        select(HumanReview, Case)
        .join(Case, HumanReview.case_pk == Case.id)
        .order_by(HumanReview.created_at.desc())
    )
    if status:
        stmt = stmt.where(HumanReview.review_status == status)

    rows = db.execute(stmt).all()

    items = []
    for review, case in rows:
        items.append({
            "review_id": review.id,
            "case_id": case.case_id,
            "customer_name": case.customer_name,
            "requested_product_type": case.requested_product_type,
            "risk_score": case.risk_score,
            "risk_level": case.risk_level,
            "system_decision": review.previous_decision,
            "governance_status": case.governance_status,
            "fairness_flag_count": case.fairness_flag_count,
            "review_status": review.review_status,
            "created_at": review.created_at,
        })
    return items


def get_review_by_id(db: Session, review_id: int) -> tuple[HumanReview, Case] | None:
    """Fetch a single review with its associated case."""
    row = db.execute(
        select(HumanReview, Case)
        .join(Case, HumanReview.case_pk == Case.id)
        .where(HumanReview.id == review_id)
    ).one_or_none()
    return row  # (HumanReview, Case) or None


def submit_review_decision(
    db: Session,
    review_id: int,
    payload: ReviewDecisionRequest,
) -> HumanReview:
    """
    Records a human reviewer's decision on an escalated case.

    Steps:
    1. Validate the review exists and is still pending
    2. Check if this is an override (human differs from system)
    3. Require override_reason if it is an override
    4. Update HumanReview row with decision
    5. Update Case status and final_decision
    6. Write an immutable AuditLog entry
    7. Commit everything atomically
    """
    row = get_review_by_id(db, review_id)
    if row is None:
        raise ValueError(f"Review {review_id} not found.")

    review, case = row

    if review.review_status != "pending":
        raise ValueError(
            f"Review {review_id} is already {review.review_status}. Cannot re-submit."
        )

    # Detect override: human chose something different from the pipeline recommendation
    system_decision = (review.previous_decision or "").upper()
    human_decision = payload.decision.upper()
    is_override = (
        system_decision not in ("", human_decision)
        and system_decision != "ESCALATE TO HUMAN REVIEW"
    )

    if is_override and not payload.override_reason:
        raise ValueError(
            "override_reason is required when your decision differs from the system recommendation."
        )

    # Determine final review status
    if human_decision == "APPROVE":
        review_status = "approved"
    else:
        review_status = "rejected"
    if is_override:
        review_status = "overridden"

    # Update the review record
    review.review_status = review_status
    review.reviewer_name = payload.reviewer_name
    review.reviewer_note = payload.reviewer_note
    review.override_reason = payload.override_reason
    review.final_decision = human_decision
    review.reviewed_at = datetime.utcnow()

    # Update the case
    case.final_decision = human_decision
    case.case_status = "completed"
    case.requires_human_review = False
    case.updated_at = datetime.utcnow()

    # Write an immutable audit log entry
    audit_summary = (
        f"Human review by {payload.reviewer_name}: decision={human_decision}. "
        f"{'OVERRIDE — ' + payload.override_reason if is_override else 'Confirmed system recommendation.'}"
    )
    db.add(AuditLog(
        case_pk=case.id,
        event_type="HUMAN_REVIEW_DECISION",
        actor=f"human:{payload.reviewer_name}",
        summary=audit_summary,
        details_json={
            "decision": human_decision,
            "reviewer_note": payload.reviewer_note,
            "override_reason": payload.override_reason,
            "is_override": is_override,
            "system_recommendation": system_decision,
        },
    ))

    db.commit()
    db.refresh(review)
    return review
