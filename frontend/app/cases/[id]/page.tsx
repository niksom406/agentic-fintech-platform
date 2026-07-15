"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Download, ExternalLink, FileText, ShieldCheck, UserRoundCheck } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { AgentPipelineProgress, DEFAULT_STAGES } from "@/components/cases/agent-pipeline-progress";
import { CaseHistoryTimeline } from "@/components/cases/case-history-timeline";
import { ExplainabilityPanel } from "@/components/cases/explainability-panel";
import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { auditExportUrl, evaluateCaseStreamUrl, getCase } from "@/lib/api";
import type { CaseDetail, PipelineStageState, PipelineStreamEvent } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

function decisionVariant(decision: string | null | undefined) {
  if (decision === "APPROVE") return "success";
  if (decision === "REJECT") return "destructive";
  if (decision === "ESCALATE TO HUMAN REVIEW") return "warning";
  return "outline";
}

function stagesFromCase(detail: CaseDetail): PipelineStageState[] {
  const evaluated = Boolean(detail.evaluated_at);
  const llmUsed = (detail.llm_usage_logs?.length ?? 0) > 0;

  return DEFAULT_STAGES.map((stage) => {
    if (!evaluated) {
      return { ...stage, status: "pending" as const };
    }
    if (stage.group === "deterministic") {
      return { ...stage, status: "done" as const, message: "Completed" };
    }
    if (llmUsed) {
      const agentName = stage.id.replace("llm_", "") + "_agent";
      const log = detail.llm_usage_logs?.find((l) => l.agent_name === agentName);
      return {
        ...stage,
        status: "done" as const,
        message: log ? `${log.total_tokens.toLocaleString()} tokens · ${log.latency_ms}ms` : "Completed",
      };
    }
    return { ...stage, status: "skipped" as const, message: "LLM agents not used" };
  });
}

