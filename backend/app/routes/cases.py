from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Case
from app.schemas.cases import (
    CaseCreateResponse,
    CaseDetailResponse,
    CaseListItem,
    CaseListResponse,
    CaseSubmission,
    EvaluateCaseResponse,
)
from app.services.evaluation_service import evaluate_case, get_case_with_relations
from app.services.intake_service import create_case

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseCreateResponse, status_code=201)
def create_case_route(payload: CaseSubmission, db: Session = Depends(get_db)):
    """
    Step 1: Submit a new financial case.
    Normalises input, computes derived ratios, stores to DB.
    Returns a case_id — use it to call /evaluate next.
    """
    case = create_case(db, payload)
    return CaseCreateResponse(
        case_id=case.case_id,
        status=case.case_status,
        created_at=case.created_at,
    )


@router.post("/{case_id}/evaluate", response_model=EvaluateCaseResponse)
def evaluate_case_route(case_id: str, db: Session = Depends(get_db)):
    """
    Step 2: Run the full governance pipeline on an existing case.
    Policy engine → Risk engine → Governance engine → Decision.
    In Phase 3, real LLM agents will run inside this pipeline.
    """
    try:
        case = evaluate_case(db, case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    total_tokens = sum(log.total_tokens for log in case.llm_usage_logs)

    return EvaluateCaseResponse(
        case_id=case.case_id,
        final_decision=case.final_decision,
        case_status=case.case_status,
        risk_score=case.risk_score,
        risk_level=case.risk_level,
        policy_version_used=case.policy_version_used,
        explanation=case.final_explanation,
        requires_human_review=case.requires_human_review,
        llm_agents_used=len(case.llm_usage_logs) > 0,
        total_tokens_used=total_tokens,
    )


@router.get("", response_model=CaseListResponse)
def list_cases(
    decision: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    escalated: bool | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """List all cases with optional filters."""
    stmt = select(Case).order_by(Case.created_at.desc())
    filters = []

    if decision:
        filters.append(Case.final_decision == decision)
    if risk_level:
        filters.append(Case.risk_level == risk_level)
    if escalated is not None:
        filters.append(Case.was_escalated.is_(escalated))
    if search:
        filters.append(
            (Case.customer_name.ilike(f"%{search}%")) |
            (Case.case_id.ilike(f"%{search}%"))
        )
    if filters:
        stmt = stmt.where(and_(*filters))

    items = list(db.execute(stmt).scalars().all())
    return CaseListResponse(
        items=[CaseListItem.model_validate(c) for c in items],
        total=len(items),
    )


@router.get("/{case_id}", response_model=CaseDetailResponse)
def get_case_route(case_id: str, db: Session = Depends(get_db)):
    """Get full case detail including all agent outputs, audit trail, and token usage."""
    case = get_case_with_relations(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")
    return CaseDetailResponse.model_validate(case)
