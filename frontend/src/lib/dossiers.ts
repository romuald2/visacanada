/** Presentation helpers for dossiers (status labels + badge styling). */

import type { DossierStatus } from "@/lib/types";

export const DOSSIER_STATUS_LABELS: Record<DossierStatus, string> = {
  nouveau: "Nouveau",
  en_cours: "En cours",
  documents_manquants: "Documents manquants",
  en_revision: "En révision",
  soumis: "Soumis",
  approuve: "Approuvé",
  refuse: "Refusé",
  archive: "Archivé",
};

export function dossierStatusLabel(status: DossierStatus): string {
  return DOSSIER_STATUS_LABELS[status] ?? status;
}

/** Tailwind classes for a status badge, keyed off the workflow stage. */
export function dossierStatusClasses(status: DossierStatus): string {
  switch (status) {
    case "approuve":
      return "bg-emerald-500/10 text-emerald-600";
    case "refuse":
      return "bg-destructive/10 text-destructive";
    case "documents_manquants":
      return "bg-amber-500/10 text-amber-600";
    case "soumis":
    case "en_revision":
      return "bg-blue-500/10 text-blue-600";
    case "archive":
      return "bg-muted text-muted-foreground";
    case "nouveau":
    case "en_cours":
    default:
      return "bg-secondary text-secondary-foreground";
  }
}
