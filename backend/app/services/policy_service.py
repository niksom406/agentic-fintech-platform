"""
Policy Service — Phase 4.

Manages policy versioning: creating new versions, activating them,
and reading version history.

Key concepts:
- Only ONE version is active at a time (is_active=True)
- When a new version is published, the old one is deactivated
- Old versions are NEVER deleted — cases always reference their evaluation version
- Version numbers auto-increment as semver patch (1.0.0 → 1.0.1 → 1.0.2)
- This means decisions are always reproducible: re-run any old case against
  the exact policy it was originally evaluated with
"""
from __future__ import annotations

from sqlalchemy import desc, select, update
from sqlalchemy.orm import Session

from app.models import PolicyVersion
from app.schemas.policies import PolicyCreateRequest


def _next_version(current: str) -> str:
    """
    Increments the patch number of a semver string.
    1.0.0 → 1.0.1,  2.3.4 → 2.3.5
    """
    parts = current.split(".")
    if len(parts) == 3:
        parts[2] = str(int(parts[2]) + 1)
        return ".".join(parts)
    return current + ".1"


def get_active_policy_version(db: Session) -> PolicyVersion | None:
    """Returns the currently active policy version, or None."""
    return db.execute(
        select(PolicyVersion)
        .where(PolicyVersion.is_active.is_(True))
        .order_by(desc(PolicyVersion.created_at))
    ).scalar_one_or_none()


def list_policy_versions(db: Session) -> list[PolicyVersion]:
    """Returns all policy versions, newest first."""
    return list(
        db.execute(
            select(PolicyVersion).order_by(desc(PolicyVersion.created_at))
        ).scalars().all()
    )


def get_policy_version_by_id(db: Session, version_id: int) -> PolicyVersion | None:
    """Fetch a specific policy version by its database ID."""
    return db.get(PolicyVersion, version_id)


def publish_new_policy(
    db: Session,
    payload: PolicyCreateRequest,
) -> tuple[PolicyVersion, str | None]:
    """
    Publishes a new active policy version.

    Steps:
    1. Find the current active version (to deactivate and get its version number)
    2. Auto-compute the next version number
    3. Deactivate all current active versions
    4. Create the new version as active
    5. Return (new_version, previous_version_string)

    This is atomic — either both the deactivation and creation succeed, or neither does.
    """
    # Find current active version
    current = get_active_policy_version(db)
    previous_version = current.version if current else None

    # Compute next version number
    if previous_version:
        new_version_str = _next_version(previous_version)
    else:
        new_version_str = "1.0.0"

    # Deactivate all currently active versions
    db.execute(
        update(PolicyVersion)
        .where(PolicyVersion.is_active.is_(True))
        .values(is_active=False)
    )

    # Create new version
    rules_as_dicts = [rule.model_dump() for rule in payload.rules]
    new_policy = PolicyVersion(
        version=new_version_str,
        name=payload.name,
        description=payload.description,
        rules_json=rules_as_dicts,
        is_active=True,
        created_by=payload.created_by,
    )
    db.add(new_policy)
    db.commit()
    db.refresh(new_policy)

    return new_policy, previous_version


def rollback_to_version(db: Session, version_id: int) -> PolicyVersion:
    """
    Rolls back to a specific previous version by making it active again.

    This does NOT delete the current version — it just deactivates it.
    Useful for quickly reverting a bad policy update.
    """
    target = get_policy_version_by_id(db, version_id)
    if target is None:
        raise ValueError(f"Policy version {version_id} not found.")

    # Deactivate all active versions
    db.execute(
        update(PolicyVersion)
        .where(PolicyVersion.is_active.is_(True))
        .values(is_active=False)
    )

    # Re-activate the target
    target.is_active = True
    db.commit()
    db.refresh(target)
    return target
