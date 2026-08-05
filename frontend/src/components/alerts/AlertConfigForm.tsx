"use client";

import { useEffect, useState } from "react";
import { Settings } from "lucide-react";
import { getAlertConfig, updateAlertConfig } from "@/lib/api";
import type { AlertConfig } from "@/lib/types";

interface AlertConfigFormProps {
  dossierId: number;
}

const ALERT_TYPES = [
  { value: "passport_expiring", label: "Passeport expirant" },
  { value: "medical_expiring", label: "Examen médical expirant" },
  { value: "language_expiring", label: "Test de langue expirant" },
  { value: "express_entry_round", label: "Ronde Express Entry" },
  { value: "policy_change", label: "Changement de politique" },
  { value: "submission_deadline", label: "Date limite de soumission" },
  { value: "ita_response", label: "Réponse ITA" },
  { value: "biometrics", label: "Biométrie" },
  { value: "ppr", label: "Demande de passeport" },
  { value: "medical_request", label: "Demande d'examen médical" },
  { value: "permit_expiring", label: "Permis expirant" },
];

export function AlertConfigForm({ dossierId }: AlertConfigFormProps) {
  const [config, setConfig] = useState<AlertConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getAlertConfig(dossierId);
        setConfig(data);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Erreur de chargement";
        setError(message);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [dossierId]);

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const updated = await updateAlertConfig(dossierId, {
        is_enabled: config.is_enabled,
        enabled_types: config.enabled_types,
        channels: config.channels,
      });
      setConfig(updated);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur de sauvegarde";
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="text-sm text-gray-600">Chargement de la configuration...</div>;
  }

  if (error && !config) {
    return <div className="text-sm text-red-600">{error}</div>;
  }

  if (!config) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Settings className="h-6 w-6 text-gray-600" aria-hidden="true" />
        <h3 className="text-lg font-semibold text-gray-900">Configuration des alertes</h3>
      </div>

      {/* Global Enable/Disable */}
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
        <label className="flex items-center gap-3">
          <input
            type="checkbox"
            checked={config.is_enabled}
            onChange={(e) => setConfig({ ...config, is_enabled: e.target.checked })}
            className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <div>
            <div className="font-medium text-gray-900">Activer les alertes pour ce dossier</div>
            <div className="text-sm text-gray-600">
              Recevoir des notifications automatiques pour les événements importants
            </div>
          </div>
        </label>
      </div>

      {/* Alert Types */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <h4 className="mb-4 font-medium text-gray-900">Types d&apos;alertes</h4>
        <div className="space-y-3">
          {ALERT_TYPES.map((type) => (
            <label key={type.value} className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={config.enabled_types[type.value] !== false}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    enabled_types: {
                      ...config.enabled_types,
                      [type.value]: e.target.checked,
                    },
                  })
                }
                disabled={!config.is_enabled}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
              />
              <span className={`text-sm ${config.is_enabled ? "text-gray-700" : "text-gray-400"}`}>
                {type.label}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Channels */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <h4 className="mb-4 font-medium text-gray-900">Canaux de notification</h4>
        <div className="space-y-3">
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={config.channels.dashboard}
              onChange={(e) =>
                setConfig({
                  ...config,
                  channels: { ...config.channels, dashboard: e.target.checked },
                })
              }
              disabled={!config.is_enabled}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
            />
            <div>
              <div className={`font-medium ${config.is_enabled ? "text-gray-900" : "text-gray-400"}`}>
                Tableau de bord
              </div>
              <div className="text-sm text-gray-500">
                Afficher les alertes dans l&apos;interface web
              </div>
            </div>
          </label>
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={config.channels.email}
              onChange={(e) =>
                setConfig({
                  ...config,
                  channels: { ...config.channels, email: e.target.checked },
                })
              }
              disabled={!config.is_enabled}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
            />
            <div>
              <div className={`font-medium ${config.is_enabled ? "text-gray-900" : "text-gray-400"}`}>
                Email
              </div>
              <div className="text-sm text-gray-500">
                Recevoir les alertes par email
              </div>
            </div>
          </label>
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={config.channels.whatsapp}
              onChange={(e) =>
                setConfig({
                  ...config,
                  channels: { ...config.channels, whatsapp: e.target.checked },
                })
              }
              disabled={!config.is_enabled}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
            />
            <div>
              <div className={`font-medium ${config.is_enabled ? "text-gray-900" : "text-gray-400"}`}>
                WhatsApp
              </div>
              <div className="text-sm text-gray-500">
                Recevoir les alertes critiques par WhatsApp
              </div>
            </div>
          </label>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded-md bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 disabled:bg-gray-400"
        >
          {saving ? "Enregistrement..." : "Enregistrer"}
        </button>
        {success && (
          <span className="text-sm font-medium text-green-600">✓ Configuration enregistrée</span>
        )}
        {error && <span className="text-sm text-red-600">{error}</span>}
      </div>
    </div>
  );
}
