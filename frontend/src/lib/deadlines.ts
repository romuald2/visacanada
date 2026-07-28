/** Presentation helpers for deadlines/alerts (labels, severity styling). */

import type { AlertSeverity, AlertType, UpcomingAlert } from "@/lib/types";

/** Human-readable French labels per alert type. */
export const ALERT_TYPE_LABELS: Record<AlertType, string> = {
  passport_expiring: "Passeport",
  medical_expiring: "Examen medical",
  language_expiring: "Test de langue",
  express_entry_round: "Ronde Express Entry",
  policy_change: "Changement de politique",
  submission_deadline: "Soumission",
  ita_response: "Reponse ITA",
  biometrics: "Biometries",
  ppr: "Demande de passeport",
  medical_request: "Examen medical demande",
  permit_expiring: "Permis",
};

export function alertTypeLabel(type: AlertType): string {
  return ALERT_TYPE_LABELS[type] ?? type;
}

/** Tailwind classes for a severity badge, using the design tokens. */
export function severityBadgeClasses(severity: AlertSeverity): string {
  switch (severity) {
    case "critical":
      return "bg-destructive text-destructive-foreground";
    case "warning":
      return "bg-amber-500 text-white";
    case "info":
    default:
      return "bg-secondary text-secondary-foreground";
  }
}

export const SEVERITY_LABELS: Record<AlertSeverity, string> = {
  critical: "Critique",
  warning: "Avertissement",
  info: "Info",
};

/** Format the days-left field into a short French phrase. */
export function formatDaysLeft(daysLeft: number | null): string {
  if (daysLeft === null || daysLeft === undefined) return "";
  if (daysLeft < 0) {
    const n = Math.abs(daysLeft);
    return `En retard de ${n} jour${n > 1 ? "s" : ""}`;
  }
  if (daysLeft === 0) return "Aujourd'hui";
  return `Dans ${daysLeft} jour${daysLeft > 1 ? "s" : ""}`;
}

const SEVERITY_RANK: Record<AlertSeverity, number> = {
  critical: 0,
  warning: 1,
  info: 2,
};

/** Count alerts per severity. */
export function countBySeverity(
  items: UpcomingAlert[],
): Record<AlertSeverity, number> {
  const counts: Record<AlertSeverity, number> = {
    critical: 0,
    warning: 0,
    info: 0,
  };
  for (const item of items) {
    counts[item.severity] = (counts[item.severity] ?? 0) + 1;
  }
  return counts;
}

/** Sort by severity (critical first) then soonest days_left. */
export function sortByUrgency(items: UpcomingAlert[]): UpcomingAlert[] {
  return [...items].sort((a, b) => {
    const rank = SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity];
    if (rank !== 0) return rank;
    const da = a.days_left ?? Number.MAX_SAFE_INTEGER;
    const db = b.days_left ?? Number.MAX_SAFE_INTEGER;
    return da - db;
  });
}
