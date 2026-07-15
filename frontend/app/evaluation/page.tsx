"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, ExternalLink, Shield } from "lucide-react";
import type { FormEvent } from "react";
import { useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { AgentPipelineProgress, DEFAULT_STAGES } from "@/components/cases/agent-pipeline-progress";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { createCase, evaluateCaseStreamUrl, getCase } from "@/lib/api";
import type {
  CaseDetail,
  CaseSubmission,
  Decision,
  PipelineStageState,
  PipelineStreamEvent,
} from "@/lib/types";
import { cn } from "@/lib/utils";

/** Empty form — all strings so fields can stay blank until the user types. */
type EvalForm = {
  applicant_name: string;
  customer_id: string;
  age: string;
  annual_income: string;
  monthly_income: string;
  loan_amount: string;
  existing_debt: string;
  monthly_obligations: string;
  credit_score: string;
  employment_status: string;
  years_employed: string;
  country: string;
  region: string;
  transaction_amount: string;
  transaction_type: string;
  purpose: string;
  requested_product_type: string;
  model_recommendation: Decision | "";
  model_confidence: string;
  evidence_completeness_score: string;
  supporting_evidence_text: string;
  agent_explanation: string;
};

const emptyForm: EvalForm = {
  applicant_name: "",
  customer_id: "",
  age: "",
  annual_income: "",
  monthly_income: "",
  loan_amount: "",
  existing_debt: "",
  monthly_obligations: "",
  credit_score: "",
  employment_status: "",
  years_employed: "",
  country: "",
  region: "",
  transaction_amount: "",
  transaction_type: "",
  purpose: "",
  requested_product_type: "",
  model_recommendation: "",
  model_confidence: "",
  evidence_completeness_score: "",
  supporting_evidence_text: "",
  agent_explanation: "",
};

function toSubmission(form: EvalForm): CaseSubmission {
  const requiredSelects = [
    form.employment_status,
    form.requested_product_type,
    form.transaction_type,
    form.model_recommendation,
  ];
  if (requiredSelects.some((v) => !v)) {
    throw new Error("Please fill employment status, product type, transaction type, and model recommendation.");
  }

  const num = (label: string, value: string) => {
    if (value.trim() === "") throw new Error(`Please enter ${label}.`);
    const n = Number(value);
    if (Number.isNaN(n)) throw new Error(`${label} must be a number.`);
    return n;
  };

  return {
    applicant_name: form.applicant_name.trim(),
    customer_id: form.customer_id.trim(),
    age: num("age", form.age),
    annual_income: num("annual income", form.annual_income),
    monthly_income: num("monthly income", form.monthly_income),
    loan_amount: num("loan amount", form.loan_amount),
    existing_debt: num("existing debt", form.existing_debt),
    monthly_obligations: num("monthly obligations", form.monthly_obligations),
    credit_score: num("credit score", form.credit_score),
    employment_status: form.employment_status,
    years_employed: num("years employed", form.years_employed),
    country: form.country.trim(),
    region: form.region.trim(),
    transaction_amount: num("transaction amount", form.transaction_amount),
    transaction_type: form.transaction_type,
    purpose: form.purpose.trim(),
    requested_product_type: form.requested_product_type,
    model_recommendation: form.model_recommendation as Decision,
    model_confidence: num("model confidence", form.model_confidence),
    evidence_completeness_score: num("evidence completeness", form.evidence_completeness_score),
    supporting_evidence_text: form.supporting_evidence_text.trim(),
    agent_explanation: form.agent_explanation.trim() || undefined,
    explanation_mode: "deterministic",
  };
}

function decisionVariant(decision: string | null | undefined) {
  if (decision === "APPROVE") return "success";
  if (decision === "REJECT") return "destructive";
  if (decision === "ESCALATE TO HUMAN REVIEW") return "warning";
  return "outline";
}

export default function EvaluationPage() {
  const [form, setForm] = useState<EvalForm>(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pipelineStages, setPipelineStages] = useState<PipelineStageState[]>(DEFAULT_STAGES);
  const [pipelineRunning, setPipelineRunning] = useState(false);

  function updateField<K extends keyof EvalForm>(field: K, value: EvalForm[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function runStreamEvaluation(id: string) {
    setPipelineRunning(true);
    setPipelineStages(DEFAULT_STAGES.map((s) => ({ ...s, status: "pending", message: undefined })));

    await new Promise<void>((resolve, reject) => {
      const source = new EventSource(evaluateCaseStreamUrl(id));

      source.onmessage = (event) => {
        let data: PipelineStreamEvent;
        try {
          data = JSON.parse(event.data) as PipelineStreamEvent;
        } catch {
          return;
        }

        if (data.type === "pipeline") {
          setPipelineStages(
            data.stages.map((s) => ({
              id: s.id,
              label: s.label,
              group: s.group === "llm" ? "llm" : "deterministic",
              status: "pending",
            })),
          );
          return;
        }

        if (data.type === "stage") {
          setPipelineStages((prev) =>
            prev.map((stage) =>
              stage.id === data.stage
                ? {
                    ...stage,
                    status: data.status,
                    message: data.message,
                    label: data.label || stage.label,
                  }
                : stage,
            ),
          );
          return;
        }

        if (data.type === "complete") {
          source.close();
          void getCase(id)
            .then((detail) => {
              setCaseDetail(detail);
              resolve();
            })
            .catch(reject);
          return;
        }

        if (data.type === "error") {
          source.close();
          reject(new Error(data.content));
        }
      };

      source.onerror = () => {
        source.close();
        reject(new Error("Pipeline stream disconnected before completion."));
      };
    });
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setCaseDetail(null);

    try {
      if (!form.applicant_name.trim() || !form.customer_id.trim()) {
        throw new Error("Please enter applicant name and customer ID.");
      }
      if (!form.supporting_evidence_text.trim()) {
        throw new Error("Please enter supporting evidence text.");
      }

      const payload = toSubmission(form);
      const created = await createCase(payload);
      setCaseId(created.case_id);
      await runStreamEvaluation(created.case_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run guardrail review.");
    } finally {
      setSubmitting(false);
      setPipelineRunning(false);
    }
  }

  const triggeredRules =
    caseDetail?.policy_results.filter((r) => r.triggered).map((r) => r.rule_name) ?? [];
  const govFlags = caseDetail?.governance_flags.map((f) => f.flag_name) ?? [];
  const llmUsed = (caseDetail?.llm_usage_logs?.length ?? 0) > 0;

  return (
    <AppShell>
      {/* Left form expands · right rail fixed to workflow width (420px) */}
      <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="min-w-0 space-y-5">
          <Card className="panel-gradient border-primary/20">
            <CardContent className="space-y-3 py-6">
              <Badge variant="outline">New evaluation intake</Badge>
              <h2 className="text-3xl font-semibold leading-tight tracking-tight">
                Submit a financial case
              </h2>
              <p className="max-w-3xl text-base text-muted-foreground">
                Fill from scratch. Submit runs the live workflow on the right, then shows deterministic + LLM outcomes below it.
              </p>
            </CardContent>
          </Card>

          <form className="space-y-5" onSubmit={(e) => void handleSubmit(e)}>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xl">Customer and affordability profile</CardTitle>
                <CardDescription className="text-sm">
                  Core applicant and credit information used by intake and risk engines.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Applicant name</span>
                  <Input className="h-11 text-base" value={form.applicant_name} onChange={(e) => updateField("applicant_name", e.target.value)} placeholder="e.g. Priya Mehta" />
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Customer ID</span>
                  <Input className="h-11 text-base" value={form.customer_id} onChange={(e) => updateField("customer_id", e.target.value)} placeholder="e.g. CUST-DEMO-101" />
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Age</span>
                  <Input className="h-11 text-base" type="number" value={form.age} onChange={(e) => updateField("age", e.target.value)} placeholder="34" />
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Credit score</span>
                  <Input className="h-11 text-base" type="number" value={form.credit_score} onChange={(e) => updateField("credit_score", e.target.value)} placeholder="300–850" />
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Annual income (£)</span>
                  <Input className="h-11 text-base" type="number" value={form.annual_income} onChange={(e) => updateField("annual_income", e.target.value)} placeholder="120000" />
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Monthly income (£)</span>
                  <Input className="h-11 text-base" type="number" value={form.monthly_income} onChange={(e) => updateField("monthly_income", e.target.value)} placeholder="10000" />
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Loan amount (£)</span>
                  <Input className="h-11 text-base" type="number" value={form.loan_amount} onChange={(e) => updateField("loan_amount", e.target.value)} placeholder="180000" />
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Existing debt (£)</span>
                  <Input className="h-11 text-base" type="number" value={form.existing_debt} onChange={(e) => updateField("existing_debt", e.target.value)} placeholder="400" />
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Monthly obligations (£)</span>
                  <Input className="h-11 text-base" type="number" value={form.monthly_obligations} onChange={(e) => updateField("monthly_obligations", e.target.value)} placeholder="1200" />
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Years employed</span>
                  <Input className="h-11 text-base" type="number" step="0.1" value={form.years_employed} onChange={(e) => updateField("years_employed", e.target.value)} placeholder="6" />
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Employment status</span>
                  <Select className="h-11 text-base" value={form.employment_status} onChange={(e) => updateField("employment_status", e.target.value)}>
                    <option value="">Select…</option>
                    {["Full Time", "Contract", "Self Employed", "Retired"].map((option) => (
                      <option key={option}>{option}</option>
                    ))}
                  </Select>
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Product type</span>
                  <Select className="h-11 text-base" value={form.requested_product_type} onChange={(e) => updateField("requested_product_type", e.target.value)}>
                    <option value="">Select…</option>
                    {["Residential Mortgage", "Personal Loan", "SME Working Capital", "Trade Finance", "Professional Loan", "Commercial Credit"].map(
                      (option) => (
                        <option key={option}>{option}</option>
                      ),
                    )}
                  </Select>
                </label>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xl">Transaction and model signal</CardTitle>
                <CardDescription className="text-sm">
                  Upstream model outputs that your guardrails will supervise.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Country</span>
                  <Input className="h-11 text-base" value={form.country} onChange={(e) => updateField("country", e.target.value)} placeholder="United Kingdom" />
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Region</span>
                  <Input className="h-11 text-base" value={form.region} onChange={(e) => updateField("region", e.target.value)} placeholder="London" />
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Transaction amount (£)</span>
                  <Input className="h-11 text-base" type="number" value={form.transaction_amount} onChange={(e) => updateField("transaction_amount", e.target.value)} placeholder="5000" />
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Transaction type</span>
                  <Select className="h-11 text-base" value={form.transaction_type} onChange={(e) => updateField("transaction_type", e.target.value)}>
                    <option value="">Select…</option>
                    {["Bank Transfer", "International Wire", "Cash Withdrawal", "Crypto Transfer"].map((option) => (
                      <option key={option}>{option}</option>
                    ))}
                  </Select>
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Purpose</span>
                  <Input className="h-11 text-base" value={form.purpose} onChange={(e) => updateField("purpose", e.target.value)} placeholder="Home purchase" />
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Model recommendation</span>
                  <Select
                    className="h-11 text-base"
                    value={form.model_recommendation}
                    onChange={(e) => updateField("model_recommendation", e.target.value as Decision | "")}
                  >
                    <option value="">Select…</option>
                    {["APPROVE", "REJECT", "ESCALATE TO HUMAN REVIEW"].map((option) => (
                      <option key={option}>{option}</option>
                    ))}
                  </Select>
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Model confidence (0–1)</span>
                  <Input className="h-11 text-base" type="number" step="0.01" min="0" max="1" value={form.model_confidence} onChange={(e) => updateField("model_confidence", e.target.value)} placeholder="0.88" />
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-muted-foreground">Evidence completeness (0–1)</span>
                  <Input className="h-11 text-base" type="number" step="0.01" min="0" max="1" value={form.evidence_completeness_score} onChange={(e) => updateField("evidence_completeness_score", e.target.value)} placeholder="0.90" />
                </label>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xl">Evidence and explainability input</CardTitle>
                <CardDescription className="text-sm">
                  Free-text evidence is reviewed by governance and stored in the audit trail.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea
                  className="min-h-[120px] text-base"
                  value={form.supporting_evidence_text}
                  onChange={(e) => updateField("supporting_evidence_text", e.target.value)}
                  placeholder="Supporting evidence text (required)"
                />
                <Textarea
                  className="min-h-[96px] text-base"
                  value={form.agent_explanation}
                  onChange={(e) => updateField("agent_explanation", e.target.value)}
                  placeholder="Optional upstream model explanation"
                />
                <Button type="submit" size="lg" className="h-12 w-full text-base" disabled={submitting}>
                  {submitting ? "Running guardrail review…" : "Run Guardrail Review"}
                </Button>
              </CardContent>
            </Card>
          </form>
        </div>

        <aside className="w-full space-y-4 xl:w-[420px] xl:justify-self-end xl:sticky xl:top-6 xl:self-start">
          <AgentPipelineProgress
            stages={pipelineStages}
            running={pipelineRunning || submitting}
            error={null}
            langsmithTraceUrl={caseDetail?.langsmith_trace_url}
            langsmithRunId={caseDetail?.langsmith_run_id}
            showRunButton={false}
            compact
          />

          <Card className="w-full">
            <CardHeader className="pb-2">
              <CardTitle>Evaluation outcome</CardTitle>
              <CardDescription>Deterministic decision + LLM enrichment.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {error ? (
                <div className="rounded-2xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                  {error}
                </div>
              ) : null}

              {caseDetail ? (
                <>
                  <div className="rounded-2xl border border-border/70 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="text-sm text-muted-foreground">Final decision</p>
                        <p className="mt-1 text-lg font-semibold leading-snug">{caseDetail.final_decision}</p>
                      </div>
                      <Badge variant={decisionVariant(caseDetail.final_decision)}>
                        {caseDetail.final_decision ?? "Pending"}
                      </Badge>
                    </div>
                    <div className="mt-3 space-y-2">
                      <div className="rounded-xl bg-secondary/60 p-3">
                        <p className="text-xs text-muted-foreground">Risk score</p>
                        <p className="mt-1 text-sm font-semibold">
                          {caseDetail.risk_score} ({caseDetail.risk_level})
                        </p>
                      </div>
                      <div className="rounded-xl bg-secondary/60 p-3">
                        <p className="text-xs text-muted-foreground">Policy version</p>
                        <p className="mt-1 text-sm font-semibold">{caseDetail.policy_version_used}</p>
                      </div>
                      <div className="rounded-xl bg-secondary/60 p-3">
                        <p className="text-xs text-muted-foreground">LLM agents</p>
                        <p className="mt-1 text-sm font-semibold">{llmUsed ? "Used" : "Skipped"}</p>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-border/70 p-4 space-y-2">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-success" />
                      <p className="text-sm font-semibold">Deterministic output</p>
                    </div>
                    <p className="text-sm leading-6 text-muted-foreground">
                      {caseDetail.deterministic_explanation || "No deterministic explanation recorded."}
                    </p>
                    <div className="space-y-1 text-xs text-muted-foreground">
                      <p>
                        <span className="font-semibold text-foreground">Triggered rules: </span>
                        {triggeredRules.length ? triggeredRules.join(", ") : "none"}
                      </p>
                      <p>
                        <span className="font-semibold text-foreground">Governance flags: </span>
                        {govFlags.length ? govFlags.join(", ") : "none"}
                      </p>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-primary/30 bg-primary/5 p-4 space-y-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">LLM</Badge>
                      <p className="text-sm font-semibold">LLM agent output</p>
                    </div>
                    {llmUsed ? (
                      <>
                        {caseDetail.worker_summary ? (
                          <div>
                            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                              Intake summary
                            </p>
                            <p className="mt-1 text-sm leading-6">{caseDetail.worker_summary}</p>
                          </div>
                        ) : null}
                        {caseDetail.llm_explanation ? (
                          <div>
                            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                              Decision explanation
                            </p>
                            <p className="mt-1 text-sm leading-6 text-muted-foreground">
                              {caseDetail.llm_explanation}
                            </p>
                          </div>
                        ) : null}
                        {caseDetail.risk_result?.llm_narrative ? (
                          <div>
                            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                              Risk narrative
                            </p>
                            <p className="mt-1 text-sm leading-6 text-muted-foreground">
                              {caseDetail.risk_result.llm_narrative}
                            </p>
                          </div>
                        ) : null}
                        <p className="text-xs text-muted-foreground">
                          Tokens used:{" "}
                          {caseDetail.llm_usage_logs
                            .reduce((sum, log) => sum + log.total_tokens, 0)
                            .toLocaleString()}
                        </p>
                      </>
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        LLM agents did not run. Deterministic result still stands.
                      </p>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-3">
                    {caseId ? (
                      <Link
                        href={`/cases/${caseId}`}
                        className="inline-flex items-center gap-2 text-sm font-semibold text-primary"
                      >
                        Open case detail
                        <ArrowRight className="h-4 w-4" />
                      </Link>
                    ) : null}
                    {caseDetail.langsmith_trace_url ? (
                      <a
                        href={caseDetail.langsmith_trace_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={cn(buttonVariants({ variant: "secondary", size: "sm" }), "gap-2")}
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                        LangSmith
                      </a>
                    ) : null}
                  </div>
                </>
              ) : (
                <div className="rounded-2xl border border-dashed border-border/70 p-6 text-sm text-muted-foreground">
                  {submitting
                    ? "Pipeline is running — watch the workflow above."
                    : "Submit a case to see deterministic + LLM outcomes here."}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="w-full">
            <CardContent className="flex items-start gap-3 py-5">
              <div className="rounded-2xl bg-warning/15 p-3 text-warning">
                <Shield className="h-5 w-5" />
              </div>
              <div>
                <p className="font-semibold">Governance note</p>
                <p className="mt-1.5 text-sm text-muted-foreground">
                  Deterministic engines decide. LLM agents explain — they cannot override policy.
                </p>
              </div>
            </CardContent>
          </Card>
        </aside>
      </div>
    </AppShell>
  );
}
