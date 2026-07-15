export type Decision = "APPROVE" | "REJECT" | "ESCALATE TO HUMAN REVIEW";

export interface DashboardSummary {
  total_cases: number;
  approved: number;
  rejected: number;
  escalated: number;
  average_risk_score: number;
  average_confidence: number;
  fairness_flags_count: number;
  pending_human_review_count: number;
  recent_activity: Array<{
    case_id: string;
    event_type: string;
    actor: string;
    summary: string;
    created_at: string;
  }>;
  recent_audit_logs: Array<{
    case_id: string;
    event_type: string;
    actor: string;
    summary: string;
    created_at: string;
  }>;
  top_policy_rule_violations: Array<{
    rule_name: string;
    count: number;
  }>;
  system_health: Record<string, string>;
}

export interface DashboardCharts {
  decision_distribution: Array<{ name: string; value: number }>;
  risk_histogram: Array<{ bucket: string; count: number }>;
  rule_violations: Array<{ rule_name: string; count: number }>;
  review_queue_stats: Array<{ status: string; count: number }>;
  activity_over_time: Array<{ date: string; count: number }>;
}

export interface CaseInputSnapshot {
  raw_payload: Record<string, unknown>;
  normalized_payload: Record<string, unknown>;
  derived_fields: Record<string, unknown>;
}

export interface CaseListItem {
  case_id: string;
  customer_name: string;
  customer_id: string;
  requested_product_type: string;
  transaction_type: string;
  model_recommendation: Decision;
  final_decision: Decision | null;
  case_status: string;
  risk_score: number | null;
  risk_level: string | null;
  overall_confidence: number | null;
  policy_version_used: string | null;
  requires_human_review: boolean;
  was_escalated: boolean;
  fairness_flag_count: number;
  created_at: string;
  evaluated_at: string | null;
}

export interface CaseDetail extends Omit<CaseListItem, "evaluated_at"> {
  model_confidence: number;
  evidence_completeness_score: number;
  /** "deterministic" or "llm" — matches backend explanation_mode field */
  explanation_mode: "deterministic" | "llm";
  worker_summary: string | null;
  governance_status: string | null;
  reviewer_note: string | null;
  override_reason: string | null;
  final_explanation: string | null;
  deterministic_explanation: string | null;
  /** LLM-generated explanation (backend field: llm_explanation) */
  llm_explanation: string | null;
  top_risk_factors: Array<{ name: string; score: number; reason: string }> | null;
  blocker_rules: Array<{ rule_name: string; outcome: string; severity: string }> | null;
  langsmith_run_id: string | null;
  langsmith_trace_url: string | null;
  updated_at: string;
  evaluated_at: string | null;
  case_input?: CaseInputSnapshot;
  policy_results: Array<{
    rule_name: string;
    description: string;
    severity: string;
    threshold: number;
    rule_type: string;
    outcome: string;
    triggered: boolean;
    details: Record<string, unknown>;
  }>;
  risk_result: {
    overall_score: number;
    risk_level: string;
    credit_risk: number;
    debt_to_income_risk: number;
    transaction_anomaly_risk: number;
    evidence_weakness_risk: number;
    model_confidence_penalty: number;
    llm_narrative: string | null;
    breakdown: {
      components: Array<{ name: string; score: number; reason: string }>;
      derived_metrics: Record<string, number>;
      top_contributors: Array<{ name: string; score: number; reason: string }>;
    };
  } | null;
  governance_flags: Array<{
    flag_name: string;
    category: string;
    severity: string;
    requires_human_review: boolean;
    /** LLM-generated reasoning for why this flag was raised */
    llm_reasoning: string | null;
    /** Policy document / Chroma source that grounded this flag */
    rag_source: string | null;
    context: Record<string, unknown>;
  }>;
  audit_logs: Array<{
    event_type: string;
    actor: string;
    summary: string;
    created_at: string;
  }>;
  human_reviews: Array<{
    id: number;
    review_status: string;
    reviewer_name: string | null;
    reviewer_note: string | null;
    override_reason: string | null;
    previous_decision: string | null;
    /** The final human decision (APPROVE / REJECT) */
    final_decision: string | null;
    reviewed_at: string | null;
    created_at: string;
  }>;
  llm_usage_logs: Array<{
    agent_name: string;
    model: string;
    provider: string;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    estimated_cost_usd: number;
    latency_ms: number;
  }>;
}

