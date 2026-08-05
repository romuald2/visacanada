import { useEffect, useState } from "react";

interface DossierFiltersProps {
  status: string;
  programId: number | undefined;
  onStatusChange: (status: string) => void;
  onProgramChange: (programId: number | undefined) => void;
}

interface Program {
  id: number;
  name: string;
  category: string;
}

const STATUS_OPTIONS = [
  { value: "", label: "Tous les statuts" },
  { value: "nouveau", label: "Nouveau" },
  { value: "en_cours", label: "En cours" },
  { value: "documents_manquants", label: "Documents manquants" },
  { value: "en_revision", label: "En révision" },
  { value: "soumis", label: "Soumis" },
  { value: "approuve", label: "Approuvé" },
  { value: "refuse", label: "Refusé" },
  { value: "archive", label: "Archivé" },
];

export function DossierFilters({
  status,
  programId,
  onStatusChange,
  onProgramChange,
}: DossierFiltersProps) {
  const [programs, setPrograms] = useState<Program[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    fetch("http://localhost:8000/programs/", {
      signal: controller.signal,
    })
      .then((r) => r.json())
      .then((data) => {
        if (!controller.signal.aborted) {
          setPrograms(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  return (
    <div className="flex flex-wrap gap-4 rounded-lg border border-gray-200 bg-white p-4">
      <div className="flex-1 min-w-[200px]">
        <label
          htmlFor="status-filter"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          Statut
        </label>
        <select
          id="status-filter"
          value={status}
          onChange={(e) => onStatusChange(e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex-1 min-w-[200px]">
        <label
          htmlFor="program-filter"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          Programme
        </label>
        <select
          id="program-filter"
          value={programId ?? ""}
          onChange={(e) =>
            onProgramChange(e.target.value ? Number(e.target.value) : undefined)
          }
          disabled={loading}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
        >
          <option value="">Tous les programmes</option>
          {programs.map((prog) => (
            <option key={prog.id} value={prog.id}>
              {prog.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
