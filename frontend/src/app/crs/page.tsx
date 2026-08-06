"use client";

import { useState } from "react";
import { Calculator } from "lucide-react";
import { CRSForm } from "@/components/crs/CRSForm";
import { CRSResultDisplay } from "@/components/crs/CRSResultDisplay";
import { calculateCRS } from "@/lib/api";
import type { CRSCalculateRequest, CRSResult } from "@/lib/types";

export default function CRSCalculatorPage() {
  const [result, setResult] = useState<CRSResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (data: CRSCalculateRequest) => {
    setLoading(true);
    setError(null);
    try {
      const res = await calculateCRS(data);
      setResult(res);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur lors du calcul du score CRS";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Calculator className="h-8 w-8 text-blue-600" aria-hidden="true" />
            <h1 className="text-3xl font-bold text-gray-900">Calculateur CRS</h1>
          </div>
          <p className="text-gray-600">
            Calculez votre score du Système de classement global (CRS) pour l&apos;Entrée express
          </p>
        </div>

        {error && (
          <div
            className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4"
            role="alert"
          >
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {result ? (
          <div>
            <div className="mb-6 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">Vos résultats</h2>
              <button
                onClick={handleReset}
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                Nouveau calcul
              </button>
            </div>
            <CRSResultDisplay result={result} />
          </div>
        ) : (
          <CRSForm onSubmit={handleSubmit} loading={loading} />
        )}
      </div>
    </div>
  );
}
