from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Case(Base):
    """
    The central table. One row = one financial case moving through the pipeline.
    All other tables link back to this via case_pk (foreign key).
    """
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    # Customer info
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Product and transaction
    requested_product_type: Mapped[str] = mapped_column(String(100), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # What the AI model recommended coming in
    model_recommendation: Mapped[str] = mapped_column(String(50), nullable=False)
    model_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_completeness_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Pipeline outputs
    case_status: Mapped[str] = mapped_column(String(50), default="intake_completed")
    final_decision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    overall_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    policy_version_used: Mapped[str | None] = mapped_column(String(20), nullable=True)
    governance_status: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Flags
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    was_escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    fairness_flag_count: Mapped[int] = mapped_column(Integer, default=0)

    # Agent outputs (LLM-generated text — your differentiator)
    explanation_mode: Mapped[str] = mapped_column(String(30), default="deterministic")
    worker_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    deterministic_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)  # real LLM output

    # JSON columns for flexible data
    top_risk_factors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    blocker_rules: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships — SQLAlchemy loads related rows automatically
    case_input: Mapped[CaseInput | None] = relationship("CaseInput", back_populates="case", uselist=False)
    policy_results: Mapped[list[PolicyResult]] = relationship("PolicyResult", back_populates="case")
    risk_result: Mapped[RiskResult | None] = relationship("RiskResult", back_populates="case", uselist=False)
    governance_flags: Mapped[list[GovernanceFlag]] = relationship("GovernanceFlag", back_populates="case")
    human_reviews: Mapped[list[HumanReview]] = relationship("HumanReview", back_populates="case")
    audit_logs: Mapped[list[AuditLog]] = relationship("AuditLog", back_populates="case", order_by="AuditLog.created_at")
    llm_usage_logs: Mapped[list[LLMUsageLog]] = relationship("LLMUsageLog", back_populates="case")


from app.models.case_input import CaseInput
from app.models.policy_result import PolicyResult
from app.models.risk_result import RiskResult
from app.models.governance_flag import GovernanceFlag
from app.models.human_review import HumanReview
from app.models.audit_log import AuditLog
from app.models.llm_usage_log import LLMUsageLog
