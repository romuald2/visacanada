import { cn } from "@/lib/utils";
import { sortByUrgency } from "@/lib/deadlines";
import type { UpcomingAlert } from "@/lib/types";
import { DeadlineCard } from "./DeadlineCard";
import { SeverityCounters } from "./SeverityCounters";

export interface UpcomingDeadlinesProps {
  items: UpcomingAlert[];
  windowDays?: number;
  className?: string;
}

/**
 * Dashboard widget: severity counters plus the urgency-sorted list of
 * upcoming deadlines. Pure — the caller fetches and passes `items` in.
 */
export function UpcomingDeadlines({
  items,
  windowDays = 30,
  className,
}: UpcomingDeadlinesProps) {
  const sorted = sortByUrgency(items);

  return (
    <section
      className={cn("space-y-4 rounded-xl border border-border bg-card p-5", className)}
      aria-label="Echeances a venir"
    >
      <header className="space-y-1">
        <h2 className="text-lg font-semibold text-card-foreground">
          {windowDays} prochains jours
        </h2>
        <p className="text-sm text-muted-foreground">
          {sorted.length === 0
            ? "Aucune echeance a venir"
            : `${sorted.length} echeance${sorted.length > 1 ? "s" : ""} a suivre`}
        </p>
      </header>

      <SeverityCounters items={items} />

      {sorted.length > 0 ? (
        <ul className="space-y-2">
          {sorted.map((alert) => (
            <li key={alert.id}>
              <DeadlineCard alert={alert} />
            </li>
          ))}
        </ul>
      ) : (
        <p className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
          Rien a signaler pour cette periode.
        </p>
      )}
    </section>
  );
}
