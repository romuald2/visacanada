"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, FileText, Upload, CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import { getMyDossier, getMyDossierDocuments, uploadMyDocument } from "@/lib/api";
import type { PortalDossierDetail, DossierDocuments } from "@/lib/types";

const STATUS_COLORS: Record<string, string> = {
  nouveau: "bg-slate-100 text-slate-700",
  en_cours: "bg-blue-100 text-blue-700",
  documents_manquants: "bg-amber-100 text-amber-700",
  en_revision: "bg-purple-100 text-purple-700",
  soumis: "bg-indigo-100 text-indigo-700",
  approuve: "bg-green-100 text-green-700",
  refuse: "bg-red-100 text-red-700",
  archive: "bg-gray-100 text-gray-700",
};

const DOC_STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  uploaded: {
    label: "En attente",
    color: "text-blue-600",
    icon: <AlertCircle className="h-5 w-5" aria-hidden="true" />,
  },
  approved: {
    label: "Approuvé",
    color: "text-green-600",
    icon: <CheckCircle2 className="h-5 w-5" aria-hidden="true" />,
  },
  rejected: {
    label: "Rejeté",
    color: "text-red-600",
    icon: <XCircle className="h-5 w-5" aria-hidden="true" />,
  },
  expired: {
    label: "Expiré",
    color: "text-gray-600",
    icon: <XCircle className="h-5 w-5" aria-hidden="true" />,
  },
};

export default function DossierDetailPage() {
  const params = useParams();
  const router = useRouter();
  const dossierId = Number(params.id);

  const [dossier, setDossier] = useState<PortalDossierDetail | null>(null);
  const [documents, setDocuments] = useState<DossierDocuments | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [dossierData, docsData] = await Promise.all([
        getMyDossier(dossierId),
        getMyDossierDocuments(dossierId),
      ]);
      setDossier(dossierData);
      setDocuments(docsData);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur de chargement";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [dossierId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleFileUpload = async (documentType: string, file: File) => {
    setUploading(true);
    setUploadError(null);
    try {
      await uploadMyDocument(dossierId, documentType, file);
      await loadData(); // Reload to show the new document
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur d'upload";
      setUploadError(message);
    } finally {
      setUploading(false);
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

  if (!dossier || !documents) {
    return null;
  }

  const statusColor = STATUS_COLORS[dossier.status] || "bg-gray-100 text-gray-700";

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
        <button
          onClick={() => router.back()}
          className="mb-6 flex items-center gap-2 text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="h-5 w-5" aria-hidden="true" />
          Retour
        </button>

        {/* Header */}
        <div className="mb-6">
          <div className="mb-2 flex items-center gap-3">
            <FileText className="h-8 w-8 text-blue-600" aria-hidden="true" />
            <h1 className="text-3xl font-bold text-gray-900">
              Dossier {dossier.reference_number || `#${dossier.id}`}
            </h1>
          </div>
          <span className={`inline-block rounded-full px-3 py-1 text-sm font-medium ${statusColor}`}>
            {dossier.status_label.fr}
          </span>
        </div>

        {/* Progress */}
        <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6">
          <div className="mb-2 flex items-center justify-between">
            <span className="font-medium text-gray-900">Progression</span>
            <span className="text-gray-600">{dossier.progress}%</span>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-gray-200">
            <div
              className="h-full bg-blue-600 transition-all duration-300"
              style={{ width: `${dossier.progress}%` }}
            />
          </div>
        </div>

        {/* Program & Dates */}
        <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Informations</h2>
          <dl className="space-y-3">
            {dossier.program && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Programme</dt>
                <dd className="mt-1 text-gray-900">{dossier.program.name}</dd>
              </div>
            )}
            {dossier.submitted_at && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Date de soumission</dt>
                <dd className="mt-1 text-gray-900">
                  {new Date(dossier.submitted_at).toLocaleDateString("fr-CA")}
                </dd>
              </div>
            )}
            {dossier.decision_at && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Date de décision</dt>
                <dd className="mt-1 text-gray-900">
                  {new Date(dossier.decision_at).toLocaleDateString("fr-CA")}
                </dd>
              </div>
            )}
          </dl>
        </div>

        {/* Upload Error */}
        {uploadError && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
            {uploadError}
          </div>
        )}

        {/* Provided Documents */}
        {documents.provided.length > 0 && (
          <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">
              Documents fournis ({documents.provided_count})
            </h2>
            <div className="space-y-3">
              {documents.provided.map((doc) => {
                const config = DOC_STATUS_CONFIG[doc.status] || DOC_STATUS_CONFIG.uploaded;
                return (
                  <div
                    key={doc.id}
                    className="flex items-start justify-between rounded-lg border border-gray-100 p-4"
                  >
                    <div className="flex items-start gap-3">
                      <FileText className="mt-0.5 h-5 w-5 text-gray-400" aria-hidden="true" />
                      <div>
                        <div className="font-medium text-gray-900">{doc.file_name}</div>
                        <div className="text-sm text-gray-500">{doc.document_type}</div>
                        {doc.uploaded_at && (
                          <div className="text-xs text-gray-400">
                            Uploadé le {new Date(doc.uploaded_at).toLocaleDateString("fr-CA")}
                          </div>
                        )}
                        {doc.rejection_reason && (
                          <div className="mt-1 text-sm text-red-600">
                            Raison du rejet: {doc.rejection_reason}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className={`flex items-center gap-1.5 ${config.color}`}>
                      {config.icon}
                      <span className="text-sm font-medium">{config.label}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Missing Documents */}
        {documents.missing.length > 0 && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-6">
            <h2 className="mb-4 text-lg font-semibold text-amber-900">
              Documents manquants ({documents.missing_count})
            </h2>
            <div className="space-y-4">
              {documents.missing.map((doc, idx) => (
                <div key={idx} className="rounded-lg border border-amber-200 bg-white p-4">
                  <div className="mb-3">
                    <div className="font-medium text-gray-900">{doc.document_name}</div>
                    <div className="text-sm text-gray-600">{doc.document_type}</div>
                    {doc.description && (
                      <div className="mt-1 text-sm text-gray-500">{doc.description}</div>
                    )}
                    <div className="mt-1">
                      <span
                        className={`text-xs font-medium ${
                          doc.priority === "required"
                            ? "text-red-600"
                            : doc.priority === "recommended"
                              ? "text-amber-600"
                              : "text-gray-600"
                        }`}
                      >
                        {doc.priority === "required" && "Obligatoire"}
                        {doc.priority === "recommended" && "Recommandé"}
                        {doc.priority === "optional" && "Optionnel"}
                      </span>
                    </div>
                  </div>
                  <label
                    htmlFor={`upload-${idx}`}
                    className="inline-flex cursor-pointer items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-gray-400"
                  >
                    <Upload className="h-4 w-4" aria-hidden="true" />
                    {uploading ? "Upload en cours..." : "Téléverser"}
                  </label>
                  <input
                    type="file"
                    id={`upload-${idx}`}
                    className="hidden"
                    disabled={uploading}
                    accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        handleFileUpload(doc.document_type, file);
                      }
                    }}
                  />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
