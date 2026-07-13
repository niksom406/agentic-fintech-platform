"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  CircleDot,
  Filter,
  Layers,
  Loader2,
  Search,
  XCircle,
} from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getCases } from "@/lib/api";
import type { CaseListItem } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

// ─── helpers ──────────────────────────────────────────────────────────────────

function decisionVariant(d: string | null) {
  if (d === "APPROVE") return "success";
  if (d === "REJECT") return "destructive";
  if (d === "ESCALATE TO HUMAN REVIEW") return "warning";
  return "outline";
}

function riskVariant(r: string | null) {
  if (r === "Critical") return "destructive";
  if (r === "High") return "warning";
  if (r === "Medium") return "outline";
  return "outline";
}

function DecisionIcon({ decision }: { decision: string | null }) {
  if (decision === "APPROVE")
    return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
  if (decision === "REJECT")
    return <XCircle className="h-4 w-4 text-red-400" />;
  if (decision === "ESCALATE TO HUMAN REVIEW")
    return <AlertTriangle className="h-4 w-4 text-amber-400" />;
  return <CircleDot className="h-4 w-4 text-muted-foreground" />;
}

// ─── main page ────────────────────────────────────────────────────────────────

export default function CasesPage() {
  const [cases, setCases] = useState<CaseListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // filters
  const [search, setSearch] = useState("");
  const [decision, setDecision] = useState("");
  const [riskLevel, setRiskLevel] = useState("");
  const [escalated, setEscalated] = useState<"" | "true" | "false">("");

  async function load() {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (search) params.search = search;
      if (decision) params.decision = decision;
      if (riskLevel) params.risk_level = riskLevel;
      if (escalated) params.escalated = escalated;
      const data = await getCases(params);
      setCases(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }

  // debounced search
  useEffect(() => {
    const t = setTimeout(() => void load(), 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, decision, riskLevel, escalated]);

  const hasFilters = !!search || !!decision || !!riskLevel || !!escalated;

  function clearFilters() {
    setSearch("");
    setDecision("");
    setRiskLevel("");
    setEscalated("");
  }

  // ─── stats ────────────────────────────────────────────────────────────────

  const approvedCount = cases.filter((c) => c.final_decision === "APPROVE").length;
  const rejectedCount = cases.filter((c) => c.final_decision === "REJECT").length;
  const escalatedCount = cases.filter((c) => c.final_decision === "ESCALATE TO HUMAN REVIEW").length;
  const highRiskCount = cases.filter((c) => c.risk_level === "High" || c.risk_level === "Critical").length;

  return (
    <AppShell>
      {/* Header */}
      <Card className="panel-gradient border-primary/20">
        <CardContent className="space-y-4 pt-6">
          <Badge variant="outline">
            <Layers className="mr-1.5 h-3 w-3" />
            Case pipeline
          </Badge>
          <h2 className="text-3xl font-semibold">All cases</h2>
          <p className="text-muted-foreground">
            Browse, filter, and inspect every financial case that has passed through the governance pipeline.
          </p>
        </CardContent>
      </Card>

      {/* Stat strip */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          { label: "Total cases", value: total, color: "text-foreground" },
          { label: "Approved", value: approvedCount, color: "text-emerald-400" },
          { label: "Rejected", value: rejectedCount, color: "text-red-400" },
          { label: "High / Critical risk", value: highRiskCount, color: "text-amber-400" },
        ].map((s) => (
          <Card key={s.label} className="border-border/60">
            <CardContent className="pt-5">
              <p className="text-xs uppercase tracking-widest text-muted-foreground">{s.label}</p>
              <p className={cn("mt-2 text-3xl font-bold tabular-nums", s.color)}>
                {loading ? <Skeleton className="h-8 w-16 inline-block" /> : s.value}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filter bar */}
      <Card className="border-border/60">
        <CardContent className="pt-5">
          <div className="flex flex-wrap items-center gap-3">
            {/* Search */}
            <div className="relative min-w-[200px] flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                id="cases-search"
                type="text"
                placeholder="Search by name or case ID…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-xl border border-border/60 bg-secondary/40 py-2 pl-9 pr-4 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
              />
            </div>

            {/* Decision filter */}
            <div className="relative">
              <select
                id="cases-decision-filter"
                value={decision}
                onChange={(e) => setDecision(e.target.value)}
                className="appearance-none rounded-xl border border-border/60 bg-secondary/40 py-2 pl-4 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                <option value="">All decisions</option>
                <option value="APPROVE">APPROVE</option>
                <option value="REJECT">REJECT</option>
                <option value="ESCALATE TO HUMAN REVIEW">ESCALATE</option>
              </select>
              <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            </div>

            {/* Risk filter */}
            <div className="relative">
              <select
                id="cases-risk-filter"
                value={riskLevel}
                onChange={(e) => setRiskLevel(e.target.value)}
                className="appearance-none rounded-xl border border-border/60 bg-secondary/40 py-2 pl-4 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                <option value="">All risk levels</option>
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
                <option value="Critical">Critical</option>
              </select>
              <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            </div>

            {/* Escalated toggle */}
            <div className="relative">
              <select
                id="cases-escalated-filter"
                value={escalated}
                onChange={(e) => setEscalated(e.target.value as "" | "true" | "false")}
                className="appearance-none rounded-xl border border-border/60 bg-secondary/40 py-2 pl-4 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                <option value="">All escalation</option>
                <option value="true">Escalated</option>
                <option value="false">Not escalated</option>
              </select>
              <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            </div>

            {hasFilters && (
              <Button variant="secondary" size="sm" onClick={clearFilters} className="gap-1.5">
                <Filter className="h-3.5 w-3.5" />
                Clear
              </Button>
            )}

            {loading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
          </div>
        </CardContent>
      </Card>

      {/* Case list */}
      <Card className="border-border/60">
        <CardHeader className="pb-2">
          <CardTitle>
            {loading ? "Loading…" : `${cases.length} case${cases.length !== 1 ? "s" : ""}${hasFilters ? " matching filters" : ""}`}
          </CardTitle>
          <CardDescription>Click any row to open the full governance trace.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-14 rounded-xl" />
              ))}
            </div>
          ) : cases.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center text-sm text-muted-foreground">
              <Layers className="h-8 w-8 opacity-30" />
              <p>{hasFilters ? "No cases match the current filters." : "No cases found."}</p>
              {hasFilters && (
                <Button variant="secondary" size="sm" onClick={clearFilters}>
                  Clear filters
                </Button>
              )}
            </div>
          ) : (
            <div className="divide-y divide-border/40">
              {cases.map((c) => (
                <Link
                  key={c.case_id}
                  href={`/cases/${c.case_id}`}
                  className="group flex items-center gap-4 px-6 py-4 transition-colors hover:bg-secondary/40"
                >
                  {/* Decision icon */}
                  <div className="shrink-0">
                    <DecisionIcon decision={c.final_decision} />
                  </div>

                  {/* Customer + case ID */}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate font-semibold">{c.customer_name}</p>
                      {c.requires_human_review && (
                        <Badge variant="warning" className="shrink-0 text-[10px]">
                          Needs review
                        </Badge>
                      )}
                    </div>
                    <p className="truncate text-xs text-muted-foreground">
                      {c.case_id} · {c.requested_product_type}
                    </p>
                  </div>

                  {/* Decision */}
                  <div className="hidden w-36 sm:block">
                    <Badge variant={decisionVariant(c.final_decision)} className="text-[11px]">
                      {c.final_decision ?? "Pending"}
                    </Badge>
                  </div>

                  {/* Risk */}
                  <div className="hidden w-24 md:block">
                    {c.risk_level ? (
                      <Badge variant={riskVariant(c.risk_level)} className="text-[11px]">
                        {c.risk_level}
                      </Badge>
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )}
                  </div>

                  {/* Risk score */}
                  <div className="hidden w-20 text-right lg:block">
                    {c.risk_score != null ? (
                      <span className="tabular-nums text-sm font-medium">{c.risk_score}</span>
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )}
                  </div>

                  {/* Date */}
                  <div className="hidden w-32 text-right text-xs text-muted-foreground xl:block">
                    {formatDate(c.created_at)}
                  </div>

                  {/* Arrow */}
                  <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-1" />
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
