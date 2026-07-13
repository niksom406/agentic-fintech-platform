from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Input schema (what the frontend sends) ────────────────────────────────────

class CaseSubmission(BaseModel):
    """Everything needed to create and evaluate a financial case."""
    # Customer
    applicant_name: str = Field(min_length=1, max_length=200)
    customer_id: str = Field(min_length=1, max_length=64)
    age: int = Field(ge=18, le=100)

    # Financials
    annual_income: float = Field(gt=0)
    monthly_income: float = Field(gt=0)
    loan_amount: float = Field(gt=0)
    existing_debt: float = Field(ge=0)
    monthly_obligations: float = Field(ge=0)
    credit_score: int = Field(ge=300, le=850)
    employment_status: str = Field(min_length=1, max_length=50)
    years_employed: float = Field(ge=0)

    # Location
    country: str = Field(min_length=1, max_length=100)
    region: str = Field(min_length=1, max_length=100)

    # Transaction
    transaction_amount: float = Field(gt=0)
    transaction_type: str = Field(min_length=1, max_length=100)
    purpose: str = Field(min_length=1, max_length=300)
    requested_product_type: str = Field(min_length=1, max_length=100)

    # Model signal (what the upstream AI recommended)
    model_recommendation: Literal["APPROVE", "REJECT", "ESCALATE TO HUMAN REVIEW"]
    model_confidence: float = Field(ge=0.0, le=1.0)
    evidence_completeness_score: float = Field(ge=0.0, le=1.0)
    supporting_evidence_text: str = Field(min_length=10, max_length=4000)
    agent_explanation: str | None = Field(default=None, max_length=4000)
    explanation_mode: Literal["deterministic", "llm"] = "deterministic"


# ── Output schemas (what the API returns) ─────────────────────────────────────

class CaseCreateResponse(BaseModel):
    case_id: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseListItem(BaseModel):
    case_id: str
    customer_name: str
    customer_id: str
    requested_product_type: str
    transaction_type: str
    model_recommendation: str
    final_decision: str | None
    case_status: str
    risk_score: float | None
    risk_level: str | None
    overall_confidence: float | None
    policy_version_used: str | None
    requires_human_review: bool
    was_escalated: bool
    fairness_flag_count: int
    created_at: datetime
    evaluated_at: datetime | None

    model_config = {"from_attributes": True}


class CaseListResponse(BaseModel):
    items: list[CaseListItem]
    total: int


class EvaluateCaseResponse(BaseModel):
    case_id: str
    final_decision: str
    case_status: str
    risk_score: float | None
    risk_level: str | None
    policy_version_used: str | None
    explanation: str | None
    requires_human_review: bool
    llm_agents_used: bool
    total_tokens_used: int

    model_config = {"from_attributes": True}


class PolicyResultOut(BaseModel):
    rule_name: str
    description: str
    severity: str
    threshold: float
    outcome: str
    triggered: bool
    details: dict

    model_config = {"from_attributes": True}


class GovernanceFlagOut(BaseModel):
    flag_name: str
    category: str
    severity: str
    requires_human_review: bool
    context: dict
    llm_reasoning: str | None

    model_config = {"from_attributes": True}


class RiskResultOut(BaseModel):
    overall_score: float
    risk_level: str
    credit_risk: float
    debt_to_income_risk: float
    transaction_anomaly_risk: float
    evidence_weakness_risk: float
    model_confidence_penalty: float
    breakdown: dict
    llm_narrative: str | None

    model_config = {"from_attributes": True}


class AuditLogOut(BaseModel):
    event_type: str
    actor: str
    summary: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LLMUsageOut(BaseModel):
    agent_name: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    latency_ms: int

    model_config = {"from_attributes": True}


class CaseInputOut(BaseModel):
    raw_payload: dict
    normalized_payload: dict
    derived_fields: dict
    model_config = {"from_attributes": True}


class CaseDetailResponse(BaseModel):
    case_id: str
    customer_name: str
    customer_id: str
    requested_product_type: str
    transaction_type: str
    model_recommendation: str
    model_confidence: float
    evidence_completeness_score: float
    final_decision: str | None
    case_status: str
    risk_score: float | None
    risk_level: str | None
    overall_confidence: float | None
    policy_version_used: str | None
    requires_human_review: bool
    was_escalated: bool
    fairness_flag_count: int
    governance_status: str | None
    explanation_mode: str
    worker_summary: str | None
    final_explanation: str | None
    deterministic_explanation: str | None
    llm_explanation: str | None
    top_risk_factors: list | None
    blocker_rules: list | None
    created_at: datetime
    evaluated_at: datetime | None
    updated_at: datetime
    case_input: CaseInputOut | None = None
    policy_results: list[PolicyResultOut] = []
    risk_result: RiskResultOut | None = None
    governance_flags: list[GovernanceFlagOut] = []
    audit_logs: list[AuditLogOut] = []
    llm_usage_logs: list[LLMUsageOut] = []

    model_config = {"from_attributes": True}
