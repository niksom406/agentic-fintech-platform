import Link from "next/link";
import { BellRing, ExternalLink, ShieldCheck } from "lucide-react";

import { ThemeToggle } from "@/components/theme-toggle";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function TopNav() {
  return (
    <div className="sticky top-0 z-20 flex items-center justify-between gap-4 rounded-xl border border-border/50 bg-card/70 px-5 py-3 backdrop-blur-md shadow-panel">
      {/* Left: breadcrumb + status */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="hidden sm:flex items-center gap-2 text-sm text-muted-foreground">
          <span className="font-medium text-foreground">Guardrail Console</span>
        </div>
        <Badge variant="success" className="hidden sm:inline-flex">
          <span className="relative flex h-1.5 w-1.5 shrink-0">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-success" />
          </span>
          Live
        </Badge>
      </div>

      {/* Right: actions */}
      <div className="flex items-center gap-2">
        <Badge variant="outline" className="hidden md:inline-flex gap-1.5">
          <ShieldCheck className="h-3 w-3 text-primary" />
          Policy v2 active
        </Badge>

        <Button variant="ghost" size="icon" className="relative">
          <BellRing className="h-4 w-4" />
          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-primary" />
        </Button>

        <ThemeToggle />

        <Link
          href="/evaluation"
          className={cn(
            buttonVariants({ variant: "default", size: "sm" }),
            "gap-1.5",
          )}
        >
          <ExternalLink className="h-3.5 w-3.5" />
          New Review
        </Link>
      </div>
    </div>
  );
}
