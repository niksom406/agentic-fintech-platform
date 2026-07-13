from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Case, PolicyVersion
from app.schemas.cases import CaseSubmission
from app.services.evaluation_service import evaluate_case
from app.services.intake_service import create_case


def seed_policy_versions(db: Session) -> None:
    if db.query(PolicyVersion).count() > 0:
        return

    default_rules = [
        {
            "name": "CREDIT_SCORE_MIN",
            "description": "Reject if credit score falls below the minimum threshold.",
            "severity": "critical",
            "threshold": 580.0,
            "rule_type": "credit",
            "enabled": True,
        },
        {
            "name": "DEBT_TO_INCOME_MAX",
            "description": "Escalate if debt-to-income ratio exceeds the governed threshold.",
            "severity": "high",
            "threshold": 0.43,
            "rule_type": "affordability",
            "enabled": True,
        },
        {
            "name": "MODEL_CONFIDENCE_MIN",
            "description": "Escalate low-confidence model recommendations.",
            "severity": "high",
            "threshold": 0.55,
            "rule_type": "model_risk",
            "enabled": True,
        },
        {
            "name": "EVIDENCE_COMPLETENESS_MIN",
            "description": "Escalate if evidence completeness score is below threshold.",
            "severity": "high",
            "threshold": 0.60,
            "rule_type": "evidence",
            "enabled": True,
        },
        {
            "name": "TRANSACTION_INCOME_RATIO_MAX",
            "description": "Escalate if transaction is unusually large relative to monthly income.",
            "severity": "medium",
            "threshold": 5.0,
            "rule_type": "transaction",
            "enabled": True,
        },
    ]

    db.add(PolicyVersion(
        version="1.0.0",
        name="Initial Policy Baseline",
        description="Default governance rules for financial case evaluation.",
        rules_json=default_rules,
        is_active=True,
        created_by="system",
    ))
    db.commit()


DEMO_CASES = [
    {
        "applicant_name": "Ava Sterling",
        "customer_id": "CUST-0001",
        "age": 36,
        "annual_income": 112000, "monthly_income": 9333,
        "loan_amount": 240000, "existing_debt": 900, "monthly_obligations": 1800,
        "credit_score": 762, "employment_status": "Full Time", "years_employed": 8,
        "country": "United Kingdom", "region": "London",
        "transaction_amount": 8500, "transaction_type": "Bank Transfer",
        "purpose": "Home purchase", "requested_product_type": "Residential Mortgage",
        "model_recommendation": "APPROVE", "model_confidence": 0.89,
        "evidence_completeness_score": 0.92,
        "supporting_evidence_text": "Verified payslips, tax filings, employer confirmation, and signed affordability disclosure attached.",
        "agent_explanation": "Stable income, low affordability stress, and complete documentation support approval.",
        "explanation_mode": "deterministic",
    },
    {
        "applicant_name": "Leo Carter",
        "customer_id": "CUST-0002",
        "age": 29,
        "annual_income": 54000, "monthly_income": 4500,
        "loan_amount": 190000, "existing_debt": 700, "monthly_obligations": 900,
        "credit_score": 541, "employment_status": "Full Time", "years_employed": 3,
        "country": "United Kingdom", "region": "Manchester",
        "transaction_amount": 2800, "transaction_type": "Bank Transfer",
        "purpose": "Debt consolidation", "requested_product_type": "Personal Loan",
        "model_recommendation": "APPROVE", "model_confidence": 0.81,
        "evidence_completeness_score": 0.88,
        "supporting_evidence_text": "Income verification and debt schedule supplied.",
        "agent_explanation": "Model favours approval on recent income growth despite weaker credit.",
        "explanation_mode": "deterministic",
    },
    {
        "applicant_name": "Nina Rahman",
        "customer_id": "CUST-0003",
        "age": 42,
        "annual_income": 78000, "monthly_income": 6500,
        "loan_amount": 125000, "existing_debt": 1200, "monthly_obligations": 2100,
        "credit_score": 682, "employment_status": "Contract", "years_employed": 4,
        "country": "United Kingdom", "region": "Birmingham",
        "transaction_amount": 6400, "transaction_type": "Bank Transfer",
        "purpose": "Business expansion", "requested_product_type": "SME Working Capital",
        "model_recommendation": "APPROVE", "model_confidence": 0.73,
        "evidence_completeness_score": 0.79,
        "supporting_evidence_text": "Signed contracts, current bank statements, and management accounts included.",
        "agent_explanation": "Business cash flow adequate but monthly commitments elevated.",
        "explanation_mode": "deterministic",
    },
    {
        "applicant_name": "James Okafor",
        "customer_id": "CUST-0004",
        "age": 38,
        "annual_income": 95000, "monthly_income": 7917,
        "loan_amount": 320000, "existing_debt": 500, "monthly_obligations": 1200,
        "credit_score": 720, "employment_status": "Full Time", "years_employed": 10,
        "country": "United Kingdom", "region": "Bristol",
        "transaction_amount": 4200, "transaction_type": "Bank Transfer",
        "purpose": "Property investment", "requested_product_type": "Residential Mortgage",
        "model_recommendation": "APPROVE", "model_confidence": 0.48,
        "evidence_completeness_score": 0.85,
        "supporting_evidence_text": "Full affordability assessment, property valuation, and solicitor correspondence attached.",
        "agent_explanation": "Strong profile but low model confidence warrants review.",
        "explanation_mode": "deterministic",
    },
    {
        "applicant_name": "Priya Mehta",
        "customer_id": "CUST-0005",
        "age": 31,
        "annual_income": 61000, "monthly_income": 5083,
        "loan_amount": 85000, "existing_debt": 400, "monthly_obligations": 600,
        "credit_score": 695, "employment_status": "Full Time", "years_employed": 6,
        "country": "United Kingdom", "region": "Leeds",
        "transaction_amount": 3100, "transaction_type": "Bank Transfer",
        "purpose": "Home improvement", "requested_product_type": "Personal Loan",
        "model_recommendation": "APPROVE", "model_confidence": 0.83,
        "evidence_completeness_score": 0.38,
        "supporting_evidence_text": "Partial evidence pack. Some documents pending.",
        "agent_explanation": "Evidence package incomplete.",
        "explanation_mode": "deterministic",
    },
]


def seed_demo_cases(db: Session) -> None:
    if db.query(Case).count() > 0:
        return

    for case_data in DEMO_CASES:
        submission = CaseSubmission(**case_data)
        case = create_case(db, submission)
        evaluate_case(db, case.case_id)


def seed_demo_data(db: Session) -> None:
    seed_policy_versions(db)
    seed_demo_cases(db)
