"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  FileCheck2,
  LayoutDashboard,
  Layers,
  ListChecks,
  MessageSquare,
  Shield,
  Sparkles,
  Zap,
} from "lucide-react";

import { cn } from "@/lib/utils";

const sections = [
  {
    label: "Overview",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/cases", label: "Cases", icon: Layers },
    ],
  },
  {
    label: "Operations",
    items: [
      { href: "/evaluation", label: "New Evaluation", icon: Sparkles },
      { href: "/reviews", label: "Human Review", icon: ListChecks },
      { href: "/audit", label: "Audit Log", icon: FileCheck2 },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { href: "/chat", label: "AI Analyst", icon: MessageSquare },
      { href: "/policies", label: "Policies", icon: Shield },
    ],
  },
];

export function SidebarNav() {
  const pathname = usePathname();

  return (
    <aside className="hidden xl:flex w-60 shrink-0 flex-col sticky top-6 h-[calc(100vh-3rem)] overflow-hidden">
      {/* Logo block */}
      <div className="mb-6 flex items-center gap-3 px-2">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-glow-sm shrink-0">
          <Zap className="h-4.5 w-4.5" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
            Guardrail
          </p>
          <p className="truncate text-sm font-semibold leading-tight">Financial AI Control</p>
        </div>
      </div>

      {/* Nav sections */}
      <nav className="flex-1 space-y-5 overflow-y-auto pr-1">
        {sections.map((section) => (
          <div key={section.label}>
            <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60">
              {section.label}
            </p>
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all duration-150",
                      active
                        ? "bg-primary/10 text-primary font-semibold border-l-2 border-primary pl-[10px]"
                        : "text-muted-foreground hover:bg-secondary/70 hover:text-foreground border-l-2 border-transparent pl-[10px]",
                    )}
                  >
                    <Icon
                      className={cn(
                        "h-4 w-4 shrink-0 transition-colors",
                        active ? "text-primary" : "text-muted-foreground group-hover:text-foreground",
                      )}
                    />
                    <span className="truncate">{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Status block */}
      <div className="mt-4 rounded-lg border border-success/20 bg-success/5 px-3 py-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-success">
          <span className="relative flex h-2 w-2 shrink-0">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
          </span>
          Governance online
        </div>
        <p className="mt-1.5 text-[11px] leading-relaxed text-muted-foreground">
          Policy engine · Audit trace · Human override
        </p>
      </div>
    </aside>
  );
}
