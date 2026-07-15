"use client";

import {
  ArrowDown,
  ArrowRight,
  CheckCircle2,
  Circle,
  ExternalLink,
  Loader2,
  Play,
  SkipForward,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { PipelineStageState, PipelineStageStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const DEFAULT_STAGES: PipelineStageState[] = [
  { id: "policy", label: "Policy Engine", group: "deterministic", status: "pending" },
  { id: "risk", label: "Risk Engine", group: "deterministic", status: "pending" },
  { id: "governance", label: "Governance Engine", group: "deterministic", status: "pending" },
  { id: "decision", label: "Decision Engine", group: "deterministic", status: "pending" },
  { id: "llm_intake", label: "Intake Agent", group: "llm", status: "pending" },
  { id: "llm_risk", label: "Risk Agent", group: "llm", status: "pending" },
  { id: "llm_governance", label: "Governance Agent", group: "llm", status: "pending" },
  { id: "llm_decision", label: "Decision Agent", group: "llm", status: "pending" },
  { id: "llm_audit", label: "Audit Agent", group: "llm", status: "pending" },
];

const SHORT_LABELS: Record<string, string> = {
  policy: "Policy",
  risk: "Risk",
  governance: "Governance",
  decision: "Decision",
  llm_intake: "Intake",
  llm_risk: "Risk",
  llm_governance: "Governance",
  llm_decision: "Decision",
  llm_audit: "Audit",
};

function edgeTone(left?: PipelineStageStatus, right?: PipelineStageStatus) {
  if (left === "done" || left === "skipped") {
    if (right === "running") return "active";
    if (right === "done" || right === "skipped") return "complete";
  }
  if (left === "running") return "active";
  return "idle";
}

function WorkflowEdge({
  tone,
  orientation = "horizontal",
}: {
  tone: "idle" | "active" | "complete";
  orientation?: "horizontal" | "vertical";
}) {
  const lineClass = cn(
    "transition-colors duration-300",
    tone === "complete" && "bg-success/70",
    tone === "active" && "bg-primary animate-pulse",
    tone === "idle" && "bg-border",
  );

  if (orientation === "vertical") {
    return (
      <div className="flex flex-col items-center gap-1 py-0.5">
        <div className={cn("h-4 w-0.5 rounded-full", lineClass)} />
        <ArrowDown
          className={cn(
            "h-3.5 w-3.5",
            tone === "complete" && "text-success",
            tone === "active" && "text-primary",
            tone === "idle" && "text-muted-foreground/50",
          )}
        />
        <div className={cn("h-4 w-0.5 rounded-full", lineClass)} />
      </div>
    );
  }

  return (
    <div className="flex min-w-[20px] items-center gap-1 px-0.5">
      <div className={cn("h-0.5 w-3 rounded-full sm:w-4", lineClass)} />
      <ArrowRight
        className={cn(
          "h-3 w-3 shrink-0",
          tone === "complete" && "text-success",
          tone === "active" && "text-primary",
          tone === "idle" && "text-muted-foreground/50",
        )}
      />
      <div className={cn("h-0.5 w-3 rounded-full sm:w-4", lineClass)} />
    </div>
  );
}

function WorkflowNode({
  stage,
  index,
}: {
  stage: PipelineStageState;
  index: number;
}) {
  const short = SHORT_LABELS[stage.id] ?? stage.label;

  return (
    <div
      className={cn(
        "relative flex w-[96px] shrink-0 flex-col items-center text-center",
        stage.status === "running" && "z-10",
      )}
    >
      {stage.status === "running" ? (
        <span className="pointer-events-none absolute top-4 h-10 w-10 animate-ping rounded-full bg-primary/20" />
      ) : null}

      <div
        className={cn(
          "relative flex h-10 w-10 items-center justify-center rounded-2xl border-2 shadow-sm transition-all duration-300",
          stage.status === "running" && "border-primary bg-primary/15 text-primary shadow-primary/20",
          stage.status === "done" && "border-success/60 bg-success/15 text-success",
          stage.status === "error" && "border-destructive/60 bg-destructive/15 text-destructive",
          stage.status === "pending" && "border-border bg-card text-muted-foreground",
          stage.status === "skipped" && "border-border/50 bg-secondary/40 text-muted-foreground opacity-70",
        )}
      >
        {stage.status === "running" ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
        {stage.status === "done" ? <CheckCircle2 className="h-4 w-4" /> : null}
        {stage.status === "error" ? <XCircle className="h-4 w-4" /> : null}
        {stage.status === "skipped" ? <SkipForward className="h-4 w-4" /> : null}
        {stage.status === "pending" ? (
          <span className="text-xs font-semibold tabular-nums">{index}</span>
        ) : null}
      </div>

      <p className="mt-2 text-xs font-semibold leading-tight tracking-tight">{short}</p>
      <p className="mt-0.5 line-clamp-2 max-w-[100px] text-[10px] leading-snug text-muted-foreground">
        {stage.message
          ? stage.message
          : stage.status === "running"
            ? "Running…"
            : stage.status === "pending"
              ? "Waiting"
              : stage.status === "skipped"
                ? "Skipped"
                : "Done"}
      </p>
    </div>
  );
}

function VerticalColumn({
  title,
  badge,
  stages,
  startIndex,
}: {
  title: string;
  badge: string;
  stages: PipelineStageState[];
  startIndex: number;
}) {
  return (
    <div className="flex w-[120px] shrink-0 flex-col rounded-2xl border border-border/60 bg-secondary/20 p-2.5">
      <div className="mb-2.5 flex flex-col items-center gap-1 text-center">
        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">{title}</p>
        <Badge variant="outline" className="text-[9px] px-1.5 py-0">
          {badge}
        </Badge>
      </div>
      <div className="flex flex-col items-center">
        {stages.map((stage, i) => (
          <div key={stage.id} className="flex flex-col items-center">
            <WorkflowNode stage={stage} index={startIndex + i} />
            {i < stages.length - 1 ? (
              <WorkflowEdge
                orientation="vertical"
                tone={edgeTone(stage.status, stages[i + 1]?.status)}
              />
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

export function AgentPipelineProgress({
  stages = DEFAULT_STAGES,
  running,
  error,
  langsmithTraceUrl,
  langsmithRunId,
  onRun,
  showRunButton = true,
  compact = false,
}: {
  stages?: PipelineStageState[];
  running?: boolean;
  error?: string | null;
  langsmithTraceUrl?: string | null;
  langsmithRunId?: string | null;
  onRun?: () => void;
  showRunButton?: boolean;
  compact?: boolean;
}) {
  const deterministic = stages.filter((s) => s.group === "deterministic");
  const llm = stages.filter((s) => s.group === "llm");
  const doneCount = stages.filter((s) => s.status === "done" || s.status === "skipped").length;
  const activeStage = stages.find((s) => s.status === "running");

  const bridgeTone = edgeTone(
    deterministic[deterministic.length - 1]?.status,
    llm[0]?.status,
  );

  return (
    <Card className={cn(compact ? "w-full" : "mx-auto w-full max-w-[420px]")}>
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3 space-y-0 pb-3">
        <div>
          <CardTitle>Agent workflow</CardTitle>
          <CardDescription>
            Vertical guardrails → horizontal handoff → vertical LLM agents.
          </CardDescription>
          {activeStage ? (
            <p className="mt-2 text-xs font-medium text-primary">
              Currently executing: {activeStage.label}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline">
            {doneCount}/{stages.length} nodes
          </Badge>
          {showRunButton && onRun ? (
            <Button onClick={onRun} disabled={running} size="sm">
              {running ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Running…
                </>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5" />
                  Run evaluation
                </>
              )}
            </Button>
          ) : null}
          {langsmithTraceUrl ? (
            <a
              href={langsmithTraceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(buttonVariants({ variant: "secondary", size: "sm" }), "gap-2")}
            >
              <ExternalLink className="h-3.5 w-3.5" />
              LangSmith
            </a>
          ) : null}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {error ? (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        ) : null}
        {langsmithRunId && !langsmithTraceUrl ? (
          <p className="text-xs text-muted-foreground">LangSmith run id: {langsmithRunId}</p>
        ) : null}

        {/* Side-by-side vertical flows + horizontal handoff */}
        <div className="flex flex-col items-center justify-center gap-2 sm:flex-row sm:items-center">
          <VerticalColumn
            title="Phase 1"
            badge="Deterministic"
            stages={deterministic}
            startIndex={1}
          />

          {/* Horizontal handoff between the two columns */}
          <div className="flex shrink-0 flex-row items-center justify-center gap-2 py-1 sm:flex-col sm:px-0.5">
            <div className="flex items-center sm:hidden">
              <WorkflowEdge orientation="vertical" tone={bridgeTone} />
            </div>
            <div className="hidden sm:flex sm:flex-col sm:items-center sm:gap-1.5">
              <WorkflowEdge tone={bridgeTone} />
              <div
                className={cn(
                  "rounded-full border px-2 py-0.5 text-center text-[9px] font-semibold uppercase tracking-[0.12em]",
                  bridgeTone === "complete" && "border-success/40 bg-success/10 text-success",
                  bridgeTone === "active" && "border-primary/40 bg-primary/10 text-primary",
                  bridgeTone === "idle" && "border-border bg-secondary/50 text-muted-foreground",
                )}
              >
                handoff
              </div>
              <WorkflowEdge tone={bridgeTone} />
            </div>
            <div
              className={cn(
                "rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] sm:hidden",
                bridgeTone === "complete" && "border-success/40 bg-success/10 text-success",
                bridgeTone === "active" && "border-primary/40 bg-primary/10 text-primary",
                bridgeTone === "idle" && "border-border bg-secondary/50 text-muted-foreground",
              )}
            >
              handoff → LLM
            </div>
          </div>

          <VerticalColumn
            title="Phase 2"
            badge="LLM agents"
            stages={llm}
            startIndex={deterministic.length + 1}
          />
        </div>

        <div className="flex flex-wrap items-center justify-center gap-3 border-t border-border/50 pt-3 text-[11px] text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Circle className="h-3 w-3" /> Pending
          </span>
          <span className="flex items-center gap-1.5 text-primary">
            <Loader2 className="h-3 w-3" /> Running
          </span>
          <span className="flex items-center gap-1.5 text-success">
            <CheckCircle2 className="h-3 w-3" /> Done
          </span>
          <span className="flex items-center gap-1.5">
            <SkipForward className="h-3 w-3" /> Skipped
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

export { DEFAULT_STAGES };
