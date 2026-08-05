import { cn } from "@/lib/utils";
import { dossierStatusClasses, dossierStatusLabel } from "@/lib/dossiers";
import type { Dossier } from "@/lib/types";

export interface DossierListProps {
  items: Dossier[];
  total: number;
  page: number;
  pages: number;
  loading?: boolean;
  error?: string | null;
  onPageChange?: (page: number) => void;
  className?: string;
}

/** Paginated dossier table. Pure — the parent fetches and passes data in. */
export function DossierList({
  items,
  total,
  page,
  pages,
  loading = false,
  error = null,
  onPageChange,
  className,
}: DossierListProps) {
  return (
    <section
      className={cn("rounded-xl border border-border bg-card", className)}
      aria-label="Liste des dossiers"
    >
      <header className="flex items-center justify-between border-b border-border px-5 py-3">
        <h2 className="text-lg font-semibold text-card-foreground">Dossiers</h2>
        <span className="text-sm text-muted-foreground">{total} au total</span>
      </header>

      {error ? (
        <p role="alert" className="p-6 text-sm text-destructive">
          {error}
        </p>
      ) : loading ? (
        <p className="p-6 text-sm text-muted-foreground">Chargement…</p>
      ) : items.length === 0 ? (
        <p className="p-6 text-sm text-muted-foreground">Aucun dossier.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-muted-foreground">
              <th className="px-5 py-2 font-medium">Référence</th>
              <th className="px-5 py-2 font-medium">Statut</th>
              <th className="px-5 py-2 font-medium">Consultant</th>
              <th className="px-5 py-2 font-medium">Conformité</th>
            </tr>
          </thead>
          <tbody>
            {items.map((d) => (
              <tr
                key={d.id}
                className="border-b border-border last:border-0 hover:bg-secondary/40"
              >
                <td className="px-5 py-3 font-medium text-card-foreground">
                  {d.reference_number ?? `#${d.id}`}
                </td>
                <td className="px-5 py-3">
                  <span
                    className={cn(
                      "rounded-full px-2 py-0.5 text-xs font-semibold",
                      dossierStatusClasses(d.status),
                    )}
                  >
                    {dossierStatusLabel(d.status)}
                  </span>
                </td>
                <td className="px-5 py-3 text-muted-foreground">
                  {d.assigned_to ? `#${d.assigned_to}` : "Non assigné"}
                </td>
                <td className="px-5 py-3 text-muted-foreground tabular-nums">
                  {d.compliance_score !== null
                    ? `${Math.round(d.compliance_score)} %`
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {pages > 1 ? (
        <footer className="flex items-center justify-between px-5 py-3 text-sm">
          <button
            type="button"
            disabled={page <= 1 || loading}
            onClick={() => onPageChange?.(page - 1)}
            className="rounded-md border border-border px-3 py-1 disabled:opacity-50"
          >
            Précédent
          </button>
          <span className="text-muted-foreground">
            Page {page} / {pages}
          </span>
          <button
            type="button"
            disabled={page >= pages || loading}
            onClick={() => onPageChange?.(page + 1)}
            className="rounded-md border border-border px-3 py-1 disabled:opacity-50"
          >
            Suivant
          </button>
        </footer>
      ) : null}
    </section>
  );
}
