"""
Policy Management Routes — Phase 4.

Endpoints:
  GET  /policies                    → list all policy versions
  GET  /policies/active             → get the currently active policy (with full rules)
  GET  /policies/{id}               → get a specific version (with full rules)
  POST /policies/publish            → publish a new version (deactivates current)
  POST /policies/{id}/rollback      → roll back to a specific older version
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.database import get_db
from app.schemas.policies import (
    PolicyCreateRequest,
    PolicyListResponse,
    PolicyUpdateResponse,
    PolicyVersionDetail,
    PolicyVersionOut,
)
from app.services import policy_service
from sqlalchemy.orm import Session

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("", response_model=PolicyListResponse)
def list_policies(db: Session = Depends(get_db)):
    """
    Lists all policy versions with their metadata.

    This is the version history — every past policy is preserved.
    You can see which version was active when, and compare rule counts.
    """
    versions = policy_service.list_policy_versions(db)
    active = next((v for v in versions if v.is_active), None)

    return PolicyListResponse(
        versions=[
            PolicyVersionOut(
                id=v.id,
                version=v.version,
                name=v.name,
                description=v.description,
                is_active=v.is_active,
                created_by=v.created_by,
                created_at=v.created_at,
                rule_count=len(v.rules_json) if v.rules_json else 0,
            )
            for v in versions
        ],
        total=len(versions),
        active_version=active.version if active else None,
    )


@router.get("/active", response_model=PolicyVersionDetail)
def get_active_policy(db: Session = Depends(get_db)):
    """Returns the currently active policy with full rule definitions."""
    policy = policy_service.get_active_policy_version(db)
    if policy is None:
        raise HTTPException(status_code=404, detail="No active policy found.")

    return PolicyVersionDetail(
        id=policy.id,
        version=policy.version,
        name=policy.name,
        description=policy.description,
        rules=policy.rules_json,
        is_active=policy.is_active,
        created_by=policy.created_by,
        created_at=policy.created_at,
    )


@router.get("/{policy_id}", response_model=PolicyVersionDetail)
def get_policy_version(policy_id: int, db: Session = Depends(get_db)):
    """Returns a specific policy version with full rule definitions."""
    policy = policy_service.get_policy_version_by_id(db, policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail=f"Policy version {policy_id} not found.")

    return PolicyVersionDetail(
        id=policy.id,
        version=policy.version,
        name=policy.name,
        description=policy.description,
        rules=policy.rules_json,
        is_active=policy.is_active,
        created_by=policy.created_by,
        created_at=policy.created_at,
    )


@router.post("/publish", response_model=PolicyUpdateResponse, status_code=201)
def publish_policy(payload: PolicyCreateRequest, db: Session = Depends(get_db)):
    """
    Publishes a new policy version and makes it the active policy.

    The previous version is deactivated but preserved in history.
    All future case evaluations will use the new rules immediately.
    Past cases remain linked to the version they were evaluated against.

    Example use case: compliance team tightens the DTI threshold from 0.45 to 0.40
    after a regulatory update. They publish a new version. New cases get stricter
    rules. Old cases still show which (looser) rules were used at decision time.
    """
    try:
        new_policy, prev_version = policy_service.publish_new_policy(db, payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return PolicyUpdateResponse(
        new_version=new_policy.version,
        previous_version=prev_version,
        name=new_policy.name,
        rule_count=len(new_policy.rules_json),
        is_active=new_policy.is_active,
        created_at=new_policy.created_at,
    )


@router.post("/{policy_id}/rollback", response_model=PolicyVersionDetail)
def rollback_policy(policy_id: int, db: Session = Depends(get_db)):
    """
    Rolls back to a previously active policy version.

    Useful for quickly reverting a bad policy publish without losing
    the intermediate version history.
    """
    try:
        policy = policy_service.rollback_to_version(db, policy_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return PolicyVersionDetail(
        id=policy.id,
        version=policy.version,
        name=policy.name,
        description=policy.description,
        rules=policy.rules_json,
        is_active=policy.is_active,
        created_by=policy.created_by,
        created_at=policy.created_at,
    )
