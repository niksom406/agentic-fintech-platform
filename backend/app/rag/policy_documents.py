"""
Policy knowledge base — the documents embedded into ChromaDB.

In production these would be loaded from PDFs (regulatory filings,
internal policy manuals, compliance guidelines). For this project
we write structured text that covers the key governance domains.

Each document has:
  id:       unique identifier (used for deduplication)
  text:     the actual policy content that gets embedded
  metadata: structured tags for filtering (category, severity, regulation)

The metadata lets us filter before semantic search — e.g. only search
fairness documents when evaluating a fairness concern.
"""
from __future__ import annotations

POLICY_DOCUMENTS: list[dict] = [

    # ── Credit Risk ────────────────────────────────────────────────────────────

    {
        "id": "credit-001",
        "text": (
            "Credit Score Minimum Requirements: All lending products require a minimum "
            "credit score of 580 for standard evaluation. Applicants with scores below 580 "
            "are automatically declined due to elevated default risk. Scores between 580-620 "
            "represent elevated risk and require additional income verification. Scores above "
            "720 are considered prime and qualify for preferential terms. Credit scores must "
            "be sourced from approved bureaus (Experian, TransUnion, Equifax) within 90 days "
            "of application."
        ),
        "metadata": {"category": "credit_risk", "severity": "critical", "regulation": "internal"},
    },
    {
        "id": "credit-002",
        "text": (
            "Credit History Assessment: Beyond the numeric score, underwriters must review "
            "the pattern of credit usage. A recent bankruptcy (within 7 years) is an automatic "
            "disqualifier for mortgage products. More than 3 missed payments in the last 24 months "
            "triggers mandatory escalation. Collections accounts over $500 must be explained. "
            "Thin credit files (fewer than 3 trade lines) require alternative credit documentation "
            "such as rental payment history or utility payment records."
        ),
        "metadata": {"category": "credit_risk", "severity": "high", "regulation": "internal"},
    },

    # ── Affordability / DTI ────────────────────────────────────────────────────

    {
        "id": "dti-001",
        "text": (
            "Debt-to-Income Ratio Policy: The maximum allowable debt-to-income ratio is 43% "
            "for conventional mortgage products, following Consumer Financial Protection Bureau "
            "(CFPB) qualified mortgage guidelines. For personal loans and working capital, "
            "the maximum DTI is 50%. DTI is calculated as total monthly debt obligations "
            "divided by gross monthly income. Obligations include: mortgage or rent, car payments, "
            "student loans, minimum credit card payments, and the proposed new payment. "
            "Applications exceeding the DTI threshold must be escalated for manual review "
            "unless compensating factors are present (substantial assets, large down payment)."
        ),
        "metadata": {"category": "affordability", "severity": "high", "regulation": "CFPB"},
    },
    {
        "id": "dti-002",
        "text": (
            "Compensating Factors for DTI Exceptions: When a case exceeds the standard DTI "
            "threshold, the following compensating factors may justify approval after human review: "
            "(1) Verified liquid assets exceeding 12 months of housing payments; "
            "(2) Demonstrated history of successfully managing similar payment levels; "
            "(3) Significant equity in existing properties; "
            "(4) Strong employment history with documented income growth trajectory; "
            "(5) Low loan-to-value ratio below 70%. No single factor is sufficient — "
            "reviewers must document which factors apply and explain the risk rationale."
        ),
        "metadata": {"category": "affordability", "severity": "high", "regulation": "internal"},
    },

    # ── Fair Lending / ECOA ────────────────────────────────────────────────────

    {
        "id": "fairness-001",
        "text": (
            "Equal Credit Opportunity Act (ECOA) Compliance: All lending decisions must comply "
            "with ECOA, which prohibits discrimination based on race, color, religion, national "
            "origin, sex, marital status, age, or receipt of public assistance. Decisions must "
            "be based solely on creditworthiness factors. Geographic location may be considered "
            "only when directly relevant to risk (e.g. flood zones for property insurance) and "
            "must not be used as a proxy for protected characteristics. Any model that uses "
            "zip codes or neighborhood demographics must be regularly tested for disparate impact."
        ),
        "metadata": {"category": "fairness", "severity": "critical", "regulation": "ECOA"},
    },
    {
        "id": "fairness-002",
        "text": (
            "Fair Housing Act Compliance for Mortgage Products: The Fair Housing Act prohibits "
            "discriminatory practices in residential mortgage lending. Redlining — refusing loans "
            "in minority neighborhoods — is illegal. Reverse redlining — targeting high-cost "
            "products at minority communities — is also prohibited. All mortgage applications must "
            "be evaluated on their individual merits. Geographic risk factors must have a documented, "
            "non-discriminatory business justification. AI models used in lending must be regularly "
            "audited for disparate impact on protected groups."
        ),
        "metadata": {"category": "fairness", "severity": "critical", "regulation": "FHA"},
    },
    {
        "id": "fairness-003",
        "text": (
            "Disparate Impact Analysis: Even facially neutral policies can violate fair lending "
            "laws if they have a disproportionate adverse impact on protected classes. Lenders "
            "must conduct regular disparate impact testing on all automated decision systems. "
            "If a policy produces a statistically significant adverse impact, the lender must "
            "demonstrate it is a business necessity and that no less discriminatory alternative "
            "exists. AI-generated recommendations must be explainable to the applicant in plain "
            "language, and the explanation must not reference protected characteristics."
        ),
        "metadata": {"category": "fairness", "severity": "high", "regulation": "ECOA"},
    },

    # ── Model Risk / AI Governance ─────────────────────────────────────────────

    {
        "id": "model-risk-001",
        "text": (
            "Model Risk Management Policy (SR 11-7): AI and machine learning models used in "
            "credit decisions must comply with Federal Reserve SR 11-7 guidance on model risk "
            "management. This requires: (1) Model validation by an independent team before "
            "deployment; (2) Ongoing monitoring of model performance and stability; "
            "(3) Documentation of model inputs, outputs, assumptions and limitations; "
            "(4) Fallback procedures when models behave unexpectedly; "
            "(5) Human override capability for all model-driven decisions. "
            "Low confidence model recommendations (below 60%) must always be escalated to human review."
        ),
        "metadata": {"category": "model_risk", "severity": "high", "regulation": "SR 11-7"},
    },
    {
        "id": "model-risk-002",
        "text": (
            "Explainability Requirements for AI Decisions: All AI-assisted credit decisions "
            "must be explainable to the applicant upon request, per the Fair Credit Reporting Act "
            "and CFPB guidance. The explanation must identify the principal reasons for the "
            "decision — typically the top 4 factors that influenced the outcome. Generic "
            "explanations (e.g., 'model score was low') are insufficient. The explanation "
            "must be specific enough that the applicant can take action to improve their "
            "creditworthiness. Model explanations must not reference variables that are "
            "proxies for protected characteristics."
        ),
        "metadata": {"category": "model_risk", "severity": "high", "regulation": "FCRA"},
    },

    # ── Human Review / Escalation ──────────────────────────────────────────────

    {
        "id": "escalation-001",
        "text": (
            "Human Review Escalation Policy: Cases must be escalated to human review when: "
            "(1) The AI model recommendation contradicts the deterministic policy outcome; "
            "(2) The debt-to-income ratio exceeds the governed threshold; "
            "(3) The model confidence score is below 55%; "
            "(4) Evidence completeness score is below 60%; "
            "(5) The transaction amount exceeds 5x the applicant's monthly income; "
            "(6) Any governance flag of HIGH or CRITICAL severity is raised. "
            "Escalated cases must be reviewed within 3 business days. The reviewer must "
            "document their reasoning and any compensating factors considered."
        ),
        "metadata": {"category": "escalation", "severity": "high", "regulation": "internal"},
    },
    {
        "id": "escalation-002",
        "text": (
            "Override Documentation Requirements: When a human reviewer overrides the system "
            "recommendation, they must document: (1) The specific reason for the override; "
            "(2) Which compensating factors were considered; (3) Any additional information "
            "obtained beyond the automated assessment; (4) Confirmation that the decision "
            "complies with fair lending requirements. Override decisions are reviewed quarterly "
            "by the Chief Risk Officer for pattern analysis. Reviewers who consistently override "
            "in one direction must justify this pattern."
        ),
        "metadata": {"category": "escalation", "severity": "medium", "regulation": "internal"},
    },

    # ── AML / Transaction Risk ─────────────────────────────────────────────────

    {
        "id": "aml-001",
        "text": (
            "Anti-Money Laundering (AML) Transaction Screening: Transactions must be screened "
            "against OFAC sanctions lists and high-risk country lists. Transactions originating "
            "from or destined to high-risk jurisdictions require enhanced due diligence. "
            "Cash transactions above $10,000 require Currency Transaction Reports (CTR). "
            "Structuring — breaking large transactions into smaller ones to avoid reporting — "
            "is a federal crime. Unusual transaction patterns relative to the customer's "
            "established profile trigger Suspicious Activity Report (SAR) obligations."
        ),
        "metadata": {"category": "aml", "severity": "critical", "regulation": "BSA"},
    },
    {
        "id": "aml-002",
        "text": (
            "Know Your Customer (KYC) Requirements: All applicants must complete KYC verification "
            "before any lending product is approved. KYC includes: identity verification (government "
            "ID), address verification, beneficial ownership for businesses, and source of funds "
            "documentation for large transactions. Enhanced due diligence applies to politically "
            "exposed persons (PEPs) and their associates. KYC documentation must be refreshed "
            "every 3 years for active customers and immediately when suspicious activity is detected."
        ),
        "metadata": {"category": "aml", "severity": "critical", "regulation": "FinCEN"},
    },

    # ── Audit / Compliance ─────────────────────────────────────────────────────

    {
        "id": "audit-001",
        "text": (
            "Audit Trail Requirements: All lending decisions must maintain a complete, immutable "
            "audit trail including: the data used at decision time, which policy version was applied, "
            "all automated rule evaluations and their outcomes, any governance flags raised, "
            "the final decision and its reasoning, and the identity of any human reviewer involved. "
            "Audit records must be retained for 7 years minimum. Records must be tamper-evident "
            "and timestamped. In the event of a regulatory inquiry, the full decision history "
            "must be reconstructable from the audit log."
        ),
        "metadata": {"category": "audit", "severity": "high", "regulation": "internal"},
    },
    {
        "id": "audit-002",
        "text": (
            "Adverse Action Notice Requirements: When a credit application is declined or "
            "approved on less favorable terms, the applicant must receive an Adverse Action Notice "
            "within 30 days. The notice must include: the principal reasons for the decision "
            "(up to 4 factors), the credit bureau used and how to obtain a free report, "
            "contact information for the decision maker, and information about the applicant's "
            "right to dispute inaccurate information. AI-generated decisions must produce "
            "human-readable adverse action reasons — not model scores."
        ),
        "metadata": {"category": "audit", "severity": "critical", "regulation": "ECOA"},
    },
]