export default function CaseDetailPage() {
  const params = useParams<{ id: string }>();
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pipelineStages, setPipelineStages] = useState<PipelineStageState[]>(DEFAULT_STAGES);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);

  const loadCase = useCallback(async () => {
    const detail = await getCase(params.id);
    setCaseDetail(detail);
    setPipelineStages(stagesFromCase(detail));
    return detail;
  }, [params.id]);

  useEffect(() => {
    async function load() {
      try {
        await loadCase();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load case detail.");
      }
    }

    if (params.id) {
      void load();
    }
  }, [params.id, loadCase]);

  async function runLiveEvaluation() {
    if (!params.id || pipelineRunning) return;
    setPipelineRunning(true);
    setPipelineError(null);
    setPipelineStages(DEFAULT_STAGES.map((s) => ({ ...s, status: "pending", message: undefined })));

    try {
      await new Promise<void>((resolve, reject) => {
        const source = new EventSource(evaluateCaseStreamUrl(params.id));

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
                  ? { ...stage, status: data.status, message: data.message, label: data.label || stage.label }
                  : stage,
              ),
            );
            return;
          }

          if (data.type === "complete") {
            source.close();
            void loadCase()
              .then(() => resolve())
              .catch((err) => reject(err));
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
    } catch (err) {
      setPipelineError(err instanceof Error ? err.message : "Evaluation failed.");
    } finally {
      setPipelineRunning(false);
    }
  }

  const latestReview = (caseDetail?.human_reviews || []).find((review) => review.review_status === "completed");
  const sortedAuditLogs = caseDetail ? [...caseDetail.audit_logs].sort((a, b) => a.created_at.localeCompare(b.created_at)) : [];
  const sortedPolicyResults = caseDetail
    ? [...caseDetail.policy_results].sort((a, b) => Number(b.triggered) - Number(a.triggered) || a.rule_name.localeCompare(b.rule_name))
    : [];

  const hasTrace = Boolean(caseDetail?.langsmith_trace_url);

  return (
    <AppShell>
      {!caseDetail && !error ? (
        <div className="space-y-6">
          <Skeleton className="h-52 rounded-2xl" />
          <Skeleton className="h-[600px] rounded-2xl" />
        </div>
      ) : null}

      {error ? <EmptyState title="Unable to load case" description={error} /> : null}

      {caseDetail ? (
        <div className="space-y-6">
          <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
            <Card className="panel-gradient border-primary/20">
              <CardContent className="space-y-4">
                <div className="flex flex-wrap items-center gap-3">
                  <Badge variant="outline">{caseDetail.case_id}</Badge>
                  <Badge variant={decisionVariant(caseDetail.final_decision)}>{caseDetail.final_decision ?? "Pending"}</Badge>
                  <Badge variant="outline">{caseDetail.policy_version_used ?? "No policy"}</Badge>
                  {hasTrace ? <Badge variant="success">LangSmith traced</Badge> : null}
                </div>
                <h2 className="text-3xl font-semibold">{caseDetail.customer_name}</h2>
                <p className="text-muted-foreground">{caseDetail.worker_summary}</p>
                <div className="grid gap-3 md:grid-cols-3">
                  <div className="rounded-2xl bg-secondary/60 p-4">
                    <p className="text-sm text-muted-foreground">Risk score</p>
                    <p className="mt-2 text-xl font-semibold">{caseDetail.risk_score}</p>
                  </div>
                  <div className="rounded-2xl bg-secondary/60 p-4">
                    <p className="text-sm text-muted-foreground">Risk level</p>
                    <p className="mt-2 text-xl font-semibold">{caseDetail.risk_level}</p>
                  </div>
                  <div className="rounded-2xl bg-secondary/60 p-4">
                    <p className="text-sm text-muted-foreground">Confidence</p>
                    <p className="mt-2 text-xl font-semibold">
                      {caseDetail.overall_confidence != null
                        ? `${(caseDetail.overall_confidence * 100).toFixed(1)}%`
                        : "—"}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Case metadata</CardTitle>
                <CardDescription>Timestamp, policy, observability, and audit export controls.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-border/70 p-4">
                    <p className="text-sm text-muted-foreground">Created</p>
                    <p className="mt-2 font-semibold">{formatDate(caseDetail.created_at)}</p>
                  </div>
                  <div className="rounded-2xl border border-border/70 p-4">
                    <p className="text-sm text-muted-foreground">Evaluated</p>
                    <p className="mt-2 font-semibold">{formatDate(caseDetail.evaluated_at)}</p>
                  </div>
                  <div className="rounded-2xl border border-border/70 p-4">
                    <p className="text-sm text-muted-foreground">Governance status</p>
                    <p className="mt-2 font-semibold">{caseDetail.governance_status}</p>
                  </div>
                  <div className="rounded-2xl border border-border/70 p-4">
                    <p className="text-sm text-muted-foreground">Fairness flags</p>
                    <p className="mt-2 font-semibold">{caseDetail.fairness_flag_count}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-3">
                  <Link href={auditExportUrl(caseDetail.case_id, "json")} className={cn(buttonVariants({ variant: "secondary" }), "gap-2")}>
                    <Download className="h-4 w-4" />
                    JSON audit
                  </Link>
                  <Link href={auditExportUrl(caseDetail.case_id, "txt")} className={cn(buttonVariants({ variant: "secondary" }), "gap-2")}>
                    <FileText className="h-4 w-4" />
                    TXT audit
                  </Link>
                  {caseDetail.langsmith_trace_url ? (
                    <a
                      href={caseDetail.langsmith_trace_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={cn(buttonVariants({ variant: "outline" }), "gap-2")}
                    >
                      <ExternalLink className="h-4 w-4" />
                      LangSmith
                    </a>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          </section>

          <AgentPipelineProgress
            stages={pipelineStages}
            running={pipelineRunning}
            error={pipelineError}
            langsmithTraceUrl={caseDetail.langsmith_trace_url}
            langsmithRunId={caseDetail.langsmith_run_id}
            onRun={() => void runLiveEvaluation()}
          />

          <ExplainabilityPanel caseDetail={caseDetail} />

          <section className="grid gap-6 xl:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Original input payload</CardTitle>
                <CardDescription>Raw and normalized case intake used by the platform.</CardDescription>
              </CardHeader>
              <CardContent>
                <pre className="overflow-x-auto rounded-2xl bg-secondary/60 p-4 text-xs leading-6">
                  {JSON.stringify(caseDetail.case_input?.normalized_payload, null, 2)}
                </pre>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Derived intake fields</CardTitle>
                <CardDescription>Normalized ratios and derived metrics computed during intake.</CardDescription>
              </CardHeader>
              <CardContent>
                <pre className="overflow-x-auto rounded-2xl bg-secondary/60 p-4 text-xs leading-6">
                  {JSON.stringify(caseDetail.case_input?.derived_fields, null, 2)}
                </pre>
              </CardContent>
            </Card>
          </section>

          <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
            <Card>
              <CardHeader>
                <CardTitle>Policy rule results</CardTitle>
                <CardDescription>Deterministic rule outcomes recorded under the active policy version.</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Rule</TableHead>
                      <TableHead>Severity</TableHead>
                      <TableHead>Outcome</TableHead>
                      <TableHead>Threshold</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sortedPolicyResults.map((result) => (
                      <TableRow key={result.rule_name}>
                        <TableCell>
                          <p className="font-semibold">{result.rule_name}</p>
                          <p className="text-xs text-muted-foreground">{result.description}</p>
                        </TableCell>
                        <TableCell>
                          <Badge variant={result.severity === "critical" ? "destructive" : result.severity === "medium" ? "warning" : "outline"}>
                            {result.severity}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={result.outcome === "REJECT" ? "destructive" : result.outcome === "ESCALATE" ? "warning" : "success"}>
                            {result.outcome}
                          </Badge>
                        </TableCell>
                        <TableCell>{result.threshold}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Risk score breakdown</CardTitle>
                <CardDescription>Component-level scores feeding the overall risk assessment.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {(caseDetail.top_risk_factors || []).map((component) => (
                  <div key={component.name}>
                    <div className="mb-2 flex items-center justify-between text-sm">
                      <span>{component.name}</span>
                      <span>{component.score}</span>
                    </div>
                    <Progress value={component.score} />
                    <p className="mt-2 text-xs text-muted-foreground">{component.reason}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          </section>

          <section className="grid gap-6 xl:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Fairness and governance findings</CardTitle>
                <CardDescription>Governance interventions and fairness-sensitive routing findings.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {caseDetail.governance_flags.length ? (
                  caseDetail.governance_flags.map((flag) => (
                    <div key={flag.flag_name} className="rounded-2xl border border-border/70 p-4 space-y-3">
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2 flex-wrap">
                          <Badge variant={flag.requires_human_review ? "warning" : "outline"}>{flag.flag_name}</Badge>
                          <Badge variant="outline">{flag.category}</Badge>
                          <Badge variant={flag.severity === "high" ? "destructive" : flag.severity === "medium" ? "warning" : "outline"}>{flag.severity}</Badge>
                        </div>
                        {flag.requires_human_review && (
                          <Badge variant="warning" className="text-[10px] shrink-0">Needs human review</Badge>
                        )}
                      </div>
                      {flag.llm_reasoning && (
                        <p className="text-sm text-muted-foreground">{flag.llm_reasoning}</p>
                      )}
                      {flag.rag_source && (
                        <div className="rounded-xl border border-border/60 bg-secondary/40 px-3 py-2 text-xs text-muted-foreground">
                          <span className="font-semibold text-foreground">RAG source: </span>
                          {flag.rag_source}
                        </div>
                      )}
                      {Object.keys(flag.context).length > 0 && (
                        <pre className="overflow-x-auto rounded-xl bg-secondary/60 p-3 text-xs leading-6">
                          {JSON.stringify(flag.context, null, 2)}
                        </pre>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="rounded-2xl border border-dashed border-border/70 p-6 text-sm text-muted-foreground">
                    No governance flags were triggered for this case.
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Human review output</CardTitle>
                <CardDescription>Reviewer note, override reason, and completion metadata.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-2xl border border-border/70 p-4">
                  <div className="flex items-center gap-3">
                    <div className="rounded-2xl bg-primary/10 p-3 text-primary">
                      <UserRoundCheck className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="font-semibold">{latestReview?.reviewer_name ?? "No completed review yet"}</p>
                      <p className="text-sm text-muted-foreground">{latestReview?.final_decision ?? caseDetail.case_status}</p>
                    </div>
                  </div>
                  <Separator />
                  <div className="space-y-3 pt-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Reviewer note</p>
                      <p className="mt-1 text-sm">{caseDetail.reviewer_note ?? latestReview?.reviewer_note ?? "No reviewer note recorded."}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Override reason</p>
                      <p className="mt-1 text-sm">{caseDetail.override_reason ?? latestReview?.override_reason ?? "No override applied."}</p>
                    </div>
                  </div>
                </div>

                <div className="rounded-2xl border border-border/70 p-4">
                  <div className="flex items-center gap-3">
                    <div className="rounded-2xl bg-success/15 p-3 text-success">
                      <ShieldCheck className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="font-semibold">Policy version used</p>
                      <p className="text-sm text-muted-foreground">{caseDetail.policy_version_used}</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </section>

          <CaseHistoryTimeline events={sortedAuditLogs} />

          {/* LLM Usage Logs */}
          {caseDetail.llm_usage_logs && caseDetail.llm_usage_logs.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>LLM agent usage logs</CardTitle>
                <CardDescription>Token consumption, latency, and estimated cost per agent run in this case.</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Agent</TableHead>
                      <TableHead>Model</TableHead>
                      <TableHead>Provider</TableHead>
                      <TableHead className="text-right">Prompt tokens</TableHead>
                      <TableHead className="text-right">Completion</TableHead>
                      <TableHead className="text-right">Total tokens</TableHead>
                      <TableHead className="text-right">Cost (USD)</TableHead>
                      <TableHead className="text-right">Latency</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {caseDetail.llm_usage_logs.map((log, i) => (
                      <TableRow key={i}>
                        <TableCell className="font-semibold">{log.agent_name}</TableCell>
                        <TableCell>{log.model}</TableCell>
                        <TableCell>{log.provider}</TableCell>
                        <TableCell className="text-right tabular-nums">{log.prompt_tokens.toLocaleString()}</TableCell>
                        <TableCell className="text-right tabular-nums">{log.completion_tokens.toLocaleString()}</TableCell>
                        <TableCell className="text-right tabular-nums font-semibold">{log.total_tokens.toLocaleString()}</TableCell>
                        <TableCell className="text-right tabular-nums">${log.estimated_cost_usd.toFixed(5)}</TableCell>
                        <TableCell className="text-right tabular-nums">{log.latency_ms}ms</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                <div className="mt-4 flex gap-6 rounded-xl border border-border/50 bg-secondary/30 px-4 py-3 text-sm">
                  <span className="text-muted-foreground">Total tokens:</span>
                  <span className="font-semibold tabular-nums">
                    {caseDetail.llm_usage_logs.reduce((s, l) => s + l.total_tokens, 0).toLocaleString()}
                  </span>
                  <span className="ml-auto text-muted-foreground">Total cost:</span>
                  <span className="font-semibold tabular-nums">
                    ${caseDetail.llm_usage_logs.reduce((s, l) => s + l.estimated_cost_usd, 0).toFixed(5)}
                  </span>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      ) : null}
    </AppShell>
  );
}
