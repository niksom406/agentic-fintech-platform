"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BellRing, ExternalLink, Menu, ShieldCheck, X, Zap } from "lucide-react";

import { navSections } from "@/components/layout/sidebar-nav";
import { ThemeToggle } from "@/components/theme-toggle";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function TopNav() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!menuOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  return (
    <>
      <div className="sticky top-0 z-20 flex items-center justify-between gap-3 rounded-xl border border-border/50 bg-card/70 px-3 py-3 backdrop-blur-md shadow-panel sm:gap-4 sm:px-5">
        <div className="flex min-w-0 items-center gap-2">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="xl:hidden shrink-0"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>

          <div className="flex min-w-0 flex-col items-start">
            <h1 className="truncate text-base font-bold leading-tight tracking-tight text-foreground sm:text-lg">
              Guardrail Operating Dashboard
            </h1>
            <span className="hidden text-xs font-medium text-muted-foreground xs:inline sm:inline">
              Financial AI Governance Solution
            </span>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <Badge variant="success" className="hidden sm:inline-flex">
            <span className="relative flex h-1.5 w-1.5 shrink-0">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-success" />
            </span>
            Live
          </Badge>

          <Badge variant="outline" className="hidden md:inline-flex gap-1.5">
            <ShieldCheck className="h-3 w-3 text-primary" />
            Policy v2 active
          </Badge>

          <Button variant="ghost" size="icon" className="relative hidden sm:inline-flex">
            <BellRing className="h-4 w-4" />
            <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-primary" />
          </Button>

          <ThemeToggle />

          <Link
            href="/evaluation"
            className={cn(buttonVariants({ variant: "default", size: "sm" }), "gap-1.5")}
          >
            <ExternalLink className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">New Review</span>
            <span className="sm:hidden">New</span>
          </Link>
        </div>
      </div>

      {/* Mobile / tablet navigation drawer */}
      {menuOpen ? (
        <div className="fixed inset-0 z-50 xl:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-slate-950/55 backdrop-blur-sm"
            aria-label="Close menu overlay"
            onClick={() => setMenuOpen(false)}
          />
          <aside className="absolute left-0 top-0 flex h-full w-[min(20rem,88vw)] flex-col border-r border-border/60 bg-card p-4 shadow-panel animate-fade-in-up">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-glow-sm shrink-0">
                  <Zap className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <p className="truncate text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
                    Guardrail
                  </p>
                  <p className="truncate text-sm font-semibold leading-tight">Financial AI Control</p>
                </div>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label="Close menu"
                onClick={() => setMenuOpen(false)}
              >
                <X className="h-5 w-5" />
              </Button>
            </div>

            <nav className="flex-1 space-y-5 overflow-y-auto pr-1">
              {navSections.map((section) => (
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
                          onClick={() => setMenuOpen(false)}
                          className={cn(
                            "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all duration-150",
                            active
                              ? "border-l-2 border-primary bg-primary/10 pl-[10px] font-semibold text-primary"
                              : "border-l-2 border-transparent pl-[10px] text-muted-foreground hover:bg-secondary/70 hover:text-foreground",
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
          </aside>
        </div>
      ) : null}
    </>
  );
}
