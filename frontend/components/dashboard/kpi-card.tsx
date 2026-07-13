import { type LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

export function KpiCard({
  title,
  value,
  description,
  icon: Icon,
}: {
  title: string;
  value: string;
  description: string;
  icon: LucideIcon;
}) {
  return (
    <Card className="hover:border-primary/30 transition-all duration-200 group">
      <CardContent className="flex items-start justify-between p-5 space-y-0">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{title}</p>
          <p className="text-2xl font-bold tracking-tight text-foreground">{value}</p>
          <p className="text-xs text-muted-foreground/80 leading-normal">{description}</p>
        </div>
        <div className="rounded-lg border border-border bg-secondary/40 p-2 text-muted-foreground group-hover:text-primary group-hover:border-primary/20 group-hover:bg-primary/5 transition-all duration-150">
          <Icon className="h-4.5 w-4.5" />
        </div>
      </CardContent>
    </Card>
  );
}

