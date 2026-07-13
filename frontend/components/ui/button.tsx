import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-2 text-sm font-medium",
    "rounded-lg transition-all duration-150 focus-visible:outline-none",
    "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1",
    "disabled:pointer-events-none disabled:opacity-40 select-none",
  ].join(" "),
  {
    variants: {
      variant: {
        default: [
          "bg-primary text-primary-foreground",
          "hover:brightness-110 active:brightness-95",
          "shadow-sm shadow-primary/20",
        ].join(" "),
        secondary: [
          "bg-secondary text-secondary-foreground border border-border/60",
          "hover:bg-muted active:bg-secondary",
        ].join(" "),
        outline: [
          "border border-border bg-transparent text-foreground",
          "hover:bg-secondary/60 active:bg-secondary",
        ].join(" "),
        ghost: [
          "text-muted-foreground",
          "hover:bg-secondary/60 hover:text-foreground active:bg-secondary",
        ].join(" "),
        destructive: [
          "bg-destructive text-destructive-foreground",
          "hover:brightness-110 active:brightness-95",
          "shadow-sm shadow-destructive/20",
        ].join(" "),
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 px-3 text-xs rounded-md",
        lg: "h-11 px-6 text-base rounded-xl",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  ),
);
Button.displayName = "Button";

export { Button, buttonVariants };
