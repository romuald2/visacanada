"use client";

import { useState } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { Download, Loader2, FileJson } from "lucide-react";

export default function ExportPage() {
  const { token } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    if (!token || loading) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/portal/export`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Erreur lors de l'export");
      }

      // Télécharger le fichier
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `visacanada_export_${Date.now()}.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur d'export";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-3xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Exporter mes données</h1>
        <p className="text-sm text-gray-500 mt-1">
          Téléchargez une copie complète de vos données personnelles (PIPEDA Principe 9)
        </p>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-6 mb-6">
        <div className="flex gap-4 items-start">
          <FileJson className="h-12 w-12 text-blue-600 flex-shrink-0" />
          <div className="flex-1">
            <h2 className="text-lg font-semibold mb-2">Export JSON complet</h2>
            <p className="text-sm text-gray-600 mb-4">
              Le fichier exporté contient toutes vos données personnelles conservées par VisaCanada :
            </p>
            <ul className="text-sm text-gray-600 space-y-1 mb-4 list-disc list-inside">
              <li>Informations de compte (email, nom, rôle)</li>
              <li>Profil candidat (coordonnées, passeport, nationalité)</li>
              <li>Dossiers d&apos;immigration (statuts, dates, notes)</li>
              <li>Liste des documents téléversés (métadonnées, pas le contenu des fichiers)</li>
            </ul>
            <p className="text-xs text-gray-500 italic">
              Note : Les fichiers eux-mêmes (PDFs, images) ne sont pas inclus dans l&apos;export
              pour des raisons de taille. Vous pouvez les télécharger individuellement depuis votre
              portail.
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 mb-6">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      <button
        onClick={handleExport}
        disabled={loading}
        className="w-full rounded-md bg-blue-600 px-4 py-3 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" />
            Export en cours...
          </>
        ) : (
          <>
            <Download className="h-5 w-5" />
            Télécharger mes données (JSON)
          </>
        )}
      </button>

      <div className="mt-8 rounded-lg border border-blue-200 bg-blue-50 p-4">
        <h3 className="font-medium text-blue-900 mb-2">Vos droits PIPEDA</h3>
        <p className="text-sm text-blue-800 mb-2">
          Conformément au Principe 9 de la PIPEDA, vous avez le droit d&apos;accéder à vos données
          personnelles et d&apos;en obtenir une copie.
        </p>
        <p className="text-sm text-blue-800">
          Si vous constatez une erreur dans vos données, vous pouvez les corriger directement via
          votre{" "}
          <a href="/portal/profile" className="underline font-medium">
            profil
          </a>
          . Pour toute question, contactez{" "}
          <a href="mailto:privacy@visacanada.com" className="underline font-medium">
            privacy@visacanada.com
          </a>
          .
        </p>
      </div>

      <div className="mt-6 rounded-lg border border-gray-200 bg-gray-50 p-4">
        <h3 className="font-medium mb-2">Format du fichier</h3>
        <p className="text-sm text-gray-600 mb-2">
          Le fichier exporté est au format JSON (JavaScript Object Notation), un format standard
          lisible par la plupart des applications.
        </p>
        <p className="text-sm text-gray-600">
          Vous pouvez l&apos;ouvrir avec n&apos;importe quel éditeur de texte (Notepad, TextEdit)
          ou l&apos;importer dans un tableur comme Excel pour une visualisation structurée.
        </p>
      </div>
    </div>
  );
}
