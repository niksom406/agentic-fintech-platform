import { type LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export interface KpiCardProps {
  title: string;
  value: string;
  description: string;
  icon: LucideIcon;
  trend?: {
    text: string;
    direction: "up" | "down" | "neutral";
  };
}

export function KpiCard({
  title,
  value,
  description,
  icon: Icon,
  trend,
}: KpiCardProps) {
  // Determine icon color based on title/type
  let iconColor = "text-primary";
  const lowerTitle = title.toLowerCase();
  if (lowerTitle.includes("approve")) iconColor = "text-emerald-400";
  else if (lowerTitle.includes("reject")) iconColor = "text-rose-400";
  else if (lowerTitle.includes("escalat") || lowerTitle.includes("warn")) iconColor = "text-amber-400";
  else if (lowerTitle.includes("risk")) iconColor = "text-violet-400";
  else if (lowerTitle.includes("confidence")) iconColor = "text-sky-400";
  else if (lowerTitle.includes("flag")) iconColor = "text-red-400";
  else if (lowerTitle.includes("pending") || lowerTitle.includes("review")) iconColor = "text-fuchsia-400";
  else if (lowerTitle.includes("total") || lowerTitle.includes("case")) iconColor = "text-indigo-400";

  return (
    <Card className="hover:border-border/80 transition-all duration-150">
      <CardContent className="p-4 flex flex-col items-start space-y-0">
        {/* Top: Icon (no bg box, flat colored icon like reference image) */}
        <div className={iconColor}>
          <Icon className="h-5 w-5" />
        </div>

        {/* Middle: Title */}
        <p className="text-[13px] font-medium text-muted-foreground mt-2 leading-none">
          {title}
        </p>

        {/* Middle: Large Value */}
        <p className="text-3xl font-bold tracking-tight text-foreground mt-1.5 leading-none">
          {value}
        </p>
      </CardContent>
    </Card>
  );
}

