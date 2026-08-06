"use client";

import Link from "next/link";
import type { PortalDossierSummary } from "@/lib/types";
import { CheckCircle2, Clock, AlertCircle, FileText } from "lucide-react";

interface DossierCardProps {
  dossier: PortalDossierSummary;
}

const STATUS_COLORS: Record<string, string> = {
  nouveau: "bg-slate-100 text-slate-700",
  en_cours: "bg-blue-100 text-blue-700",
  documents_manquants: "bg-amber-100 text-amber-700",
  en_revision: "bg-purple-100 text-purple-700",
  soumis: "bg-indigo-100 text-indigo-700",
  approuve: "bg-green-100 text-green-700",
  refuse: "bg-red-100 text-red-700",
  archive: "bg-gray-100 text-gray-700",
};

const STATUS_ICONS: Record<string, React.ReactNode> = {
  nouveau: <FileText className="h-5 w-5" aria-hidden="true" />,
  en_cours: <Clock className="h-5 w-5" aria-hidden="true" />,
  documents_manquants: <AlertCircle className="h-5 w-5" aria-hidden="true" />,
  en_revision: <Clock className="h-5 w-5" aria-hidden="true" />,
  soumis: <Clock className="h-5 w-5" aria-hidden="true" />,
  approuve: <CheckCircle2 className="h-5 w-5" aria-hidden="true" />,
  refuse: <AlertCircle className="h-5 w-5" aria-hidden="true" />,
  archive: <FileText className="h-5 w-5" aria-hidden="true" />,
};

export function DossierCard({ dossier }: DossierCardProps) {
  const statusColor = STATUS_COLORS[dossier.status] || "bg-gray-100 text-gray-700";
  const statusIcon = STATUS_ICONS[dossier.status];

  return (
    <Link href={`/portal/dossiers/${dossier.id}`}>
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
        <div className="mb-4 flex items-start justify-between">
          <div className="flex items-center gap-2">
            {statusIcon}
            <span className={`rounded-full px-3 py-1 text-sm font-medium ${statusColor}`}>
              {dossier.status_label.fr}
            </span>
          </div>
          {dossier.reference_number && (
            <div className="text-sm text-gray-500">
              Réf: {dossier.reference_number}
            </div>
          )}
        </div>

        {/* Progress bar */}
        <div className="mb-4">
          <div className="mb-1 flex items-center justify-between text-sm">
            <span className="font-medium text-gray-700">Progression</span>
            <span className="text-gray-600">{dossier.progress}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
            <div
              className="h-full bg-blue-600 transition-all duration-300"
              style={{ width: `${dossier.progress}%` }}
            />
          </div>
        </div>

        {/* Dates */}
        <div className="space-y-1 text-sm text-gray-600">
          {dossier.submitted_at && (
            <div>
              Soumis le {new Date(dossier.submitted_at).toLocaleDateString("fr-CA")}
            </div>
          )}
          {dossier.created_at && (
            <div>
              Créé le {new Date(dossier.created_at).toLocaleDateString("fr-CA")}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
