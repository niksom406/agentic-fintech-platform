from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AuditLog(Base):
    """
    Every action on every case is recorded here.
    This is the complete, immutable event trail.
    actor = who/what did it (worker-agent, policy-engine, risk-agent, human:Maria)
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_pk: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), nullable=False, index=True)

    event_type: Mapped[str] = mapped_column(String(60), nullable=False)  # INTAKE, POLICY_EVAL, RISK_SCORING, etc.
    actor: Mapped[str] = mapped_column(String(100), nullable=False)      # worker-agent, risk-agent, human:Maria
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    case: Mapped[Case] = relationship("Case", back_populates="audit_logs")


from app.models.case import Case
