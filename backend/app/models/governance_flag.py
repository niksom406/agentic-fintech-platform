from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GovernanceFlag(Base):
    """One row per governance/fairness flag raised for a case."""
    __tablename__ = "governance_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_pk: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), nullable=False, index=True)

    flag_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)   # fairness, evidence, contradiction
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=True)
    context: Mapped[dict] = mapped_column(JSON, nullable=False)

    # LLM-generated reasoning for why this flag was raised
    llm_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Which policy document supported this flag (for RAG, Phase 5)
    rag_source: Mapped[str | None] = mapped_column(String(200), nullable=True)

    case: Mapped[Case] = relationship("Case", back_populates="governance_flags")


from app.models.case import Case
