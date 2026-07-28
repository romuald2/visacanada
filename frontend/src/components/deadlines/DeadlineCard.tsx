import { cn } from "@/lib/utils";
import {
  alertTypeLabel,
  formatDaysLeft,
  SEVERITY_LABELS,
  severityBadgeClasses,
} from "@/lib/deadlines";
import type { UpcomingAlert } from "@/lib/types";

export interface DeadlineCardProps {
  alert: UpcomingAlert;
  className?: string;
}

/** A single upcoming deadline row: type, title, severity badge, days-left. */
export function DeadlineCard({ alert, className }: DeadlineCardProps) {
  const daysLabel = formatDaysLeft(alert.days_left);
  const overdue = alert.days_left !== null && alert.days_left < 0;

  return (
    <article
      className={cn(
        "flex items-start justify-between gap-3 rounded-lg border border-border bg-card p-4",
        className,
      )}
    >
      <div className="min-w-0 space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {alertTypeLabel(alert.alert_type)}
          </span>
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-xs font-semibold",
              severityBadgeClasses(alert.severity),
            )}
          >
            {SEVERITY_LABELS[alert.severity]}
          </span>
        </div>
        <p className="truncate font-medium text-card-foreground">
          {alert.title}
        </p>
        {alert.message ? (
          <p className="line-clamp-2 text-sm text-muted-foreground">
            {alert.message}
          </p>
        ) : null}
      </div>
      {daysLabel ? (
        <span
          className={cn(
            "whitespace-nowrap text-sm font-medium",
            overdue ? "text-destructive" : "text-muted-foreground",
          )}
        >
          {daysLabel}
        </span>
      ) : null}
    </article>
  );
}
