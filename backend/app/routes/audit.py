"""
Audit Export Routes.

Endpoints:
  GET /audit/{case_id}/export/json → downloadable JSON audit package
  GET /audit/{case_id}/export/txt  → downloadable TXT audit package
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.audit_export import export_case_audit
from app.services.evaluation_service import get_case_with_relations

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/{case_id}/export/json")
def export_audit_json(case_id: str, db: Session = Depends(get_db)) -> Response:
    """Download a full JSON audit package for a case."""
    case = get_case_with_relations(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

    content, filename = export_case_audit(case, "json")
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{case_id}/export/txt")
def export_audit_txt(case_id: str, db: Session = Depends(get_db)) -> Response:
    """Download a plain-text audit report for a case."""
    case = get_case_with_relations(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

    content, filename = export_case_audit(case, "txt")
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
