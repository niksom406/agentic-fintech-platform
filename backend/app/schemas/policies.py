from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Rule schema (one rule inside a policy) ────────────────────────────────────

class PolicyRule(BaseModel):
    """
    Defines a single policy rule.

    name:       unique identifier used by the policy engine (e.g. CREDIT_SCORE_MIN)
    rule_type:  what field this rule evaluates
    threshold:  the numeric limit
    severity:   how serious a breach is
    outcome:    what happens when the rule triggers
    enabled:    rules can be toggled off without deleting them
    """
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=500)
    rule_type: str = Field(min_length=1, max_length=100)
    threshold: float
    severity: Literal["low", "medium", "high", "critical"]
    outcome: Literal["REJECT", "ESCALATE", "PASS"]
    enabled: bool = True


# ── Input: creating or updating a policy version ──────────────────────────────

class PolicyCreateRequest(BaseModel):
    """
    Used to publish a new policy version.
    The old active version is automatically deactivated.
    This creates an immutable snapshot — old versions are never deleted.
    """
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    rules: list[PolicyRule] = Field(min_length=1)
    created_by: str = Field(min_length=1, max_length=200)


# ── Output schemas ─────────────────────────────────────────────────────────────

class PolicyVersionOut(BaseModel):
    """Single policy version summary."""
    id: int
    version: str
    name: str
    description: str | None
    is_active: bool
    created_by: str
    created_at: datetime
    rule_count: int

    model_config = {"from_attributes": True}


class PolicyVersionDetail(BaseModel):
    """Full policy version with all rules."""
    id: int
    version: str
    name: str
    description: str | None
    rules: list[dict]        # the raw rules_json — flexible for display
    is_active: bool
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PolicyListResponse(BaseModel):
    versions: list[PolicyVersionOut]
    total: int
    active_version: str | None


class PolicyUpdateResponse(BaseModel):
    """Returned after a new policy version is published."""
    new_version: str
    previous_version: str | None
    name: str
    rule_count: int
    is_active: bool
    created_at: datetime
