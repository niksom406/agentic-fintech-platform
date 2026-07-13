from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import AuditLog, Case, CaseInput
from app.schemas.cases import CaseSubmission


def generate_case_id() -> str:
    """Generates a unique, human-readable case ID."""
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    suffix = uuid4().hex[:6].upper()
    return f"CSE-{stamp}-{suffix}"


def normalise_submission(payload: CaseSubmission) -> tuple[dict, dict, str]:
    """
    Step 1 of the pipeline: clean, enrich, and derive fields from raw input.

    Returns:
        normalised_payload: cleaned version of the raw data
        derived_fields: computed ratios used by the policy and risk engines
        worker_summary: plain-English summary of what was submitted
    """
    data = payload.model_dump()

    # Normalise strings — consistent casing prevents rule mismatches
    data["model_recommendation"] = data["model_recommendation"].upper()
    data["employment_status"] = data["employment_status"].strip().title()
    data["country"] = data["country"].strip().title()
    data["region"] = data["region"].strip().title()
    data["transaction_type"] = data["transaction_type"].strip().title()
    data["requested_product_type"] = data["requested_product_type"].strip().title()
    data["supporting_evidence_text"] = data["supporting_evidence_text"].strip()
    if data.get("agent_explanation"):
        data["agent_explanation"] = data["agent_explanation"].strip()

    # Derive income fields if one is missing
    if not data["monthly_income"] and data["annual_income"]:
        data["monthly_income"] = round(data["annual_income"] / 12, 2)
    if not data["annual_income"] and data["monthly_income"]:
        data["annual_income"] = round(data["monthly_income"] * 12, 2)

    monthly_income = max(data["monthly_income"], 1)   # avoid division by zero
    annual_income = max(data["annual_income"], 1)
    combined_obligations = data["existing_debt"] + data["monthly_obligations"]

    # These derived ratios are what the policy rules actually check
    derived = {
        "debt_to_income_ratio": round(combined_obligations / monthly_income, 4),
        "loan_to_income_ratio": round(data["loan_amount"] / annual_income, 4),
        "transaction_to_income_ratio": round(data["transaction_amount"] / monthly_income, 4),
        "evidence_text_length": len(data["supporting_evidence_text"]),
        "combined_monthly_obligations": round(combined_obligations, 2),
        "intake_timestamp": datetime.utcnow().isoformat(),
    }

    # Worker summary — plain English description of the case
    worker_summary = (
        f"{data['applicant_name']} requested {data['requested_product_type']} "
        f"for {data['purpose'].lower()} with a loan of £{data['loan_amount']:,.0f}. "
        f"Model recommendation is {data['model_recommendation']} at "
        f"{data['model_confidence'] * 100:.0f}% confidence. "
        f"Credit score {data['credit_score']}, DTI {derived['debt_to_income_ratio']:.0%}."
    )

    return data, derived, worker_summary


def create_case(db: Session, payload: CaseSubmission) -> Case:
    """
    Creates a case record in the database after normalising the input.
    Also writes the first audit log event: INTAKE.
    """
    normalised, derived, worker_summary = normalise_submission(payload)

    case = Case(
        case_id=generate_case_id(),
        customer_name=normalised["applicant_name"],
        customer_id=normalised["customer_id"],
        requested_product_type=normalised["requested_product_type"],
        transaction_type=normalised["transaction_type"],
        model_recommendation=normalised["model_recommendation"],
        model_confidence=normalised["model_confidence"],
        evidence_completeness_score=normalised["evidence_completeness_score"],
        explanation_mode=normalised["explanation_mode"],
        worker_summary=worker_summary,
        case_status="intake_completed",
        governance_status="Case intake completed.",
    )
    db.add(case)
    db.flush()  # assigns case.id without committing — needed for foreign keys below

    db.add(CaseInput(
        case_pk=case.id,
        raw_payload=payload.model_dump(),
        normalized_payload=normalised,
        derived_fields=derived,
    ))

    db.add(AuditLog(
        case_pk=case.id,
        event_type="INTAKE",
        actor="worker-agent",
        summary="Case intake completed and normalised.",
        details_json={
            "worker_summary": worker_summary,
            "derived_fields": derived,
        },
    ))

    db.commit()
    db.refresh(case)
    return case
