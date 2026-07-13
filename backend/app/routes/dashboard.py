"""
Dashboard Routes — aggregated KPIs and chart data for the frontend.

Endpoints:
  GET /dashboard/summary → KPI counts, recent activity, system health
  GET /dashboard/charts  → chart-ready datasets (distributions, histograms)
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.case import Case
from app.models.governance_flag import GovernanceFlag
from app.models.human_review import HumanReview
from app.models.policy_result import PolicyResult

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ── helpers ───────────────────────────────────────────────────────────────────

def _scalar(db: Session, stmt) -> int:
    result = db.execute(stmt).scalar()
    return result or 0


# ── GET /dashboard/summary ────────────────────────────────────────────────────

@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)) -> dict:
    """
    Returns aggregated KPI figures, recent activity, and system health
    for the main dashboard page.
    """
    total_cases = _scalar(db, select(func.count(Case.id)))
    approved    = _scalar(db, select(func.count(Case.id)).where(Case.final_decision == "APPROVE"))
    rejected    = _scalar(db, select(func.count(Case.id)).where(Case.final_decision == "REJECT"))
    escalated   = _scalar(db, select(func.count(Case.id)).where(Case.was_escalated.is_(True)))

    avg_risk_score = db.execute(
        select(func.avg(Case.risk_score)).where(Case.risk_score.isnot(None))
    ).scalar() or 0.0

    avg_confidence = db.execute(
        select(func.avg(Case.overall_confidence)).where(Case.overall_confidence.isnot(None))
    ).scalar() or 0.0

    fairness_flags_count = _scalar(db, select(func.count(GovernanceFlag.id)))

    pending_human_review_count = _scalar(
        db,
        select(func.count(HumanReview.id)).where(HumanReview.review_status == "pending"),
    )

    # Recent 10 audit log events with their case_id
    recent_logs_rows = db.execute(
        select(AuditLog, Case.case_id)
        .join(Case, Case.id == AuditLog.case_pk)
        .order_by(AuditLog.created_at.desc())
        .limit(10)
    ).all()

    recent_activity = [
        {
            "case_id": row.case_id,
            "event_type": row.AuditLog.event_type,
            "actor": row.AuditLog.actor,
            "summary": row.AuditLog.summary,
            "created_at": row.AuditLog.created_at.isoformat(),
        }
        for row in recent_logs_rows
    ]

    # Top violated policy rules (across all cases)
    violated_rules = db.execute(
        select(PolicyResult.rule_name, func.count(PolicyResult.id).label("cnt"))
        .where(PolicyResult.triggered.is_(True))
        .group_by(PolicyResult.rule_name)
        .order_by(func.count(PolicyResult.id).desc())
        .limit(5)
    ).all()

    top_policy_rule_violations = [
        {"rule_name": row.rule_name, "count": row.cnt} for row in violated_rules
    ]

    system_health = {
        "total_cases": str(total_cases),
        "pending_reviews": str(pending_human_review_count),
        "fairness_flags": str(fairness_flags_count),
        "approval_rate": f"{round(approved / total_cases * 100, 1)}%" if total_cases else "N/A",
    }

    return {
        "total_cases": total_cases,
        "approved": approved,
        "rejected": rejected,
        "escalated": escalated,
        "average_risk_score": round(float(avg_risk_score), 2),
        "average_confidence": round(float(avg_confidence), 2),
        "fairness_flags_count": fairness_flags_count,
        "pending_human_review_count": pending_human_review_count,
        "recent_activity": recent_activity,
        "recent_audit_logs": recent_activity,   # same feed — both consumed by dashboard
        "top_policy_rule_violations": top_policy_rule_violations,
        "system_health": system_health,
    }


# ── GET /dashboard/charts ─────────────────────────────────────────────────────

@router.get("/charts")
def get_dashboard_charts(db: Session = Depends(get_db)) -> dict:
    """
    Returns chart-ready datasets for decision distribution, risk histogram,
    rule violations, review queue breakdown, and activity over time.
    """
    # Decision distribution
    decision_rows = db.execute(
        select(Case.final_decision, func.count(Case.id).label("cnt"))
        .where(Case.final_decision.isnot(None))
        .group_by(Case.final_decision)
    ).all()
    decision_distribution = [
        {"name": row.final_decision, "value": row.cnt} for row in decision_rows
    ]

    # Risk histogram — bucket risk_score into bands
    all_scores = db.execute(
        select(Case.risk_score).where(Case.risk_score.isnot(None))
    ).scalars().all()

    buckets: dict[str, int] = {
        "0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0
    }
    for score in all_scores:
        if score < 20:
            buckets["0-20"] += 1
        elif score < 40:
            buckets["20-40"] += 1
        elif score < 60:
            buckets["40-60"] += 1
        elif score < 80:
            buckets["60-80"] += 1
        else:
            buckets["80-100"] += 1
    risk_histogram = [{"bucket": k, "count": v} for k, v in buckets.items()]

    # Rule violations per rule
    rule_rows = db.execute(
        select(PolicyResult.rule_name, func.count(PolicyResult.id).label("cnt"))
        .where(PolicyResult.triggered.is_(True))
        .group_by(PolicyResult.rule_name)
        .order_by(func.count(PolicyResult.id).desc())
        .limit(10)
    ).all()
    rule_violations = [{"rule_name": row.rule_name, "count": row.cnt} for row in rule_rows]

    # Review queue stats by status
    review_rows = db.execute(
        select(HumanReview.review_status, func.count(HumanReview.id).label("cnt"))
        .group_by(HumanReview.review_status)
    ).all()
    review_queue_stats = [{"status": row.review_status, "count": row.cnt} for row in review_rows]

    # Activity over time — cases created per day, last 30 days
    cases_by_day_rows = db.execute(
        select(
            func.strftime("%Y-%m-%d", Case.created_at).label("day"),
            func.count(Case.id).label("cnt"),
        )
        .group_by(func.strftime("%Y-%m-%d", Case.created_at))
        .order_by(func.strftime("%Y-%m-%d", Case.created_at))
        .limit(30)
    ).all()
    activity_over_time = [{"date": row.day, "count": row.cnt} for row in cases_by_day_rows]

    return {
        "decision_distribution": decision_distribution,
        "risk_histogram": risk_histogram,
        "rule_violations": rule_violations,
        "review_queue_stats": review_queue_stats,
        "activity_over_time": activity_over_time,
    }
