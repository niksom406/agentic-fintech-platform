from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LLMUsageLog(Base):
    """
    Records every LLM API call made during case evaluation.
    Gives full visibility into: which agent used what model, how many tokens,
    how long it took, and what it cost.
    
    This table is unique to your project — the clone has nothing like this.
    """
    __tablename__ = "llm_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_pk: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), nullable=False, index=True)

    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)   # intake-agent, risk-agent, etc.
    model: Mapped[str] = mapped_column(String(64), nullable=False)        # gpt-4o-mini, llama-3.1-8b-instant
    provider: Mapped[str] = mapped_column(String(32), nullable=False)     # openai, groq

    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False)

    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    case: Mapped[Case] = relationship("Case", back_populates="llm_usage_logs")


from app.models.case import Case
