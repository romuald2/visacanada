import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { countBySeverity } from "@/lib/deadlines";
import type { UpcomingAlert } from "@/lib/types";

export interface CriticalBadgeProps {
  items: UpcomingAlert[];
  className?: string;
}

/**
 * Header indicator: number of critical upcoming deadlines. Renders nothing
 * when there are none, so it stays quiet on a healthy dashboard.
 */
export function CriticalBadge({ items, className }: CriticalBadgeProps) {
  const critical = countBySeverity(items).critical;
  if (critical === 0) return null;

  return (
    <span
      role="status"
      aria-label={`${critical} échéance${critical > 1 ? "s" : ""} critique${critical > 1 ? "s" : ""}`}
      className={cn(
        "flex items-center gap-1.5 rounded-full bg-destructive/10 px-3 py-1 text-sm font-semibold text-destructive",
        className,
      )}
    >
      <AlertTriangle className="h-4 w-4" aria-hidden />
      {critical} critique{critical > 1 ? "s" : ""}
    </span>
  );
}
