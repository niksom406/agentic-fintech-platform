from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PolicyResult(Base):
    """One row per policy rule evaluated for a case."""
    __tablename__ = "policy_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_pk: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), nullable=False, index=True)

    rule_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)   # critical, high, medium
    threshold: Mapped[float] = mapped_column(nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)    # PASS, REJECT, ESCALATE, SKIPPED
    triggered: Mapped[bool] = mapped_column(Boolean, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False)

    case: Mapped[Case] = relationship("Case", back_populates="policy_results")


from app.models.case import Case
