import { cn } from "@/lib/utils";
import { countBySeverity, SEVERITY_LABELS } from "@/lib/deadlines";
import type { AlertSeverity, UpcomingAlert } from "@/lib/types";

const ORDER: AlertSeverity[] = ["critical", "warning", "info"];

const TILE_CLASSES: Record<AlertSeverity, string> = {
  critical: "border-destructive/40 bg-destructive/5 text-destructive",
  warning: "border-amber-500/40 bg-amber-500/5 text-amber-600",
  info: "border-border bg-secondary/40 text-secondary-foreground",
};

export interface SeverityCountersProps {
  items: UpcomingAlert[];
  className?: string;
}

/** Three tiles summarizing how many upcoming items sit at each severity. */
export function SeverityCounters({ items, className }: SeverityCountersProps) {
  const counts = countBySeverity(items);

  return (
    <div
      className={cn("grid grid-cols-3 gap-3", className)}
      role="group"
      aria-label="Repartition par severite"
    >
      {ORDER.map((severity) => (
        <div
          key={severity}
          className={cn(
            "flex flex-col items-center rounded-lg border p-3 text-center",
            TILE_CLASSES[severity],
          )}
        >
          <span className="text-2xl font-semibold tabular-nums">
            {counts[severity]}
          </span>
          <span className="text-xs font-medium uppercase tracking-wide">
            {SEVERITY_LABELS[severity]}
          </span>
        </div>
      ))}
    </div>
  );
}
