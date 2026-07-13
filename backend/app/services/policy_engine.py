from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import PolicyVersion

# Synthetic high-risk countries and product combinations for demo purposes
AML_WATCH_COUNTRIES = {"Koranda", "Zetavia", "Novastria", "Drakmoor"}
AML_HIGH_RISK_PRODUCTS = {"Cross-Border Wire", "Trade Finance", "Crypto Transfer", "International Wire"}


def get_active_policy(db: Session) -> PolicyVersion:
    """Fetch the currently active policy version from the database."""
    policy = db.execute(
        select(PolicyVersion)
        .where(PolicyVersion.is_active.is_(True))
        .order_by(desc(PolicyVersion.created_at))
    ).scalar_one_or_none()

    if policy is None:
        raise ValueError("No active policy version found. Run seed first.")
    return policy


def _make_result(rule: dict, version: str, outcome: str, triggered: bool, details: dict) -> dict:
    """Standardised result format for every rule evaluation."""
    return {
        "rule_name": rule["name"],
        "description": rule["description"],
        "severity": rule["severity"],
        "threshold": float(rule["threshold"]),
        "rule_type": rule["rule_type"],
        "version": version,
        "outcome": outcome,
        "triggered": triggered,
        "details": details,
    }


def evaluate_policy_rules(
    normalised: dict,
    derived: dict,
    rules: list[dict],
    version: str,
) -> dict:
    """
    Core policy engine — evaluates every enabled rule against the case data.

    Returns a dict with:
        results:       list of individual rule outcomes
        has_rejection: True if any critical REJECT rule fired
        has_escalation: True if any ESCALATE rule fired
    """
    results: list[dict] = []
    has_rejection = False
    has_escalation = False
    stacked_medium_count = 0

    for rule in rules:
        if not rule.get("enabled", True):
            results.append(_make_result(rule, version, "SKIPPED", False,
                                        {"reason": "Rule disabled in active policy."}))
            continue

        name = rule["name"]
        threshold = float(rule["threshold"])
        triggered = False
        outcome = "PASS"
        details: dict = {}

        # ── Credit ────────────────────────────────────────────────────────────
        if name == "CREDIT_SCORE_MIN":
            triggered = normalised["credit_score"] < threshold
            outcome = "REJECT" if triggered else "PASS"
            details = {
                "credit_score": normalised["credit_score"],
                "threshold": threshold,
            }

        # ── Affordability ─────────────────────────────────────────────────────
        elif name == "DEBT_TO_INCOME_MAX":
            triggered = derived["debt_to_income_ratio"] > threshold
            outcome = "ESCALATE" if triggered else "PASS"
            details = {
                "debt_to_income_ratio": derived["debt_to_income_ratio"],
                "threshold": threshold,
            }

        # ── Model risk ────────────────────────────────────────────────────────
        elif name == "MODEL_CONFIDENCE_MIN":
            triggered = normalised["model_confidence"] < threshold
            outcome = "ESCALATE" if triggered else "PASS"
            details = {
                "model_confidence": normalised["model_confidence"],
                "threshold": threshold,
            }

        # ── Evidence ──────────────────────────────────────────────────────────
        elif name == "EVIDENCE_COMPLETENESS_MIN":
            triggered = normalised["evidence_completeness_score"] < threshold
            outcome = "ESCALATE" if triggered else "PASS"
            details = {
                "evidence_completeness_score": normalised["evidence_completeness_score"],
                "threshold": threshold,
            }

        # ── Transaction risk ──────────────────────────────────────────────────
        elif name == "TRANSACTION_INCOME_RATIO_MAX":
            triggered = derived["transaction_to_income_ratio"] > threshold
            outcome = "ESCALATE" if triggered else "PASS"
            details = {
                "transaction_to_income_ratio": derived["transaction_to_income_ratio"],
                "threshold": threshold,
            }

        result = _make_result(rule, version, outcome, triggered, details)
        results.append(result)

        if triggered:
            if outcome == "REJECT":
                has_rejection = True
            elif outcome == "ESCALATE":
                has_escalation = True
                if rule["severity"] == "medium":
                    stacked_medium_count += 1

    # Stacked medium-risk signals escalate even if individually they wouldn't
    if stacked_medium_count >= 2:
        has_escalation = True

    return {
        "results": results,
        "has_rejection": has_rejection,
        "has_escalation": has_escalation,
        "version": version,
    }
