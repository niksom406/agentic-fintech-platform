import Link from "next/link";
import {
  ArrowRight,
  ShieldCheck,
  GitBranch,
  Activity,
  Workflow,
  Sparkles,
  Layers,
  Database,
  User,
  Cpu,
  ArrowRightLeft,
  FileCheck2,
  CheckCircle,
  AlertTriangle
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const features = [
  {
    icon: ShieldCheck,
    title: "Multi-Agent Governance",
    description: "Orchestrates dedicated AI agents for intake validation, risk calculation, fairness screening, and final system decisions.",
  },
  {
    icon: Layers,
    title: "Deterministic Guardrails",
    description: "Enforces strict limits (e.g., credit score thresholds, debt-to-income limits) to block risky actions before execution.",
  },
  {
    icon: Database,
    title: "Audit-Grade Logging",
    description: "Captures complete system logs, policy outputs, and agent explanation chains in immutable database archives.",
  },
];

export default function HomePage() {
  return (
    <main className="min-h-screen relative overflow-hidden bg-background">
      {/* Decorative top ambient glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[500px] pointer-events-none opacity-30 select-none">
        <div className="absolute inset-0 bg-gradient-to-b from-primary/10 via-primary/5 to-transparent blur-3xl rounded-full" />
      </div>

      {/* Hero Section */}
      <section className="relative z-10 mx-auto max-w-[1500px] px-6 pt-24 pb-16 lg:px-12">
        <div className="flex flex-col items-center text-center max-w-4xl mx-auto">
          <Badge variant="primary" className="mb-6 font-mono tracking-wider text-xs">
            Aegis Finance Governance Engine
          </Badge>
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight text-foreground leading-[1.1] animate-in">
            Deterministic Guardrails &amp; Agentic AI Control
          </h1>
          <p className="mt-6 text-lg md:text-xl text-muted-foreground leading-relaxed max-w-2xl">
            A secure governance layer for financial institutions that monitors, validates, and logs agentic AI recommendations before execution.
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <Link href="/dashboard" className={cn(buttonVariants({ size: "lg" }), "gap-2")}>
              Enter Control Panel
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link href="/evaluation" className={cn(buttonVariants({ variant: "secondary", size: "lg" }))}>
              Intake Evaluation
            </Link>
          </div>
        </div>

        {/* Feature Cards Grid */}
        <div className="mt-20 grid gap-6 md:grid-cols-3 max-w-6xl mx-auto">
          {features.map((item) => (
            <Card key={item.title} className="panel-gradient border-border/50 hover:shadow-glow transition-all duration-200">
              <CardHeader className="p-6 pb-2">
                <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <item.icon className="h-5 w-5" />
                </div>
                <CardTitle className="mt-4 text-base font-semibold">{item.title}</CardTitle>
              </CardHeader>
              <CardContent className="p-6 pt-0">
                <CardDescription className="text-sm">{item.description}</CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* System Workflow Section */}
      <section className="relative z-10 mx-auto max-w-[1500px] px-6 py-16 lg:px-12">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <Badge variant="outline" className="mb-4">System Architecture</Badge>
          <h2 className="text-3xl font-bold tracking-tight">System Workflow Pipeline</h2>
          <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
            Trace how payloads transit through our ingestion channels, rule agents, validation engines, and fallback human reviews.
          </p>
        </div>

        {/* Interactive Interactive Diagram */}
        <div className="max-w-5xl mx-auto rounded-xl border border-border/60 bg-card/60 p-6 md:p-8 backdrop-blur shadow-panel-lg">
          <div className="grid gap-8 lg:grid-cols-5 relative">
            
            {/* Step 1: User / Intake */}
            <div className="flex flex-col items-center text-center relative z-10">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-border/70 bg-secondary/80 text-foreground shadow-sm">
                <User className="h-5 w-5" />
              </div>
              <p className="mt-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Step 1</p>
              <h4 className="mt-1 text-sm font-semibold text-foreground">User Intake</h4>
              <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                Applicant profile is submitted via Next.js frontend console.
              </p>
            </div>

            {/* Step 2: FastAPI Ingestion */}
            <div className="flex flex-col items-center text-center relative z-10">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-border/70 bg-secondary/80 text-primary shadow-sm">
                <Workflow className="h-5 w-5" />
              </div>
              <p className="mt-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Step 2</p>
              <h4 className="mt-1 text-sm font-semibold text-foreground">API Ingestion</h4>
              <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                FastAPI backend receives, normalizes, and logs raw case snapshot.
              </p>
            </div>

            {/* Step 3: Guardrail Engine */}
            <div className="flex flex-col items-center text-center relative z-10">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-primary/30 bg-primary/10 text-primary shadow-glow-sm">
                <Cpu className="h-5 w-5 animate-pulse" />
              </div>
              <p className="mt-3 text-xs font-semibold uppercase tracking-wider text-primary">Step 3</p>
              <h4 className="mt-1 text-sm font-semibold text-foreground">AI Guardrails</h4>
              <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                Multi-agent validation checks policy, compliance limits, and risk.
              </p>
            </div>

            {/* Step 4: Storage & Trace */}
            <div className="flex flex-col items-center text-center relative z-10">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-border/70 bg-secondary/80 text-foreground shadow-sm">
                <Database className="h-5 w-5" />
              </div>
              <p className="mt-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Step 4</p>
              <h4 className="mt-1 text-sm font-semibold text-foreground">Audit Archival</h4>
              <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                Saves decision telemetry, LangSmith traces, and audit logs.
              </p>
            </div>

            {/* Step 5: Final Response */}
            <div className="flex flex-col items-center text-center relative z-10">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-success/30 bg-success/10 text-success shadow-sm">
                <CheckCircle className="h-5 w-5" />
              </div>
              <p className="mt-3 text-xs font-semibold uppercase tracking-wider text-success">Step 5</p>
              <h4 className="mt-1 text-sm font-semibold text-foreground">Final Decision</h4>
              <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                Approve, reject, or escalate request to the review queue.
              </p>
            </div>

            {/* Connecting lines for medium screens */}
            <div className="hidden lg:block absolute top-6 left-[10%] right-[10%] h-0.5 border-t border-dashed border-border -z-0" />
          </div>
        </div>
      </section>

      {/* Rationale & Positioning */}
      <section className="relative z-10 mx-auto max-w-[1500px] px-6 pb-24 lg:px-12">
        <Card className="panel-gradient overflow-hidden border-border/60">
          <div className="grid gap-8 lg:grid-cols-[0.8fr_1.2fr]">
            <div className="bg-primary/5 p-8 flex flex-col justify-center border-b lg:border-b-0 lg:border-r border-border/50">
              <Badge variant="primary" className="w-fit">Strategic positioning</Badge>
              <h3 className="mt-4 text-2xl font-bold leading-tight">Built for Secure Model Risk Governance</h3>
              <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
                Aegis works as a protective middleware barrier between your upstream generative model recommendation engine and the final action orchestration layers.
              </p>
            </div>
            <div className="grid gap-4 p-8 sm:grid-cols-2">
              {[
                { title: "Policy Isolation", desc: "Allows instant dynamic policy rule updates without redeploying core applications." },
                { title: "Trace Verification", desc: "Outputs readable agent decisions, logic streams, and confidence indexes." },
                { title: "Conversational RAG Tooling", desc: "Ask queries directly, inspect current policy versions, and trace failures in plain English." },
                { title: "Secure Override Routing", desc: "Flags compliance exceptions to assign case-level human reviewers with trackable explanations." },
              ].map((item) => (
                <div key={item.title} className="rounded-lg border border-border/50 bg-secondary/20 p-4 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                    <GitBranch className="h-4.5 w-4.5 text-primary" />
                    {item.title}
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </section>
    </main>
  );
}
