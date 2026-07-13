import type * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-semibold tracking-wide leading-none border",
  {
    variants: {
      variant: {
        neutral: "bg-secondary/80 text-secondary-foreground border-border/50",
        success: "bg-success/10 text-success border-success/25",
        destructive: "bg-destructive/10 text-destructive border-destructive/25",
        warning: "bg-warning/10 text-warning border-warning/25",
        outline: "border-border/70 text-foreground bg-transparent",
        primary: "bg-primary/10 text-primary border-primary/25",
      },
    },
    defaultVariants: {
      variant: "neutral",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant, className }))} {...props} />;
}
