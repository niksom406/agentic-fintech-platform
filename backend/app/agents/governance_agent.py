"""
Governance Agent — Stage 3 of the LLM pipeline.

Audits the case for fairness, explainability, and ethical concerns.
Runs independently of the risk score — it looks at process quality.

Phase 5 upgrade: Before calling the LLM, this agent now:
1. Queries ChromaDB for relevant policy passages (vector search)
2. Uses GraphRAG to expand the search to related policy areas
3. Injects the retrieved policy text directly into the prompt

This means the LLM reasons against ACTUAL current policy text,
not just its training data. When policy changes, the agent's
reasoning changes automatically — no retraining needed.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.agents.base_agent import run_agent
from app.models import Case, GovernanceFlag
from app.rag.retriever import retrieve_policy_context


def run(case: Case, risk_result: dict, db: Session) -> dict:
    """
    Runs the RAG-augmented governance agent.

    Steps:
    1. Collect case context and existing governance flags
    2. Query ChromaDB + GraphRAG for relevant policy passages
    3. Build the LLM prompt with policy context injected
    4. Call the LLM
    5. Persist the reasoning back to governance flags
    """
    flags = db.query(GovernanceFlag).filter(GovernanceFlag.case_pk == case.id).all()
    flags_data = [
        {
            "flag_name": f.flag_name,
            "category": f.category,
            "severity": f.severity,
            "requires_human_review": f.requires_human_review,
            "context": f.context,
        }
        for f in flags
    ]

    # Build case context dict for the RAG retriever
    rag_context = {
        "risk_score": case.risk_score,
        "risk_level": case.risk_level,
        "governance_flags": flags_data,
        "model_confidence": case.model_confidence,
        "product": case.requested_product_type,
    }

    # ── Step 1: GraphRAG retrieval ─────────────────────────────────────────────
    # Retrieves relevant policy passages using:
    #   - Vector similarity search in ChromaDB
    #   - Graph traversal to find related policy areas
    # Returns formatted text ready to inject into the prompt.
    policy_context = retrieve_policy_context(rag_context)

    # ── Step 2: Build the case payload ────────────────────────────────────────
    payload = {
        "case_id": case.case_id,
        "product": case.requested_product_type,
        "transaction_type": case.transaction_type,
        "model_recommendation": case.model_recommendation,
        "model_confidence": case.model_confidence,
        "evidence_completeness_score": case.evidence_completeness_score,
        "governance_flags_raised": flags_data,
        "risk_agent_narrative": risk_result.get("narrative", ""),
        "risk_tier": risk_result.get("risk_tier", ""),
        "model_explanation_quality": (
            "Model confidence provided but no qualitative explanation"
            if case.model_confidence else "No model confidence score available"
        ),
    }

    # ── Step 3: Build the user message with policy context injected ───────────
    # Policy passages come BEFORE the case data so the LLM reads the rules
    # before seeing the specific case — this anchors its reasoning in policy.
    if policy_context:
        user_content = (
            "RETRIEVED POLICY DOCUMENTS (use these to ground your assessment):\n\n"
            f"{policy_context}\n\n"
            "═══════════════════════════════════════\n\n"
            "Now perform a governance and fairness audit for this specific case:\n\n"
            f"{json.dumps(payload, indent=2)}"
        )
    else:
        user_content = (
            f"Perform a governance and fairness audit for this case:\n\n"
            f"{json.dumps(payload, indent=2)}"
        )

    # ── Step 4: Call the LLM ──────────────────────────────────────────────────
    result = run_agent(
        agent_name="governance_agent",
        prompt_file="governance.txt",
        user_content=user_content,
        case_id=case.case_id,
        case_pk=case.id,
        db=db,
        max_tokens=900,  # slightly more tokens — LLM now references specific policy text
    )

    # ── Step 5: Persist reasoning back to governance flags ────────────────────
    if flags and isinstance(result, dict) and "overall_assessment" in result:
        for flag in flags:
            # Store which policy passages were retrieved for this flag
            flag.llm_reasoning = result["overall_assessment"]
            flag.rag_source = f"chroma:policy_documents (seeds from flag: {flag.flag_name})"
        db.flush()

    return result if isinstance(result, dict) else {}
