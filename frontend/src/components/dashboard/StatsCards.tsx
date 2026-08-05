interface StatsCardsProps {
  totalDossiers: number;
  totalCandidates: number;
  averageComplianceScore: number | null;
}

export function StatsCards({
  totalDossiers,
  totalCandidates,
  averageComplianceScore,
}: StatsCardsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <p className="text-sm font-medium text-gray-600">Dossiers actifs</p>
        <p className="mt-2 text-3xl font-semibold text-gray-900">{totalDossiers}</p>
      </div>
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <p className="text-sm font-medium text-gray-600">Candidats</p>
        <p className="mt-2 text-3xl font-semibold text-gray-900">{totalCandidates}</p>
      </div>
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <p className="text-sm font-medium text-gray-600">Conformité moyenne</p>
        <p className="mt-2 text-3xl font-semibold text-gray-900">
          {averageComplianceScore !== null
            ? `${averageComplianceScore.toFixed(1)}%`
            : "N/A"}
        </p>
      </div>
    </div>
  );
}
