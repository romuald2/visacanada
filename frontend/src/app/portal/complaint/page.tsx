"use client";

import { useState } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { AlertCircle, Send, Loader2 } from "lucide-react";

export default function ComplaintPage() {
  const { token } = useAuth();
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || loading) return;

    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/portal/complaint`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ subject, description }),
        }
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Erreur lors de la soumission");
      }

      setSuccess(true);
      setSubject("");
      setDescription("");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur de soumission";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-3xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Déposer une plainte</h1>
        <p className="text-sm text-gray-500 mt-1">
          Conformément à la PIPEDA (Principe 10), vous pouvez contester le traitement de vos données personnelles
        </p>
      </div>

      <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 mb-6">
        <div className="flex gap-3">
          <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">Vos droits PIPEDA</p>
            <p>
              Vous avez le droit de déposer une plainte si vous estimez que vos données personnelles
              ont été mal utilisées, que vous n&apos;avez pas pu y accéder, ou que vos demandes de
              correction n&apos;ont pas été traitées de manière appropriée.
            </p>
          </div>
        </div>
      </div>

      {success && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4 mb-6">
          <p className="text-sm text-green-800">
            ✅ Votre plainte a été soumise avec succès. Un administrateur la traitera sous peu et vous
            contactera par email.
          </p>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 mb-6">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <div className="space-y-4">
            <div>
              <label htmlFor="subject" className="block text-sm font-medium mb-1">
                Sujet de la plainte
              </label>
              <input
                id="subject"
                type="text"
                value={subject}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setSubject(e.target.value)
                }
                placeholder="Ex: Accès refusé à mes données personnelles"
                required
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label htmlFor="description" className="block text-sm font-medium mb-1">
                Description détaillée
              </label>
              <textarea
                id="description"
                value={description}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                  setDescription(e.target.value)
                }
                placeholder="Décrivez votre plainte en détail : quelle donnée est concernée, quelle action vous attendiez, pourquoi vous estimez que vos droits n'ont pas été respectés..."
                rows={8}
                required
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Envoi en cours...
            </>
          ) : (
            <>
              <Send className="h-4 w-4" />
              Soumettre la plainte
            </>
          )}
        </button>
      </form>

      <div className="mt-8 rounded-lg border border-gray-200 bg-gray-50 p-4">
        <h2 className="font-medium mb-2">Autre option de plainte</h2>
        <p className="text-sm text-gray-600 mb-2">
          Vous pouvez également déposer une plainte directement auprès du Commissaire à la vie privée du Canada :
        </p>
        <ul className="text-sm text-gray-600 space-y-1">
          <li>
            • Site web :{" "}
            <a
              href="https://www.priv.gc.ca"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline"
            >
              www.priv.gc.ca
            </a>
          </li>
          <li>• Téléphone : 1-800-282-1376</li>
          <li>• Email : info@priv.gc.ca</li>
        </ul>
      </div>
    </div>
  );
}
