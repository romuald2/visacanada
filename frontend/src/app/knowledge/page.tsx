"use client";

import { useCallback, useEffect, useState } from "react";
import { Upload, Trash2, FileText, Loader2, Plus } from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";
import {
  getKnowledgeDocuments,
  ingestDocument,
  deleteKnowledgeDocument,
} from "@/lib/api";
import type { KnowledgeDocument } from "@/lib/types";

export default function KnowledgePage() {
  const { token } = useAuth();
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Form state
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [sourceType, setSourceType] = useState<string>("manual");
  const [sourceUrl, setSourceUrl] = useState("");
  const [language, setLanguage] = useState("fr");

  const loadDocuments = useCallback(async () => {
    if (!token) return;
    try {
      const data = await getKnowledgeDocuments({ token });
      setDocuments(data);
      setError(null);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Erreur de chargement";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || uploading) return;

    setUploading(true);
    setError(null);

    try {
      await ingestDocument(
        {
          title,
          content,
          source_type: sourceType,
          source_url: sourceUrl || null,
          language,
        },
        { token },
      );

      // Reset form
      setTitle("");
      setContent("");
      setSourceUrl("");
      setShowForm(false);

      // Reload documents
      await loadDocuments();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur d'ingestion";
      setError(message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (documentId: number) => {
    if (!token || !confirm("Supprimer ce document ?")) return;

    try {
      await deleteKnowledgeDocument(documentId, { token });
      await loadDocuments();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Erreur de suppression";
      setError(message);
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">Base de connaissances</h1>
          <p className="text-sm text-gray-500 mt-1">
            Gérer les documents ingérés pour l&apos;assistant RAG
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          {showForm ? (
            "Annuler"
          ) : (
            <span className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Nouveau document
            </span>
          )}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 mb-6">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {showForm && (
        <div className="rounded-lg border border-gray-200 bg-white p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Ingérer un document</h2>
          <form onSubmit={handleIngest} className="space-y-4">
            <div>
              <label htmlFor="title" className="block text-sm font-medium mb-1">
                Titre
              </label>
              <input
                id="title"
                type="text"
                value={title}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setTitle(e.target.value)
                }
                placeholder="Ex: Guide Express Entry 2024"
                required
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label
                htmlFor="content"
                className="block text-sm font-medium mb-1"
              >
                Contenu
              </label>
              <textarea
                id="content"
                value={content}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                  setContent(e.target.value)
                }
                placeholder="Collez le contenu du document ici..."
                rows={10}
                required
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label
                  htmlFor="sourceType"
                  className="block text-sm font-medium mb-1"
                >
                  Type de source
                </label>
                <select
                  id="sourceType"
                  value={sourceType}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                    setSourceType(e.target.value)
                  }
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="ircc_page">Page IRCC</option>
                  <option value="policy">Politique</option>
                  <option value="manual">Manuel</option>
                  <option value="faq">FAQ</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="language"
                  className="block text-sm font-medium mb-1"
                >
                  Langue
                </label>
                <select
                  id="language"
                  value={language}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                    setLanguage(e.target.value)
                  }
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="fr">Français</option>
                  <option value="en">Anglais</option>
                </select>
              </div>
            </div>

            <div>
              <label
                htmlFor="sourceUrl"
                className="block text-sm font-medium mb-1"
              >
                URL source (optionnel)
              </label>
              <input
                id="sourceUrl"
                type="url"
                value={sourceUrl}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setSourceUrl(e.target.value)
                }
                placeholder="https://www.canada.ca/fr/immigration..."
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <button
              type="submit"
              disabled={uploading}
              className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {uploading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Ingestion en cours...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  Ingérer le document
                </>
              )}
            </button>
          </form>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : documents.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-12 text-center">
          <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">
            Aucun document ingéré
          </h3>
          <p className="text-sm text-gray-500 mb-4">
            Commencez par ajouter des documents à la base de connaissances
          </p>
          <button
            onClick={() => setShowForm(true)}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 inline-flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Ajouter un document
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="rounded-lg border border-gray-200 bg-white p-4"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <FileText className="h-4 w-4 text-gray-400 flex-shrink-0" />
                    <h3 className="font-semibold truncate">{doc.title}</h3>
                  </div>
                  <div className="flex flex-wrap gap-4 text-sm text-gray-500">
                    <span>Type: {doc.source_type}</span>
                    <span>Langue: {doc.language}</span>
                    <span>{doc.chunk_count} chunks</span>
                    {doc.updated_at && (
                      <span>
                        Mis à jour:{" "}
                        {new Date(doc.updated_at).toLocaleDateString("fr-CA")}
                      </span>
                    )}
                  </div>
                  {doc.source_url && (
                    <a
                      href={doc.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:underline mt-1 block truncate"
                    >
                      {doc.source_url}
                    </a>
                  )}
                </div>
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="rounded hover:bg-gray-100 p-2 hover:text-red-600"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
