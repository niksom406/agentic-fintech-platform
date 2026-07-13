from __future__ import annotations

# Synthetic data — not real countries, safe for demo
FAIRNESS_SENSITIVE_CONTEXTS = {
    "countries": {"Eldoria", "Verantis", "Morvaine"},
    "products": {"Microfinance", "Community Loan"},
}


def _make_flag(name: str, category: str, severity: str, requires_review: bool, context: dict) -> dict:
    return {
        "flag_name": name,
        "category": category,
        "severity": severity,
        "requires_human_review": requires_review,
        "context": context,
        "llm_reasoning": None,   # filled by LLM agent in Phase 3
        "rag_source": None,       # filled by RAG in Phase 5
    }


def evaluate_governance(
    normalised: dict,
    derived: dict,
    policy_results: list[dict],
    risk_output: dict,
) -> dict:
    """
    Checks for conditions that require human oversight regardless of risk score.
    These are governance and fairness signals, not hard financial rules.

    In Phase 3, the Governance Agent LLM will replace / augment this logic.
    """
    flags: list[dict] = []

    # 1. Contradictory recommendation — model says APPROVE but rules say REJECT/ESCALATE
    triggered_blockers = [r for r in policy_results if r["triggered"] and r["outcome"] in {"REJECT", "ESCALATE"}]
    if normalised["model_recommendation"] == "APPROVE" and triggered_blockers:
        flags.append(_make_flag(
            "CONTRADICTORY_RECOMMENDATION",
            "contradiction",
            "high",
            True,
            {
                "model_recommendation": "APPROVE",
                "triggered_rules": [r["rule_name"] for r in triggered_blockers],
            },
        ))

    # 2. Weak agent explanation — very short or missing
    explanation = normalised.get("agent_explanation") or ""
    if len(explanation.strip()) < 40:
        flags.append(_make_flag(
            "WEAK_EXPLANATION",
            "evidence",
            "medium",
            True,
            {"explanation_length": len(explanation.strip())},
        ))

    # 3. Fairness-sensitive context — escalate for human review, never auto-decide
    country = normalised.get("country", "")
    product = normalised.get("requested_product_type", "")
    if country in FAIRNESS_SENSITIVE_CONTEXTS["countries"] or product in FAIRNESS_SENSITIVE_CONTEXTS["products"]:
        flags.append(_make_flag(
            "FAIRNESS_SENSITIVE_CONTEXT",
            "fairness",
            "high",
            True,
            {"country": country, "product_type": product},
        ))

    # 4. High risk + model mismatch — model confident but score is high
    if risk_output["risk_level"] in {"High", "Critical"} and normalised["model_confidence"] >= 0.80:
        flags.append(_make_flag(
            "HIGH_RISK_CONFIDENT_MODEL",
            "model_risk",
            "medium",
            True,
            {
                "risk_level": risk_output["risk_level"],
                "model_confidence": normalised["model_confidence"],
            },
        ))

    requires_review = any(f["requires_human_review"] for f in flags)
    fairness_count = sum(1 for f in flags if f["category"] == "fairness")

    status = (
        "Governance review required." if requires_review
        else "No governance concerns identified."
    )

    return {
        "flags": flags,
        "requires_human_review": requires_review,
        "fairness_flag_count": fairness_count,
        "governance_status": status,
    }
