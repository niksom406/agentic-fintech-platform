from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CaseInput(Base):
    """
    Stores the raw and normalised input payload for a case.
    Kept separate from Case so the main table stays lean.
    """
    __tablename__ = "case_inputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_pk: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), nullable=False, index=True)

    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)        # exactly what the user submitted
    normalized_payload: Mapped[dict] = mapped_column(JSON, nullable=False) # cleaned and enriched
    derived_fields: Mapped[dict] = mapped_column(JSON, nullable=False)     # computed ratios (DTI, etc.)

    case: Mapped[Case] = relationship("Case", back_populates="case_input")


from app.models.case import Case
