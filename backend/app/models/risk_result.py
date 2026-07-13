from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RiskResult(Base):
    """
    One row per evaluated case — the full risk breakdown.
    Includes both numeric scores AND the LLM-generated narrative (your differentiator).
    """
    __tablename__ = "risk_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_pk: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), nullable=False, unique=True)

    # Numeric scores
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)  # Low, Medium, High, Critical
    credit_risk: Mapped[float] = mapped_column(Float, nullable=False)
    debt_to_income_risk: Mapped[float] = mapped_column(Float, nullable=False)
    transaction_anomaly_risk: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_weakness_risk: Mapped[float] = mapped_column(Float, nullable=False)
    model_confidence_penalty: Mapped[float] = mapped_column(Float, nullable=False)

    # Structured breakdown
    breakdown: Mapped[dict] = mapped_column(JSON, nullable=False)

    # LLM-generated explanation — this is what makes your project different
    llm_narrative: Mapped[str | None] = mapped_column(Text, nullable=True)

    case: Mapped[Case] = relationship("Case", back_populates="risk_result")


from app.models.case import Case
