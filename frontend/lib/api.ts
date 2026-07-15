import type {
  CaseDetail,
  CaseListItem,
  CaseSubmission,
  ChatMessage,
  ChatResponse,
  ChatSession,
  DashboardCharts,
  DashboardSummary,
  EvaluateCaseResponse,
  PendingReview,
  PolicyListResponse,
  PolicyUpdateResponse,
  PolicyVersion,
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

// ── Dashboard ────────────────────────────────────────────────────────────────

export async function getDashboardSummary() {
  return request<DashboardSummary>("/dashboard/summary");
}

export async function getDashboardCharts() {
  return request<DashboardCharts>("/dashboard/charts");
}

// ── Cases ────────────────────────────────────────────────────────────────────

export async function getCases(params?: Record<string, string>) {
  const search = params ? `?${new URLSearchParams(params).toString()}` : "";
  return request<{ items: CaseListItem[]; total: number }>(`/cases${search}`);
}

export async function getCase(caseId: string) {
  return request<CaseDetail>(`/cases/${caseId}`);
}

export async function createCase(payload: CaseSubmission) {
  return request<{ case_id: string; status: string; created_at: string }>("/cases", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function evaluateCase(caseId: string) {
  return request<EvaluateCaseResponse>(`/cases/${caseId}/evaluate`, {
    method: "POST",
  });
}

/** SSE URL for live pipeline progress while evaluating. */
export function evaluateCaseStreamUrl(caseId: string) {
  return `${API_BASE_URL}/cases/${caseId}/evaluate/stream`;
}

// ── Reviews ──────────────────────────────────────────────────────────────────

export async function getPendingReviews() {
  return request<{ items: PendingReview[]; total: number; pending_count: number }>(
    "/reviews?status=pending",
  );
}

export async function getReviews(status?: string) {
  const search = status ? `?status=${encodeURIComponent(status)}` : "";
  return request<{ items: PendingReview[]; total: number; pending_count: number }>(
    `/reviews${search}`,
  );
}

export async function submitReviewDecision(
  reviewId: number,
  payload: {
    reviewer_name: string;
    decision: "APPROVE" | "REJECT";
    reviewer_note: string;
    override_reason: string | null;
  },
) {
  return request(`/reviews/${reviewId}/decision`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ── Policies ─────────────────────────────────────────────────────────────────

export async function getPolicies() {
  return request<PolicyVersion>("/policies/active");
}

export async function getPolicyHistory() {
  return request<PolicyListResponse>("/policies");
}

export async function getPolicyVersion(policyId: number) {
  return request<PolicyVersion>(`/policies/${policyId}`);
}

export async function updatePolicies(payload: {
  name: string;
  description: string;
  rules: PolicyVersion["rules"];
  created_by: string;
}) {
  return request<PolicyUpdateResponse>("/policies/publish", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function rollbackPolicy(policyId: number) {
  return request<PolicyVersion>(`/policies/${policyId}/rollback`, {
    method: "POST",
  });
}

// ── Audit Export ─────────────────────────────────────────────────────────────

export function auditExportUrl(caseId: string, format: "json" | "txt") {
  return `${API_BASE_URL}/audit/${caseId}/export/${format}`;
}

// ── Chat ────────────────────────────────────────────────────────────────────

export async function startChatSession(firstMessage: string) {
  return request<ChatSession>("/chat/sessions", {
    method: "POST",
    body: JSON.stringify({ first_message: firstMessage }),
  });
}

export async function listChatSessions() {
  return request<ChatSession[]>("/chat/sessions");
}

export async function getChatMessages(sessionId: string) {
  return request<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`);
}

export async function sendChatMessage(sessionId: string, message: string) {
  return request<ChatResponse>(`/chat/sessions/${sessionId}/message`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

/** Returns the WebSocket URL for streaming replies from a session. */
export function getWsChatUrl(sessionId: string) {
  const wsBase = API_BASE_URL.replace(/^http/, "ws");
  return `${wsBase}/chat/sessions/${sessionId}/stream`;
}
