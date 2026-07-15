"""
Audit Export — builds a compliance-grade case package as JSON or TXT.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import get_settings
from app.models.case import Case


def build_audit_payload(case: Case) -> dict:
    """Assemble a full audit package from a loaded Case with relations."""
    return {
        "case_id": case.case_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "customer_name": case.customer_name,
        "customer_id": case.customer_id,
        "decision": case.final_decision,
        "case_status": case.case_status,
        "policy_version_used": case.policy_version_used,
        "worker_summary": case.worker_summary,
        "governance_status": case.governance_status,
        "risk_score": case.risk_score,
        "risk_level": case.risk_level,
        "overall_confidence": case.overall_confidence,
        "top_risk_factors": case.top_risk_factors or [],
        "blocker_rules": case.blocker_rules or [],
        "deterministic_explanation": case.deterministic_explanation,
        "llm_explanation": case.llm_explanation,
        "final_explanation": case.final_explanation,
        "input_payload": case.case_input.normalized_payload if case.case_input else {},
        "derived_fields": case.case_input.derived_fields if case.case_input else {},
        "policy_results": [
            {
                "rule_name": item.rule_name,
                "severity": item.severity,
                "outcome": item.outcome,
                "triggered": item.triggered,
                "details": item.details,
            }
            for item in case.policy_results
        ],
        "governance_flags": [
            {
                "flag_name": item.flag_name,
                "category": item.category,
                "severity": item.severity,
                "requires_human_review": item.requires_human_review,
                "llm_reasoning": item.llm_reasoning,
                "rag_source": item.rag_source,
                "context": item.context,
            }
            for item in case.governance_flags
        ],
        "risk_breakdown": case.risk_result.breakdown if case.risk_result else {},
        "risk_narrative": case.risk_result.llm_narrative if case.risk_result else None,
        "human_reviews": [
            {
                "review_status": review.review_status,
                "reviewer_name": review.reviewer_name,
                "final_decision": review.final_decision,
                "reviewer_note": review.reviewer_note,
                "override_reason": review.override_reason,
                "previous_decision": review.previous_decision,
                "created_at": review.created_at.isoformat() if review.created_at else None,
                "reviewed_at": review.reviewed_at.isoformat() if review.reviewed_at else None,
            }
            for review in case.human_reviews
        ],
        "llm_usage": [
            {
                "agent_name": log.agent_name,
                "model": log.model,
                "provider": log.provider,
                "total_tokens": log.total_tokens,
                "estimated_cost_usd": log.estimated_cost_usd,
                "latency_ms": log.latency_ms,
            }
            for log in case.llm_usage_logs
        ],
        "timeline": [
            {
                "event_type": item.event_type,
                "actor": item.actor,
                "summary": item.summary,
                "details": item.details_json,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in sorted(case.audit_logs, key=lambda log: log.created_at or datetime.min)
        ],
    }


def build_audit_text(payload: dict) -> str:
    """Render the audit package as a readable plain-text report."""
    lines = [
        f"Case ID: {payload['case_id']}",
        f"Generated: {payload['generated_at']}",
        f"Decision: {payload['decision']}",
        f"Status: {payload['case_status']}",
        f"Policy Version: {payload['policy_version_used']}",
        f"Governance Status: {payload['governance_status']}",
        f"Risk Score: {payload['risk_score']} ({payload['risk_level']})",
        "",
        "Worker Summary:",
        payload.get("worker_summary") or "(none)",
        "",
        "Deterministic Explanation:",
        payload.get("deterministic_explanation") or "(none)",
        "",
        "LLM Explanation:",
        payload.get("llm_explanation") or "(none)",
        "",
        "Top Risk Factors:",
    ]
    for item in payload.get("top_risk_factors") or []:
        if isinstance(item, dict):
            lines.append(f"- {item.get('name', '?')}: {item.get('score', '?')}")
        else:
            lines.append(f"- {item}")

    lines.extend(["", "Policy Results:"])
    for item in payload.get("policy_results") or []:
        lines.append(
            f"- {item['rule_name']}: {item['outcome']} (triggered={item['triggered']})"
        )

    lines.extend(["", "Governance Flags:"])
    for item in payload.get("governance_flags") or []:
        rag = f" [RAG: {item['rag_source']}]" if item.get("rag_source") else ""
        lines.append(f"- {item['flag_name']}: {item.get('llm_reasoning') or item.get('category')}{rag}")

    lines.extend(["", "Human Reviews:"])
    for item in payload.get("human_reviews") or []:
        lines.append(
            f"- {item.get('reviewer_name') or 'unknown'}: {item.get('final_decision')} "
            f"({item.get('review_status')})"
        )

    lines.extend(["", "Timeline:"])
    for item in payload.get("timeline") or []:
        lines.append(f"- [{item.get('created_at')}] {item['event_type']} / {item['actor']}: {item['summary']}")

    return "\n".join(lines)


def persist_export(case_id: str, file_format: str, content: str) -> Path:
    """Write the export to AUDIT_EXPORT_DIR and return the path."""
    settings = get_settings()
    export_dir = Path(settings.audit_export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    path = export_dir / f"{case_id}_audit_report.{file_format}"
    path.write_text(content, encoding="utf-8")
    return path


def export_case_audit(case: Case, file_format: str) -> tuple[str, str]:
    """
    Build and persist an audit export.

    Returns: (content, filename)
    """
    payload = build_audit_payload(case)
    if file_format == "json":
        content = json.dumps(payload, indent=2, default=str)
        filename = f"{case.case_id}_audit_report.json"
    elif file_format == "txt":
        content = build_audit_text(payload)
        filename = f"{case.case_id}_audit_report.txt"
    else:
        raise ValueError(f"Unsupported format: {file_format}")

    persist_export(case.case_id, file_format, content)
    return content, filename
