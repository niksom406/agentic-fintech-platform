"""
Chat Tools — the functions the chatbot agent can call.

Tool-calling works like this:
1. User asks: "What happened with James Mitchell's case?"
2. LLM sees it needs real data, decides to call: get_case_by_customer_name("James Mitchell")
3. Our code runs the actual DB query
4. Returns real data to the LLM
5. LLM uses that data to write a clear, accurate answer

Without tools, the LLM would guess or hallucinate. With tools, it reads real data.

Each tool is defined in two places:
- TOOL_DEFINITIONS: the JSON schema OpenAI uses to understand what the tool does
- execute_tool(): the actual Python code that runs when the LLM calls the tool
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Case, HumanReview, PolicyVersion
from app.rag.retriever import retrieve_policy_context

logger = logging.getLogger(__name__)


# ── Tool Definitions (OpenAI function-calling schema) ─────────────────────────
# These tell the LLM: "here are the tools available, here's what each does,
# here are the parameters you need to provide."

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_cases",
            "description": (
                "List financial cases in the system. Can filter by decision (APPROVE, REJECT, "
                "'ESCALATE TO HUMAN REVIEW'), risk level (Low, Medium, High, Critical), "
                "or search by customer name. Returns a summary of each case."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "decision": {
                        "type": "string",
                        "description": "Filter by final decision: APPROVE, REJECT, or ESCALATE TO HUMAN REVIEW",
                    },
                    "risk_level": {
                        "type": "string",
                        "description": "Filter by risk level: Low, Medium, High, Critical",
                    },
                    "search": {
                        "type": "string",
                        "description": "Search by customer name or case ID",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of cases to return (default 5)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_case",
            "description": (
                "Get full details of a specific case including risk score, policy results, "
                "governance flags, LLM explanation, and audit trail. Use when the user asks "
                "about a specific case ID or customer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {
                        "type": "string",
                        "description": "The case ID (e.g. CSE-20260713143503-1483BF)",
                    },
                },
                "required": ["case_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_review_queue",
            "description": (
                "Get the human review queue — cases escalated and waiting for a compliance "
                "officer's decision. Can filter by status: pending, approved, rejected, overridden."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status: pending, approved, rejected, overridden",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_policy",
            "description": (
                "Get the currently active policy version with all its rules — credit score "
                "thresholds, DTI limits, etc. Use when the user asks about current policy rules."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_policy_documents",
            "description": (
                "Search the policy knowledge base (ChromaDB) for relevant regulatory guidance. "
                "Use when the user asks about regulations (ECOA, SR 11-7, CFPB), compliance "
                "requirements, or how to handle specific situations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The policy question or topic to search for",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_stats",
            "description": (
                "Get overall system statistics: total cases, breakdown by decision, "
                "pending reviews count, total token usage and cost. Use for dashboard summaries."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


# ── Tool Execution ─────────────────────────────────────────────────────────────

def execute_tool(tool_name: str, arguments: dict, db: Session) -> str:
    """
    Dispatches a tool call to the appropriate function.
    Returns a JSON string with the result — this goes back to the LLM.
    """
    logger.info("Executing tool: %s(%s)", tool_name, arguments)

    try:
        if tool_name == "list_cases":
            return _list_cases(db, **arguments)
        elif tool_name == "get_case":
            return _get_case(db, **arguments)
        elif tool_name == "get_review_queue":
            return _get_review_queue(db, **arguments)
        elif tool_name == "get_active_policy":
            return _get_active_policy(db)
        elif tool_name == "search_policy_documents":
            return _search_policy_documents(**arguments)
        elif tool_name == "get_system_stats":
            return _get_system_stats(db)
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
    except Exception as exc:
        logger.error("Tool %s failed: %s", tool_name, exc)
        return json.dumps({"error": str(exc)})


def _list_cases(
    db: Session,
    decision: str | None = None,
    risk_level: str | None = None,
    search: str | None = None,
    limit: int = 5,
) -> str:
    stmt = select(Case).order_by(Case.created_at.desc()).limit(min(limit, 20))
    if decision:
        stmt = stmt.where(Case.final_decision == decision)
    if risk_level:
        stmt = stmt.where(Case.risk_level == risk_level)
    if search:
        stmt = stmt.where(
            Case.customer_name.ilike(f"%{search}%") | Case.case_id.ilike(f"%{search}%")
        )

    cases = list(db.execute(stmt).scalars().all())
    result = [
        {
            "case_id": c.case_id,
            "customer_name": c.customer_name,
            "product": c.requested_product_type,
            "final_decision": c.final_decision,
            "risk_score": c.risk_score,
            "risk_level": c.risk_level,
            "case_status": c.case_status,
            "requires_human_review": c.requires_human_review,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in cases
    ]
    return json.dumps({"cases": result, "count": len(result)})


def _get_case(db: Session, case_id: str) -> str:
    case = db.execute(select(Case).where(Case.case_id == case_id)).scalar_one_or_none()
    if not case:
        return json.dumps({"error": f"Case {case_id} not found."})

    return json.dumps({
        "case_id": case.case_id,
        "customer_name": case.customer_name,
        "product": case.requested_product_type,
        "final_decision": case.final_decision,
        "risk_score": case.risk_score,
        "risk_level": case.risk_level,
        "case_status": case.case_status,
        "policy_version_used": case.policy_version_used,
        "requires_human_review": case.requires_human_review,
        "governance_status": case.governance_status,
        "explanation_mode": case.explanation_mode,
        "llm_explanation": case.llm_explanation,
        "top_risk_factors": case.top_risk_factors,
        "blocker_rules": case.blocker_rules,
        "evaluated_at": case.evaluated_at.isoformat() if case.evaluated_at else None,
    })


def _get_review_queue(db: Session, status: str | None = None) -> str:
    stmt = (
        select(HumanReview, Case)
        .join(Case, HumanReview.case_pk == Case.id)
        .order_by(HumanReview.created_at.desc())
    )
    if status:
        stmt = stmt.where(HumanReview.review_status == status)

    rows = db.execute(stmt).all()
    items = [
        {
            "review_id": r.id,
            "case_id": c.case_id,
            "customer_name": c.customer_name,
            "product": c.requested_product_type,
            "risk_level": c.risk_level,
            "review_status": r.review_status,
            "reviewer_name": r.reviewer_name,
            "final_decision": r.final_decision,
        }
        for r, c in rows
    ]
    pending = sum(1 for i in items if i["review_status"] == "pending")
    return json.dumps({"reviews": items, "total": len(items), "pending": pending})


def _get_active_policy(db: Session) -> str:
    policy = db.execute(
        select(PolicyVersion).where(PolicyVersion.is_active.is_(True))
    ).scalar_one_or_none()

    if not policy:
        return json.dumps({"error": "No active policy found."})

    return json.dumps({
        "version": policy.version,
        "name": policy.name,
        "description": policy.description,
        "is_active": policy.is_active,
        "created_by": policy.created_by,
        "rules": policy.rules_json,
    })


def _search_policy_documents(query: str) -> str:
    context = retrieve_policy_context(
        case_context={"governance_flags": [], "risk_level": ""},
        query=query,
        max_hops=1,
    )
    if not context:
        return json.dumps({"result": "No relevant policy documents found."})
    return json.dumps({"policy_context": context})


def _get_system_stats(db: Session) -> str:
    from sqlalchemy import func as sqlfunc
    from app.models import LLMUsageLog

    total_cases = db.execute(select(sqlfunc.count(Case.id))).scalar()
    approved = db.execute(
        select(sqlfunc.count(Case.id)).where(Case.final_decision == "APPROVE")
    ).scalar()
    rejected = db.execute(
        select(sqlfunc.count(Case.id)).where(Case.final_decision == "REJECT")
    ).scalar()
    escalated = db.execute(
        select(sqlfunc.count(Case.id)).where(Case.requires_human_review.is_(True))
    ).scalar()
    pending_reviews = db.execute(
        select(sqlfunc.count(HumanReview.id)).where(HumanReview.review_status == "pending")
    ).scalar()

    token_stats = db.execute(
        select(
            sqlfunc.sum(LLMUsageLog.total_tokens),
            sqlfunc.sum(LLMUsageLog.estimated_cost_usd),
        )
    ).one()

    return json.dumps({
        "total_cases": total_cases,
        "approved": approved,
        "rejected": rejected,
        "escalated_or_pending": escalated,
        "pending_human_reviews": pending_reviews,
        "total_llm_tokens": int(token_stats[0] or 0),
        "total_llm_cost_usd": round(float(token_stats[1] or 0), 6),
    })
