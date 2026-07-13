from __future__ import annotations


def _score_credit_risk(credit_score: int) -> float:
    """Lower credit score = higher risk. Returns 0–40 (highest weight component)."""
    if credit_score >= 750:
        return 0.0
    if credit_score >= 700:
        return 10.0
    if credit_score >= 650:
        return 20.0
    if credit_score >= 600:
        return 30.0
    return 40.0


def _score_dti_risk(dti: float) -> float:
    """Higher DTI = higher risk. Returns 0–25."""
    if dti <= 0.28:
        return 0.0
    if dti <= 0.36:
        return 8.0
    if dti <= 0.43:
        return 15.0
    if dti <= 0.50:
        return 20.0
    return 25.0


def _score_transaction_risk(tx_to_income_ratio: float) -> float:
    """Large transaction relative to income is suspicious. Returns 0–15."""
    if tx_to_income_ratio <= 1.0:
        return 0.0
    if tx_to_income_ratio <= 2.0:
        return 5.0
    if tx_to_income_ratio <= 3.5:
        return 10.0
    return 15.0


def _score_evidence_risk(completeness: float, text_length: int) -> float:
    """Incomplete or thin evidence = higher risk. Returns 0–10."""
    score = 0.0
    if completeness < 0.60:
        score += 6.0
    elif completeness < 0.75:
        score += 3.0
    if text_length < 50:
        score += 4.0
    elif text_length < 100:
        score += 2.0
    return min(score, 10.0)


def _score_confidence_penalty(confidence: float) -> float:
    """Low model confidence adds risk. Returns 0–10."""
    if confidence >= 0.80:
        return 0.0
    if confidence >= 0.65:
        return 4.0
    if confidence >= 0.55:
        return 7.0
    return 10.0


def _risk_level(score: float) -> str:
    if score <= 25:
        return "Low"
    if score <= 50:
        return "Medium"
    if score <= 75:
        return "High"
    return "Critical"


def compute_risk(normalised: dict, derived: dict) -> dict:
    """
    Computes a composite risk score from 5 components.
    Each component has a maximum contribution (weights sum to 100).

    Returns a full breakdown so the UI and agents can show exactly
    why the score is what it is.
    """
    credit_risk = _score_credit_risk(normalised["credit_score"])
    dti_risk = _score_dti_risk(derived["debt_to_income_ratio"])
    tx_risk = _score_transaction_risk(derived["transaction_to_income_ratio"])
    evidence_risk = _score_evidence_risk(
        normalised["evidence_completeness_score"],
        derived["evidence_text_length"],
    )
    confidence_penalty = _score_confidence_penalty(normalised["model_confidence"])

    overall = round(credit_risk + dti_risk + tx_risk + evidence_risk + confidence_penalty, 1)
    overall_confidence = round(
        (normalised["model_confidence"] + normalised["evidence_completeness_score"]) / 2, 3
    )

    # Top risk factors — sorted by contribution, for display and agent context
    factors = [
        {"name": "Credit Risk", "score": credit_risk, "reason": f"Credit score {normalised['credit_score']}"},
        {"name": "Debt-to-Income Risk", "score": dti_risk, "reason": f"DTI {derived['debt_to_income_ratio']:.0%}"},
        {"name": "Transaction Anomaly", "score": tx_risk, "reason": f"Tx/Income ratio {derived['transaction_to_income_ratio']:.1f}x"},
        {"name": "Evidence Weakness", "score": evidence_risk, "reason": f"Completeness {normalised['evidence_completeness_score']:.0%}"},
        {"name": "Confidence Penalty", "score": confidence_penalty, "reason": f"Confidence {normalised['model_confidence']:.0%}"},
    ]
    top_factors = sorted(
        [f for f in factors if f["score"] > 0],
        key=lambda x: x["score"],
        reverse=True,
    )[:3]

    return {
        "overall_score": overall,
        "risk_level": _risk_level(overall),
        "overall_confidence": overall_confidence,
        "credit_risk": credit_risk,
        "debt_to_income_risk": dti_risk,
        "transaction_anomaly_risk": tx_risk,
        "evidence_weakness_risk": evidence_risk,
        "model_confidence_penalty": confidence_penalty,
        "top_risk_factors": top_factors,
        "breakdown": {
            "credit_risk": credit_risk,
            "dti_risk": dti_risk,
            "transaction_risk": tx_risk,
            "evidence_risk": evidence_risk,
            "confidence_penalty": confidence_penalty,
            "max_possible": 100,
        },
    }
