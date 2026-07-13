from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Input: what a reviewer sends when making a decision ───────────────────────

class ReviewDecisionRequest(BaseModel):
    """
    Posted by the human reviewer to resolve a pending review.

    reviewer_name:  who is making this decision (compliance officer, manager)
    decision:       APPROVE or REJECT — the final human call
    reviewer_note:  required explanation (regulators want this)
    override_reason: required if the human decision differs from system recommendation
    """
    reviewer_name: str = Field(min_length=1, max_length=200)
    decision: Literal["APPROVE", "REJECT"]
    reviewer_note: str = Field(min_length=10, max_length=2000)
    override_reason: str | None = Field(default=None, max_length=2000)


# ── Output schemas ─────────────────────────────────────────────────────────────

class ReviewQueueItem(BaseModel):
    """Summary of a pending review shown in the queue."""
    review_id: int
    case_id: str
    customer_name: str
    requested_product_type: str
    risk_score: float | None
    risk_level: str | None
    system_decision: str | None       # what the pipeline decided before escalation
    governance_status: str | None
    fairness_flag_count: int
    review_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewQueueResponse(BaseModel):
    items: list[ReviewQueueItem]
    total: int
    pending_count: int


class ReviewDecisionResponse(BaseModel):
    """Returned after a reviewer submits their decision."""
    review_id: int
    case_id: str
    previous_decision: str | None
    final_decision: str
    reviewer_name: str
    review_status: str
    reviewed_at: datetime

    model_config = {"from_attributes": True}


class ReviewDetailResponse(BaseModel):
    """Full review detail for a single case."""
    review_id: int
    case_id: str
    review_status: str
    reviewer_name: str | None
    reviewer_note: str | None
    override_reason: str | None
    previous_decision: str | None
    final_decision: str | None
    reviewed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
