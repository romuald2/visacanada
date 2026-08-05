"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuth } from "@/components/auth/AuthProvider";
import { AppShell } from "@/components/layout/AppShell";
import { UpcomingDeadlines } from "@/components/deadlines/UpcomingDeadlines";
import { CriticalBadge } from "@/components/deadlines/CriticalBadge";
import { DossierList } from "@/components/dossiers/DossierList";
import { DossierFilters } from "@/components/dossiers/DossierFilters";
import { StatusChart } from "@/components/dashboard/StatusChart";
import { StatsCards } from "@/components/dashboard/StatsCards";
import { getDossiers, getUpcomingDeadlines, getDashboardOverview } from "@/lib/api";
import type { DossierPage, UpcomingAlert, DashboardOverview } from "@/lib/types";

function DashboardContent() {
  const { getValidToken } = useAuth();

  const [alerts, setAlerts] = useState<UpcomingAlert[]>([]);
  const [dossiers, setDossiers] = useState<DossierPage | null>(null);
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [programFilter, setProgramFilter] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (targetPage: number, signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      try {
        const token = (await getValidToken()) ?? undefined;
        const [upcoming, dossierPage, overviewData] = await Promise.all([
          getUpcomingDeadlines({ token, signal, days: 30 }),
          getDossiers({
            token,
            signal,
            page: targetPage,
            size: 10,
            status: statusFilter || undefined,
            program_id: programFilter,
          }),
          getDashboardOverview({ token, signal }),
        ]);
        if (signal?.aborted) return;
        setAlerts(upcoming.items);
        setDossiers(dossierPage);
        setOverview(overviewData);
      } catch {
        if (signal?.aborted) return;
        setError("Impossible de charger les données. Réessayez.");
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    [getValidToken, statusFilter, programFilter],
  );

  useEffect(() => {
    const controller = new AbortController();
    load(page, controller.signal);
    return () => controller.abort();
  }, [page, load]);

  return (
    <AppShell
      title="Tableau de bord"
      headerExtra={<CriticalBadge items={alerts} />}
    >
      <div className="space-y-6">
        {/* Stats cards */}
        {overview && (
          <StatsCards
            totalDossiers={overview.total_dossiers}
            totalCandidates={overview.total_candidates}
            averageComplianceScore={overview.average_compliance_score}
          />
        )}

        <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
          {/* Main column: status chart + filters + dossier list */}
          <div className="order-2 space-y-6 lg:order-1">
            {overview && <StatusChart byStatus={overview.by_status} />}
            <DossierFilters
              status={statusFilter}
              programId={programFilter}
              onStatusChange={(s) => {
                setStatusFilter(s);
                setPage(1);
              }}
              onProgramChange={(p) => {
                setProgramFilter(p);
                setPage(1);
              }}
            />
            <DossierList
              items={dossiers?.items ?? []}
              total={dossiers?.total ?? 0}
              page={dossiers?.page ?? page}
              pages={dossiers?.pages ?? 0}
              loading={loading}
              error={error}
              onPageChange={setPage}
            />
          </div>

          {/* Sidebar: upcoming deadlines */}
          <div className="order-1 lg:order-2">
            <UpcomingDeadlines items={alerts} windowDays={30} />
          </div>
        </div>
      </div>
    </AppShell>
  );
}

export default function DashboardPage() {
  return (
    <RequireAuth>
      <DashboardContent />
    </RequireAuth>
  );
}
