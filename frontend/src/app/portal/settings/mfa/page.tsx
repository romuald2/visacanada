"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/components/auth/AuthProvider";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface MFAStatus {
  enabled: boolean;
  available: boolean;
  backup_codes_remaining: number | null;
}

interface MFASetupData {
  secret: string;
  qr_code_svg: string;
  backup_codes: string[];
}

export default function MFAPage() {
  const { token } = useAuth();

  const [status, setStatus] = useState<MFAStatus | null>(null);
  const [setupData, setSetupData] = useState<MFASetupData | null>(null);
  const [verifyCode, setVerifyCode] = useState("");
  const [disablePassword, setDisablePassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/auth/mfa/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        setStatus(await response.json());
      }
    } catch {
      // Silent fail
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      fetchStatus();
    }
  }, [token, fetchStatus]);

  const handleSetup = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/auth/mfa/setup`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        setSetupData(await response.json());
      } else {
        const data = await response.json();
        setError(data.detail || "Échec de la configuration MFA");
      }
    } catch {
      setError("Erreur réseau");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifySetup = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(`${API_URL}/auth/mfa/verify-setup`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ code: verifyCode }),
      });

      if (response.ok) {
        setSuccess("MFA activé avec succès !");
        setSetupData(null);
        setVerifyCode("");
        await fetchStatus();
      } else {
        const data = await response.json();
        setError(data.detail || "Code invalide");
      }
    } catch {
      setError("Erreur réseau");
    } finally {
      setLoading(false);
    }
  };

  const handleDisable = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(`${API_URL}/auth/mfa/disable`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ password: disablePassword }),
      });

      if (response.ok) {
        setSuccess("MFA désactivé");
        setDisablePassword("");
        await fetchStatus();
      } else {
        const data = await response.json();
        setError(data.detail || "Échec de la désactivation");
      }
    } catch {
      setError("Erreur réseau");
    } finally {
      setLoading(false);
    }
  };

  if (!status) {
    return (
      <div className="container mx-auto py-8">
        <p>Chargement...</p>
      </div>
    );
  }

  if (!status.available) {
    return (
      <div className="container mx-auto py-8 max-w-2xl">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-800">
            ⚠️ La MFA n&apos;est disponible que pour les rôles admin et consultant.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          🛡️ Authentification multi-facteurs (MFA)
        </h1>
        <p className="text-gray-600 mt-2">
          Sécurisez votre compte avec un code TOTP généré par votre application d&apos;authentification
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
          <p className="text-red-800">⚠️ {error}</p>
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
          <p className="text-green-800">✓ {success}</p>
        </div>
      )}

      {/* Status Card */}
      <div className="bg-white border rounded-lg shadow-sm p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">État actuel</h2>
        <div className="flex items-center gap-3">
          <span className="font-medium">MFA :</span>
          {status.enabled ? (
            <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
              ✓ Activé
            </span>
          ) : (
            <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm font-medium">
              Désactivé
            </span>
          )}
        </div>
        {status.enabled && status.backup_codes_remaining !== null && (
          <p className="text-sm text-gray-600 mt-2">
            🔑 {status.backup_codes_remaining} code(s) de secours restant(s)
          </p>
        )}
      </div>

      {/* Setup Flow */}
      {!status.enabled && !setupData && (
        <div className="bg-white border rounded-lg shadow-sm p-6">
          <h2 className="text-xl font-semibold mb-2">Activer la MFA</h2>
          <p className="text-gray-600 mb-4">
            La MFA ajoute une couche de sécurité supplémentaire en exigeant un code TOTP depuis
            votre application d&apos;authentification (Google Authenticator, Authy, 1Password, etc.)
          </p>
          <button
            onClick={handleSetup}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            Configurer la MFA
          </button>
        </div>
      )}

      {/* QR Code & Backup Codes */}
      {setupData && (
        <div className="bg-white border rounded-lg shadow-sm p-6">
          <h2 className="text-xl font-semibold mb-2">Étape 1 : Scanner le QR code</h2>
          <p className="text-gray-600 mb-4">
            Scannez ce code avec votre application d&apos;authentification
          </p>

          {/* QR Code */}
          <div
            className="flex justify-center p-4 bg-white rounded border mb-6"
            dangerouslySetInnerHTML={{ __html: setupData.qr_code_svg }}
          />

          {/* Manual Secret */}
          <div className="mb-6">
            <label className="block text-sm font-medium mb-2">
              Ou entrez manuellement ce secret :
            </label>
            <code className="block p-2 bg-gray-100 rounded text-sm break-all">
              {setupData.secret}
            </code>
          </div>

          {/* Backup Codes */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <p className="font-medium mb-2">🔑 Codes de secours</p>
            <p className="text-sm text-gray-700 mb-3">
              Sauvegardez-les dans un endroit sûr. Chaque code peut être utilisé une fois si vous
              perdez accès à votre application d&apos;authentification.
            </p>
            <div className="grid grid-cols-2 gap-2">
              {setupData.backup_codes.map((code, i) => (
                <code key={i} className="p-2 bg-white rounded text-center font-mono text-sm">
                  {code}
                </code>
              ))}
            </div>
          </div>

          {/* Verify */}
          <form onSubmit={handleVerifySetup} className="space-y-4 pt-4 border-t">
            <div>
              <label htmlFor="verify-code" className="block text-sm font-medium mb-2">
                Étape 2 : Entrez le code à 6 chiffres depuis votre application
              </label>
              <input
                id="verify-code"
                type="text"
                placeholder="000000"
                value={verifyCode}
                onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                maxLength={6}
                required
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <button
              type="submit"
              disabled={loading || verifyCode.length !== 6}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              Vérifier et activer
            </button>
          </form>
        </div>
      )}

      {/* Disable MFA */}
      {status.enabled && (
        <div className="bg-white border border-red-200 rounded-lg shadow-sm p-6">
          <h2 className="text-xl font-semibold text-red-600 mb-2">Désactiver la MFA</h2>
          <p className="text-gray-600 mb-4">
            Entrez votre mot de passe pour désactiver l&apos;authentification multi-facteurs
          </p>
          <form onSubmit={handleDisable} className="space-y-4">
            <div>
              <label htmlFor="password" className="block text-sm font-medium mb-2">
                Mot de passe
              </label>
              <input
                id="password"
                type="password"
                value={disablePassword}
                onChange={(e) => setDisablePassword(e.target.value)}
                required
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
            >
              Désactiver la MFA
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
