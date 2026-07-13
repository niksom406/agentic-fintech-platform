from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class HumanReview(Base):
    """Tracks the human reviewer's decision on an escalated case."""
    __tablename__ = "human_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_pk: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), nullable=False, index=True)

    review_status: Mapped[str] = mapped_column(String(30), default="pending")  # pending, approved, rejected, overridden
    reviewer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_decision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    final_decision: Mapped[str | None] = mapped_column(String(50), nullable=True)

    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    case: Mapped[Case] = relationship("Case", back_populates="human_reviews")


from app.models.case import Case
