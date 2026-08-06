"use client";

import { useEffect, useState } from "react";
import { BarChart3, TrendingUp, Clock, DollarSign } from "lucide-react";
import {
  getAnalyticsOverview,
  getSuccessRate,
  getProcessingTime,
  getRevenue,
  getWorkloadForecast,
} from "@/lib/api";
import { ApprovalRateChart } from "@/components/analytics/ApprovalRateChart";
import { ProcessingTimeChart } from "@/components/analytics/ProcessingTimeChart";
import { RevenueChart } from "@/components/analytics/RevenueChart";
import type {
  AnalyticsOverview,
  SuccessRateByProgram,
  ProcessingTimeData,
  RevenueData,
  WorkloadForecast,
} from "@/lib/types";

export default function AnalyticsPage() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [successRate, setSuccessRate] = useState<SuccessRateByProgram[]>([]);
  const [processingTime, setProcessingTime] = useState<ProcessingTimeData | null>(null);
  const [revenue, setRevenue] = useState<RevenueData | null>(null);
  const [forecast, setForecast] = useState<WorkloadForecast | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [overviewData, successData, processData, revenueData, forecastData] =
          await Promise.all([
            getAnalyticsOverview(),
            getSuccessRate(),
            getProcessingTime(),
            getRevenue({ period: "month" }),
            getWorkloadForecast(),
          ]);
        setOverview(overviewData);
        setSuccessRate(successData);
        setProcessingTime(processData);
        setRevenue(revenueData);
        setForecast(forecastData);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Erreur de chargement";
        setError(message);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-gray-600">Chargement...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-8 flex items-center gap-3">
          <BarChart3 className="h-8 w-8 text-blue-600" aria-hidden="true" />
          <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
        </div>

        {/* Overview Cards */}
        {overview && (
          <div className="mb-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="rounded-full bg-blue-100 p-3">
                  <TrendingUp className="h-6 w-6 text-blue-600" aria-hidden="true" />
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-500">Dossiers actifs</div>
                  <div className="text-2xl font-bold text-gray-900">{overview.active}</div>
                </div>
              </div>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="rounded-full bg-green-100 p-3">
                  <BarChart3 className="h-6 w-6 text-green-600" aria-hidden="true" />
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-500">Approuvés</div>
                  <div className="text-2xl font-bold text-gray-900">{overview.approved}</div>
                </div>
              </div>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="rounded-full bg-red-100 p-3">
                  <BarChart3 className="h-6 w-6 text-red-600" aria-hidden="true" />
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-500">Refusés</div>
                  <div className="text-2xl font-bold text-gray-900">{overview.refused}</div>
                </div>
              </div>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="rounded-full bg-gray-100 p-3">
                  <BarChart3 className="h-6 w-6 text-gray-600" aria-hidden="true" />
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-500">Archivés</div>
                  <div className="text-2xl font-bold text-gray-900">{overview.archived}</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Charts */}
        <div className="space-y-6">
          {/* Approval Rate */}
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">
              Taux d&apos;approbation par programme
            </h2>
            <ApprovalRateChart data={successRate} />
          </div>

          {/* Processing Time */}
          {processingTime && (
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              <div className="mb-4 flex items-center gap-2">
                <Clock className="h-5 w-5 text-gray-600" aria-hidden="true" />
                <h2 className="text-lg font-semibold text-gray-900">
                  Temps de traitement par programme
                </h2>
              </div>
              <ProcessingTimeChart data={processingTime} />
            </div>
          )}

          {/* Revenue */}
          {revenue && (
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              <div className="mb-4 flex items-center gap-2">
                <DollarSign className="h-5 w-5 text-gray-600" aria-hidden="true" />
                <h2 className="text-lg font-semibold text-gray-900">
                  Revenus par mois
                </h2>
              </div>
              <RevenueChart data={revenue} />
            </div>
          )}

          {/* Workload Forecast */}
          {forecast && (
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold text-gray-900">
                Prévisions de charge de travail
              </h2>
              <div className="grid gap-4 sm:grid-cols-2 mb-6">
                <div className="rounded-lg bg-blue-50 p-4">
                  <div className="text-sm font-medium text-blue-700">
                    Décisions attendues (30 jours)
                  </div>
                  <div className="text-2xl font-bold text-blue-900">
                    {forecast.expected_decisions_30d}
                  </div>
                </div>
                <div className="rounded-lg bg-purple-50 p-4">
                  <div className="text-sm font-medium text-purple-700">
                    Décisions attendues (90 jours)
                  </div>
                  <div className="text-2xl font-bold text-purple-900">
                    {forecast.expected_decisions_90d}
                  </div>
                </div>
              </div>
              {forecast.by_program.length > 0 && (
                <div>
                  <h3 className="mb-3 text-sm font-medium text-gray-700">Par programme</h3>
                  <div className="space-y-2">
                    {forecast.by_program.map((prog) => (
                      <div
                        key={prog.program_id}
                        className="flex items-center justify-between rounded-lg border border-gray-100 p-3"
                      >
                        <span className="text-sm text-gray-700">{prog.program_name}</span>
                        <span className="font-semibold text-gray-900">{prog.count} dossiers</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
