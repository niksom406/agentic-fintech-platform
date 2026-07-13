"""
Human Review Routes — Phase 4.

Endpoints:
  GET  /reviews            → list the review queue (filter by status)
  GET  /reviews/{id}       → get one review's details
  POST /reviews/{id}/decision → reviewer submits their decision
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import get_db
from app.schemas.reviews import (
    ReviewDecisionRequest,
    ReviewDecisionResponse,
    ReviewDetailResponse,
    ReviewQueueItem,
    ReviewQueueResponse,
)
from app.services import review_service
from sqlalchemy.orm import Session

router = APIRouter(prefix="/reviews", tags=["human-review"])


@router.get("", response_model=ReviewQueueResponse)
def list_review_queue(
    status: str | None = Query(default=None, description="Filter: pending | approved | rejected | overridden"),
    db: Session = Depends(get_db),
):
    """
    Returns the human review queue.

    Compliance officers use this to see which cases are waiting for their decision.
    Filter by status to see only pending cases, or see all historical reviews.
    """
    items = review_service.get_review_queue(db, status=status)
    pending_count = sum(1 for i in items if i["review_status"] == "pending")

    return ReviewQueueResponse(
        items=[ReviewQueueItem(**i) for i in items],
        total=len(items),
        pending_count=pending_count,
    )


@router.get("/{review_id}", response_model=ReviewDetailResponse)
def get_review(review_id: int, db: Session = Depends(get_db)):
    """Get the full detail of a single review."""
    row = review_service.get_review_by_id(db, review_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found.")

    review, _case = row
    return ReviewDetailResponse(
        review_id=review.id,
        case_id=_case.case_id,
        review_status=review.review_status,
        reviewer_name=review.reviewer_name,
        reviewer_note=review.reviewer_note,
        override_reason=review.override_reason,
        previous_decision=review.previous_decision,
        final_decision=review.final_decision,
        reviewed_at=review.reviewed_at,
        created_at=review.created_at,
    )


@router.post("/{review_id}/decision", response_model=ReviewDecisionResponse)
def submit_decision(
    review_id: int,
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
):
    """
    Submit a human reviewer's decision on an escalated case.

    This is the core of the human-in-the-loop workflow:
    - Reviewer reads the case, LLM explanations, and governance flags
    - They decide: APPROVE or REJECT
    - If they differ from the system, they must provide an override_reason
    - The decision is written permanently to the audit log
    - The case is marked as completed
    """
    try:
        review = review_service.submit_review_decision(db, review_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Fetch the case_id for the response
    row = review_service.get_review_by_id(db, review_id)
    _review, case = row

    return ReviewDecisionResponse(
        review_id=review.id,
        case_id=case.case_id,
        previous_decision=review.previous_decision,
        final_decision=review.final_decision,
        reviewer_name=review.reviewer_name,
        review_status=review.review_status,
        reviewed_at=review.reviewed_at,
    )
