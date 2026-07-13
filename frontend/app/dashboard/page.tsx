"use client";

import { Activity, AlertTriangle, CheckCircle2, Clock3, Scale, ShieldAlert, TrendingUp, XCircle } from "lucide-react";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { ActivityChart } from "@/components/dashboard/activity-chart";
import { AuditLogTable } from "@/components/dashboard/audit-log-table";
import { DecisionDistributionChart } from "@/components/dashboard/decision-distribution-chart";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { RiskHistogramChart } from "@/components/dashboard/risk-histogram-chart";
import { RuleViolationsChart } from "@/components/dashboard/rule-violations-chart";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getDashboardCharts, getDashboardSummary } from "@/lib/api";
import type { DashboardCharts, DashboardSummary } from "@/lib/types";

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [charts, setCharts] = useState<DashboardCharts | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [summaryData, chartsData] = await Promise.all([getDashboardSummary(), getDashboardCharts()]);
        setSummary(summaryData);
        setCharts(chartsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load dashboard data.");
      }
    }

    void load();
  }, []);

  return (
    <AppShell>
      <div className="space-y-6">
        <section className="grid gap-5 xl:grid-cols-[1.3fr_0.7fr]">
          <Card className="panel-gradient border-primary/20">
            <CardContent className="space-y-3 p-6">
              <Badge variant="primary">Command Center</Badge>
              <h2 className="text-2xl font-bold tracking-tight">Guardrail Operating Dashboard</h2>
              <p className="text-sm text-muted-foreground leading-relaxed max-w-xl">
                Monitor evaluated cases, policy effectiveness, human review queue load, and system metrics across the AI governance pipeline.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="p-5 pb-0">
              <CardTitle className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Governance Fabric</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2 p-5">
              {summary ? (
                <>
                  <div className="rounded-lg border border-border bg-secondary/20 p-3">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Volume</p>
                    <p className="mt-1 text-sm font-bold">{summary.system_health.total_cases} cases</p>
                  </div>
                  <div className="rounded-lg border border-border bg-secondary/20 p-3">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Reviews</p>
                    <p className="mt-1 text-sm font-bold">{summary.system_health.pending_reviews} pending</p>
                  </div>
                  <div className="rounded-lg border border-border bg-secondary/20 p-3">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Interventions</p>
                    <p className="mt-1 text-sm font-bold">{summary.system_health.fairness_flags} flags</p>
                  </div>
                  <div className="rounded-lg border border-success/20 bg-success/5 p-3">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-success">Approval Rate</p>
                    <p className="mt-1 text-sm font-bold text-success">{summary.system_health.approval_rate}</p>
                  </div>
                </>
              ) : (
                <>
                  <Skeleton className="h-12 rounded-lg" />
                  <Skeleton className="h-12 rounded-lg" />
                  <Skeleton className="h-12 rounded-lg" />
                  <Skeleton className="h-12 rounded-lg" />
                </>
              )}
            </CardContent>
          </Card>
        </section>

        {error ? <Card><CardContent className="p-4 text-destructive">{error}</CardContent></Card> : null}

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {summary ? (
            <>
              <KpiCard title="Total cases" value={summary.total_cases.toString()} description="Evaluated portfolio volume" icon={Activity} />
              <KpiCard title="Approved" value={summary.approved.toString()} description="Guardrailed approvals" icon={CheckCircle2} />
              <KpiCard title="Rejected" value={summary.rejected.toString()} description="Deterministic blocks" icon={XCircle} />
              <KpiCard title="Escalated" value={summary.escalated.toString()} description="Human review overrides" icon={AlertTriangle} />
              <KpiCard
                title="Average risk score"
                value={summary.average_risk_score.toFixed(1)}
                description="Portfolio risk centerline"
                icon={TrendingUp}
              />
              <KpiCard
                title="Average confidence"
                value={`${(summary.average_confidence * 100).toFixed(1)}%`}
                description="Evidence confidence blend"
                icon={Scale}
              />
              <KpiCard
                title="Fairness flags"
                value={summary.fairness_flags_count.toString()}
                description="Governance flags raised"
                icon={ShieldAlert}
              />
              <KpiCard
                title="Pending review"
                value={summary.pending_human_review_count.toString()}
                description="Open review items"
                icon={Clock3}
              />
            </>
          ) : (
            Array.from({ length: 8 }).map((_, index) => <Skeleton key={index} className="h-28 rounded-lg" />)
          )}
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          {charts ? <DecisionDistributionChart data={charts.decision_distribution} /> : <Skeleton className="h-[430px] rounded-2xl" />}
          {charts ? <RiskHistogramChart data={charts.risk_histogram} /> : <Skeleton className="h-[430px] rounded-2xl" />}
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          {charts ? <RuleViolationsChart data={charts.rule_violations} /> : <Skeleton className="h-[430px] rounded-2xl" />}
          {charts ? <ActivityChart data={charts.activity_over_time} /> : <Skeleton className="h-[430px] rounded-2xl" />}
        </section>

        <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
          {summary ? <RecentActivity items={summary.recent_activity} /> : <Skeleton className="h-[520px] rounded-2xl" />}
          {summary ? <AuditLogTable rows={summary.recent_audit_logs} /> : <Skeleton className="h-[520px] rounded-2xl" />}
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Top policy rule violations</CardTitle>
              <CardDescription>Most active sources of control friction.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {summary?.top_policy_rule_violations.map((item) => (
                <div key={item.rule_name} className="flex items-center justify-between rounded-2xl border border-border/70 p-4">
                  <div>
                    <p className="font-medium">{item.rule_name}</p>
                    <p className="text-sm text-muted-foreground">Triggered policy control</p>
                  </div>
                  <Badge variant="warning">{item.count}</Badge>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Review queue status</CardTitle>
              <CardDescription>Human review backlog and completed interventions.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              {charts?.review_queue_stats.map((item) => (
                <div key={item.status} className="rounded-2xl border border-border/70 p-5">
                  <p className="text-sm capitalize text-muted-foreground">{item.status}</p>
                  <p className="mt-3 text-3xl font-semibold">{item.count}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </section>
      </div>
    </AppShell>
  );
}

