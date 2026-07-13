"""
LangGraph Orchestrator — wires the five agents into a directed graph.

Graph flow:
  intake_node → risk_node → governance_node → decision_node → audit_node

Each node receives the shared pipeline state, runs its agent,
and writes its output back into state for the next node to read.

If LLM agents are disabled (ENABLE_LLM_AGENTS=false), the orchestrator
returns an empty result immediately — the deterministic pipeline still runs.
"""
from __future__ import annotations

import logging
from typing import TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agents import audit_agent, decision_agent, governance_agent, intake_agent, risk_agent
from app.core.config import get_settings
from app.models import Case

logger = logging.getLogger(__name__)


# ─── Shared Pipeline State ────────────────────────────────────────────────────
# TypedDict defines the schema of the state object passed between nodes.
# Each node reads from state, calls its agent, and writes results back.

class PipelineState(TypedDict):
    case: Case
    db: Session
    policy_outcome: str            # from the deterministic policy engine
    final_decision: str            # set at the end by evaluation_service

    # Agent outputs — filled in as graph progresses
    intake_result: dict
    risk_result: dict
    governance_result: dict
    decision_result: dict
    audit_result: dict

    # Error tracking
    errors: list[str]


# ─── Node Functions ────────────────────────────────────────────────────────────
# Each function receives the full state dict and returns a partial update.
# LangGraph merges the returned dict into the existing state.

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


# ─── Graph Definition ─────────────────────────────────────────────────────────

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


# Compile once at module load — reused across all requests
_GRAPH = _build_graph()


# ─── Public Entry Point ────────────────────────────────────────────────────────

def run_pipeline(
    case: Case,
    db: Session,
    policy_outcome: str,
    final_decision: str,
) -> dict:
    """
    Runs the full LangGraph agent pipeline for a case.

    Returns a dict with all agent outputs, or an empty dict if
    LLM agents are disabled via the ENABLE_LLM_AGENTS setting.
    """
    settings = get_settings()

    if not settings.enable_llm_agents:
        logger.info("LLM agents disabled — skipping orchestrator for case %s", case.case_id)
        return {}

    logger.info("Starting LangGraph pipeline for case %s", case.case_id)

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

    final_state = _GRAPH.invoke(initial_state)

    if final_state.get("errors"):
        logger.warning("Pipeline completed with errors: %s", final_state["errors"])

    logger.info("LangGraph pipeline complete for case %s", case.case_id)

    return {
        "intake": final_state.get("intake_result", {}),
        "risk": final_state.get("risk_result", {}),
        "governance": final_state.get("governance_result", {}),
        "decision": final_state.get("decision_result", {}),
        "audit": final_state.get("audit_result", {}),
        "errors": final_state.get("errors", []),
    }
