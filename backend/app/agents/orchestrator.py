"""
LangGraph Orchestrator — wires the five agents into a directed graph.

Graph flow:
  intake_node → risk_node → governance_node → decision_node → audit_node

Supports:
  - Progress callbacks for live SSE streaming
  - Fixed LangSmith run_id so the frontend can deep-link to the trace
"""
from __future__ import annotations

import logging
from typing import TypedDict
from uuid import uuid4

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agents import audit_agent, decision_agent, governance_agent, intake_agent, risk_agent
from app.core.config import get_settings
from app.models import Case
from app.services.langsmith_links import build_langsmith_trace_url
from app.services.pipeline_progress import ProgressCallback, emit_progress

logger = logging.getLogger(__name__)

LLM_NODE_TO_STAGE = {
    "intake": "llm_intake",
    "risk": "llm_risk",
    "governance": "llm_governance",
    "decision": "llm_decision",
    "audit": "llm_audit",
}

LLM_NODE_ORDER = ["intake", "risk", "governance", "decision", "audit"]


class PipelineState(TypedDict):
    case: Case
    db: Session
    policy_outcome: str
    final_decision: str
    intake_result: dict
    risk_result: dict
    governance_result: dict
    decision_result: dict
    audit_result: dict
    errors: list[str]


def intake_node(state: PipelineState) -> dict:
    try:
        result = intake_agent.run(state["case"], state["db"])
        return {"intake_result": result}
    except Exception as exc:
        logger.error("intake_agent failed: %s", exc)
        return {"intake_result": {}, "errors": state.get("errors", []) + [f"intake: {exc}"]}


def risk_node(state: PipelineState) -> dict:
    try:
        result = risk_agent.run(state["case"], state["db"])
        return {"risk_result": result}
    except Exception as exc:
        logger.error("risk_agent failed: %s", exc)
        return {"risk_result": {}, "errors": state.get("errors", []) + [f"risk: {exc}"]}


def governance_node(state: PipelineState) -> dict:
    try:
        result = governance_agent.run(state["case"], state.get("risk_result", {}), state["db"])
        return {"governance_result": result}
    except Exception as exc:
        logger.error("governance_agent failed: %s", exc)
        return {"governance_result": {}, "errors": state.get("errors", []) + [f"governance: {exc}"]}


def decision_node(state: PipelineState) -> dict:
    try:
        result = decision_agent.run(
            state["case"],
            state["policy_outcome"],
            state.get("risk_result", {}),
            state.get("governance_result", {}),
            state["db"],
        )
        return {"decision_result": result}
    except Exception as exc:
        logger.error("decision_agent failed: %s", exc)
        return {"decision_result": {}, "errors": state.get("errors", []) + [f"decision: {exc}"]}


def audit_node(state: PipelineState) -> dict:
    try:
        result = audit_agent.run(
            state["case"],
            state["final_decision"],
            state.get("intake_result", {}),
            state.get("risk_result", {}),
            state.get("governance_result", {}),
            state.get("decision_result", {}),
            state["db"],
        )
        return {"audit_result": result}
    except Exception as exc:
        logger.error("audit_agent failed: %s", exc)
        return {"audit_result": {}, "errors": state.get("errors", []) + [f"audit: {exc}"]}


def _build_graph() -> StateGraph:
    graph = StateGraph(PipelineState)

    graph.add_node("intake", intake_node)
    graph.add_node("risk", risk_node)
    graph.add_node("governance", governance_node)
    graph.add_node("decision", decision_node)
    graph.add_node("audit", audit_node)

    graph.set_entry_point("intake")
    graph.add_edge("intake", "risk")
    graph.add_edge("risk", "governance")
    graph.add_edge("governance", "decision")
    graph.add_edge("decision", "audit")
    graph.add_edge("audit", END)

    return graph.compile()


_GRAPH = _build_graph()


def run_pipeline(
    case: Case,
    db: Session,
    policy_outcome: str,
    final_decision: str,
    on_progress: ProgressCallback | None = None,
) -> dict:
    """
    Runs the full LangGraph agent pipeline for a case.

    Returns agent outputs plus langsmith_run_id / langsmith_trace_url when tracing is on.
    """
    settings = get_settings()

    if not settings.enable_llm_agents:
        logger.info("LLM agents disabled — skipping orchestrator for case %s", case.case_id)
        for node in LLM_NODE_ORDER:
            emit_progress(
                on_progress,
                stage=LLM_NODE_TO_STAGE[node],
                status="skipped",
                message="LLM agents disabled",
            )
        return {}

    logger.info("Starting LangGraph pipeline for case %s", case.case_id)

    run_id = uuid4()
    config = {
        "run_id": run_id,
        "run_name": f"case-{case.case_id}",
        "tags": [case.case_id, "evaluation", "langgraph"],
        "metadata": {
            "case_id": case.case_id,
            "customer_name": case.customer_name,
            "final_decision": final_decision,
            "policy_outcome": policy_outcome,
        },
    }

    initial_state: PipelineState = {
        "case": case,
        "db": db,
        "policy_outcome": policy_outcome,
        "final_decision": final_decision,
        "intake_result": {},
        "risk_result": {},
        "governance_result": {},
        "decision_result": {},
        "audit_result": {},
        "errors": [],
    }

    emit_progress(
        on_progress,
        stage="llm_intake",
        status="running",
        message="Intake agent enriching case summary…",
    )

    final_state = dict(initial_state)
    completed_nodes: list[str] = []

    try:
        for chunk in _GRAPH.stream(initial_state, config=config, stream_mode="updates"):
            for node_name, update in chunk.items():
                if isinstance(update, dict):
                    final_state.update(update)
                completed_nodes.append(node_name)
                stage = LLM_NODE_TO_STAGE.get(node_name, f"llm_{node_name}")
                errors = (update or {}).get("errors") if isinstance(update, dict) else None
                status = "error" if errors and any(node_name in e for e in errors) else "done"
                emit_progress(
                    on_progress,
                    stage=stage,
                    status=status,
                    message=f"{node_name} agent finished",
                )

                # Mark the next agent as running
                try:
                    idx = LLM_NODE_ORDER.index(node_name)
                    if idx + 1 < len(LLM_NODE_ORDER):
                        nxt = LLM_NODE_ORDER[idx + 1]
                        emit_progress(
                            on_progress,
                            stage=LLM_NODE_TO_STAGE[nxt],
                            status="running",
                            message=f"{nxt} agent running…",
                        )
                except ValueError:
                    pass
    except Exception as exc:
        logger.error("LangGraph stream failed for case %s: %s", case.case_id, exc)
        raise

    if final_state.get("errors"):
        logger.warning("Pipeline completed with errors: %s", final_state["errors"])

    trace_url = build_langsmith_trace_url(run_id)
    logger.info(
        "LangGraph pipeline complete for case %s (run_id=%s, nodes=%s)",
        case.case_id,
        run_id,
        completed_nodes,
    )

    return {
        "intake": final_state.get("intake_result", {}),
        "risk": final_state.get("risk_result", {}),
        "governance": final_state.get("governance_result", {}),
        "decision": final_state.get("decision_result", {}),
        "audit": final_state.get("audit_result", {}),
        "errors": final_state.get("errors", []),
        "langsmith_run_id": str(run_id),
        "langsmith_trace_url": trace_url,
    }