export interface CaseSubmission {
  applicant_name: string;
  customer_id: string;
  age: number;
  annual_income: number;
  monthly_income: number;
  loan_amount: number;
  existing_debt: number;
  monthly_obligations: number;
  credit_score: number;
  employment_status: string;
  years_employed: number;
  country: string;
  region: string;
  transaction_amount: number;
  transaction_type: string;
  purpose: string;
  requested_product_type: string;
  model_recommendation: Decision;
  model_confidence: number;
  evidence_completeness_score: number;
  supporting_evidence_text: string;
  agent_explanation?: string;
  explanation_mode: "deterministic" | "llm";
}

export interface EvaluateCaseResponse {
  case_id: string;
  final_decision: Decision;
  case_status: string;
  risk_score: number;
  risk_level: string;
  policy_version_used: string;
  requires_human_review: boolean;
  explanation: string;
  llm_agents_used: boolean;
  total_tokens_used: number;
  langsmith_run_id?: string | null;
  langsmith_trace_url?: string | null;
}

export type PipelineStageStatus = "pending" | "running" | "done" | "error" | "skipped";

export interface PipelineStageState {
  id: string;
  label: string;
  group: "deterministic" | "llm";
  status: PipelineStageStatus;
  message?: string;
}

export type PipelineStreamEvent =
  | {
      type: "pipeline";
      stages: Array<{ id: string; label: string; group: string }>;
    }
  | {
      type: "stage";
      stage: string;
      label: string;
      status: PipelineStageStatus;
      message?: string;
    }
  | {
      type: "complete";
      case_id: string;
      final_decision: string;
      case_status: string;
      risk_score: number | null;
      risk_level: string | null;
      llm_agents_used: boolean;
      total_tokens_used: number;
      langsmith_run_id: string | null;
      langsmith_trace_url: string | null;
    }
  | { type: "error"; content: string };

/** Matches backend ReviewQueueItem schema */
export interface PendingReview {
  review_id: number;
  case_id: string;
  customer_name: string;
  requested_product_type: string;
  /** What the governance pipeline decided before escalation */
  system_decision: string | null;
  governance_status: string | null;
  risk_score: number | null;
  risk_level: string | null;
  fairness_flag_count: number;
  review_status: string;
  created_at: string;
  reviewer_name?: string | null;
  reviewer_note?: string | null;
  override_reason?: string | null;
  final_decision?: string | null;
  reviewed_at?: string | null;
}

export interface PolicyRule {
  name: string;
  description: string;
  severity: string;
  threshold: number;
  rule_type: string;
  outcome: string;
  enabled: boolean;
}

/** Matches backend PolicyVersionDetail schema */
export interface PolicyVersion {
  id: number;
  version: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_by: string;
  created_at: string;
  /** Not in the backend schema — use created_at as fallback if missing */
  updated_at?: string;
  rules: PolicyRule[];
}

/** Matches backend PolicyVersionOut (history list item) */
export interface PolicyVersionSummary {
  id: number;
  version: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_by: string;
  created_at: string;
  rule_count: number;
}

export interface PolicyListResponse {
  versions: PolicyVersionSummary[];
  total: number;
  active_version: string | null;
}

export interface PolicyUpdateResponse {
  new_version: string;
  previous_version: string | null;
  name: string;
  rule_count: number;
  is_active: boolean;
  created_at: string;
}

// ── Chat ─────────────────────────────────────────────────────────────────────

export interface ChatSession {
  session_id: string;
  title: string | null;
  message_count: number;
  total_tokens_used: number;
  created_at: string;
}

export interface ChatMessage {
  role: "user" | "assistant" | "tool";
  content: string;
  tool_calls: unknown[] | null;
  tool_results: Record<string, unknown> | null;
  created_at: string;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  tools_used: string[];
  tokens_used: number;
  total_session_tokens: number;
}

/** Discriminated union of WebSocket streaming events from the backend */
export type ChatStreamEvent =
  | { type: "tool_start"; tool: string }
  | { type: "tool_done"; tool: string }
  | { type: "stream_start" }
  | { type: "token"; content: string }
  | { type: "stream_end"; tokens_used: number; tools_used: string[] }
  | { type: "error"; content: string };
