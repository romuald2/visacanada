"use client";

import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { AlertConfigForm } from "@/components/alerts/AlertConfigForm";

export default function AlertConfigPage() {
  const params = useParams();
  const router = useRouter();
  const dossierId = Number(params.dossierId);

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
        <button
          onClick={() => router.back()}
          className="mb-6 flex items-center gap-2 text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="h-5 w-5" aria-hidden="true" />
          Retour
        </button>

        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">
            Configuration des alertes
          </h1>
          <p className="mt-2 text-gray-600">
            Dossier #{dossierId}
          </p>
        </div>

        <AlertConfigForm dossierId={dossierId} />
      </div>
    </div>
  );
}
