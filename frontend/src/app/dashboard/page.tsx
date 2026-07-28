"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuth } from "@/components/auth/AuthProvider";
import { AppShell } from "@/components/layout/AppShell";
import { UpcomingDeadlines } from "@/components/deadlines/UpcomingDeadlines";
import { DossierList } from "@/components/dossiers/DossierList";
import { getDossiers, getUpcomingDeadlines } from "@/lib/api";
import type { DossierPage, UpcomingAlert } from "@/lib/types";

function DashboardContent() {
  const { getValidToken } = useAuth();

  const [alerts, setAlerts] = useState<UpcomingAlert[]>([]);
  const [dossiers, setDossiers] = useState<DossierPage | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (targetPage: number, signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      try {
        const token = (await getValidToken()) ?? undefined;
        const [upcoming, dossierPage] = await Promise.all([
          getUpcomingDeadlines({ token, signal, days: 30 }),
          getDossiers({ token, signal, page: targetPage, size: 10 }),
        ]);
        if (signal?.aborted) return;
        setAlerts(upcoming.items);
        setDossiers(dossierPage);
      } catch (err) {
        if (signal?.aborted) return;
        setError("Impossible de charger les données. Réessayez.");
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    [getValidToken],
  );

  useEffect(() => {
    const controller = new AbortController();
    load(page, controller.signal);
    return () => controller.abort();
  }, [page, load]);

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
      <div className="order-2 lg:order-1">
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
      <div className="order-1 lg:order-2">
        <UpcomingDeadlines items={alerts} windowDays={30} />
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <RequireAuth>
      <AppShell title="Tableau de bord">
        <DashboardContent />
      </AppShell>
    </RequireAuth>
  );
}
