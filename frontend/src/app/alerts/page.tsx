"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Bell, AlertTriangle, Info, X, RefreshCw } from "lucide-react";
import { getAlerts, dismissAlert, runAlertScan } from "@/lib/api";
import type { Alert } from "@/lib/types";

const SEVERITY_CONFIG = {
  critical: {
    label: "Critique",
    color: "bg-red-100 text-red-700 border-red-200",
    icon: <AlertTriangle className="h-5 w-5" aria-hidden="true" />,
  },
  warning: {
    label: "Avertissement",
    color: "bg-amber-100 text-amber-700 border-amber-200",
    icon: <AlertTriangle className="h-5 w-5" aria-hidden="true" />,
  },
  info: {
    label: "Information",
    color: "bg-blue-100 text-blue-700 border-blue-200",
    icon: <Info className="h-5 w-5" aria-hidden="true" />,
  },
};

const ALERT_TYPE_LABELS: Record<string, string> = {
  passport_expiring: "Passeport expirant",
  medical_expiring: "Examen médical expirant",
  language_expiring: "Test de langue expirant",
  express_entry_round: "Ronde Express Entry",
  policy_change: "Changement de politique",
  submission_deadline: "Date limite de soumission",
  ita_response: "Réponse ITA",
  biometrics: "Biométrie",
  ppr: "Demande de passeport",
  medical_request: "Demande d'examen médical",
  permit_expiring: "Permis expirant",
};

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [includeDismissed, setIncludeDismissed] = useState(false);
  const [dismissing, setDismissing] = useState<number | null>(null);
  const [scanning, setScanning] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await getAlerts({ include_dismissed: includeDismissed });
      setAlerts(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur de chargement";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [includeDismissed]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDismiss = async (alertId: number) => {
    setDismissing(alertId);
    try {
      await dismissAlert(alertId);
      setAlerts((prev) => prev.map((a) => (a.id === alertId ? { ...a, is_dismissed: true } : a)));
    } catch (err) {
      console.error("Failed to dismiss alert:", err);
    } finally {
      setDismissing(null);
    }
  };

  const handleScan = async () => {
    setScanning(true);
    try {
      await runAlertScan({ deliver: true });
      await load(); // Reload alerts after scan
    } catch (err) {
      console.error("Failed to run scan:", err);
    } finally {
      setScanning(false);
    }
  };

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

  const activeAlerts = alerts.filter((a) => !a.is_dismissed);
  const dismissedAlerts = alerts.filter((a) => a.is_dismissed);

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bell className="h-8 w-8 text-blue-600" aria-hidden="true" />
            <h1 className="text-3xl font-bold text-gray-900">Alertes</h1>
          </div>
          <button
            onClick={handleScan}
            disabled={scanning}
            className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:bg-gray-400"
          >
            <RefreshCw className={`h-4 w-4 ${scanning ? "animate-spin" : ""}`} aria-hidden="true" />
            {scanning ? "Analyse..." : "Lancer une analyse"}
          </button>
        </div>

        {/* Filters */}
        <div className="mb-6 flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={includeDismissed}
              onChange={(e) => setIncludeDismissed(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            Inclure les alertes ignorées
          </label>
        </div>

        {alerts.length === 0 ? (
          <div className="rounded-lg border border-gray-200 bg-white p-12 text-center">
            <Bell className="mx-auto mb-4 h-12 w-12 text-gray-400" aria-hidden="true" />
            <p className="text-gray-600">Aucune alerte</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Active Alerts */}
            {activeAlerts.length > 0 && (
              <div>
                <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
                  Alertes actives ({activeAlerts.length})
                </h2>
                <div className="space-y-3">
                  {activeAlerts.map((alert) => {
                    const config = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.info;
                    return (
                      <div
                        key={alert.id}
                        className={`rounded-lg border p-4 ${config.color}`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-3 flex-1">
                            {config.icon}
                            <div className="flex-1">
                              <div className="mb-1 flex items-center gap-2">
                                <span className="font-semibold">{alert.title}</span>
                                <span className="text-xs font-medium">
                                  {ALERT_TYPE_LABELS[alert.alert_type] || alert.alert_type}
                                </span>
                              </div>
                              <p className="text-sm">{alert.message}</p>
                              {alert.extra_data?.days_left !== undefined &&
                                typeof alert.extra_data.days_left === "number" && (
                                <div className="mt-2 text-xs font-medium">
                                  Dans {alert.extra_data.days_left} jour{alert.extra_data.days_left !== 1 ? "s" : ""}
                                </div>
                              )}
                              <div className="mt-2 flex items-center gap-4 text-xs">
                                <Link
                                  href={`/dossiers/${alert.dossier_id}`}
                                  className="font-medium underline hover:no-underline"
                                >
                                  Voir le dossier #{alert.dossier_id}
                                </Link>
                                {alert.created_at && (
                                  <span className="text-gray-600">
                                    {new Date(alert.created_at).toLocaleDateString("fr-CA")}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                          <button
                            onClick={() => handleDismiss(alert.id)}
                            disabled={dismissing === alert.id}
                            className="ml-4 flex-shrink-0 rounded-md p-1 hover:bg-black/10 disabled:opacity-50"
                            aria-label="Ignorer"
                          >
                            <X className="h-5 w-5" aria-hidden="true" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Dismissed Alerts */}
            {includeDismissed && dismissedAlerts.length > 0 && (
              <div>
                <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
                  Alertes ignorées ({dismissedAlerts.length})
                </h2>
                <div className="space-y-3">
                  {dismissedAlerts.map((alert) => {
                    const config = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.info;
                    return (
                      <div
                        key={alert.id}
                        className="rounded-lg border border-gray-200 bg-gray-50 p-4 opacity-60"
                      >
                        <div className="flex items-start gap-3">
                          {config.icon}
                          <div className="flex-1">
                            <div className="mb-1 flex items-center gap-2">
                              <span className="font-semibold text-gray-700">{alert.title}</span>
                              <span className="text-xs font-medium text-gray-600">
                                {ALERT_TYPE_LABELS[alert.alert_type] || alert.alert_type}
                              </span>
                            </div>
                            <p className="text-sm text-gray-600">{alert.message}</p>
                            <div className="mt-2 text-xs text-gray-500">
                              <Link
                                href={`/dossiers/${alert.dossier_id}`}
                                className="underline hover:no-underline"
                              >
                                Dossier #{alert.dossier_id}
                              </Link>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
