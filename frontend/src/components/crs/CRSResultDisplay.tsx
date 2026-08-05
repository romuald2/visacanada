"use client";

import type { CRSResult } from "@/lib/types";
import { TrendingUp, AlertCircle, CheckCircle2 } from "lucide-react";

interface CRSResultDisplayProps {
  result: CRSResult;
}

export function CRSResultDisplay({ result }: CRSResultDisplayProps) {
  const { total_score, breakdown, clb_levels, recommendations, recent_rounds, eligible_for_ita } =
    result;

  return (
    <div className="space-y-6">
      {/* Total Score Card */}
      <div className="rounded-lg border-2 border-blue-500 bg-gradient-to-br from-blue-50 to-white p-8 text-center shadow-lg">
        <div className="mb-2 text-sm font-medium uppercase tracking-wide text-blue-600">
          Score CRS Total
        </div>
        <div className="mb-4 text-6xl font-bold text-blue-600">{total_score}</div>
        <div className="flex items-center justify-center gap-2">
          {eligible_for_ita ? (
            <>
              <CheckCircle2 className="h-5 w-5 text-green-600" aria-hidden="true" />
              <span className="text-sm font-medium text-green-700">
                Éligible selon les dernières rondes
              </span>
            </>
          ) : (
            <>
              <AlertCircle className="h-5 w-5 text-amber-600" aria-hidden="true" />
              <span className="text-sm font-medium text-amber-700">
                Score inférieur aux seuils récents
              </span>
            </>
          )}
        </div>
      </div>

      {/* Score Breakdown */}
      <section className="rounded-lg border border-gray-200 bg-white p-6">
        <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900">
          <TrendingUp className="h-5 w-5 text-blue-600" aria-hidden="true" />
          Répartition des points
        </h3>
        <div className="space-y-3">
          {Object.entries(breakdown).map(([category, points]) => (
            <div
              key={category}
              className="flex items-center justify-between border-b border-gray-100 pb-2 last:border-b-0"
            >
              <span className="text-sm text-gray-700">{formatCategory(category)}</span>
              <span className="font-semibold text-gray-900">{points} pts</span>
            </div>
          ))}
        </div>
      </section>

      {/* CLB Levels */}
      <section className="rounded-lg border border-gray-200 bg-white p-6">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">Niveaux CLB / NCLC</h3>
        <div className="space-y-4">
          <div>
            <div className="mb-2 text-sm font-medium text-gray-700">Première langue</div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {Object.entries(clb_levels.first).map(([skill, level]) => (
                <div key={skill} className="rounded-md bg-gray-50 p-3 text-center">
                  <div className="text-xs text-gray-600 capitalize mb-1">
                    {skill === "reading" && "Lecture"}
                    {skill === "writing" && "Écriture"}
                    {skill === "listening" && "Écoute"}
                    {skill === "speaking" && "Expression"}
                  </div>
                  <div className="text-lg font-bold text-gray-900">CLB {level}</div>
                </div>
              ))}
            </div>
          </div>
          {clb_levels.second && (
            <div>
              <div className="mb-2 text-sm font-medium text-gray-700">Deuxième langue</div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {Object.entries(clb_levels.second).map(([skill, level]) => (
                  <div key={skill} className="rounded-md bg-gray-50 p-3 text-center">
                    <div className="text-xs text-gray-600 capitalize mb-1">
                      {skill === "reading" && "Lecture"}
                      {skill === "writing" && "Écriture"}
                      {skill === "listening" && "Écoute"}
                      {skill === "speaking" && "Expression"}
                    </div>
                    <div className="text-lg font-bold text-gray-900">CLB {level}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Recent Rounds */}
      {recent_rounds.length > 0 && (
        <section className="rounded-lg border border-gray-200 bg-white p-6">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">Rondes d&apos;invitation récentes</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left">
                  <th className="pb-2 font-medium text-gray-700">Date</th>
                  <th className="pb-2 font-medium text-gray-700">Programme</th>
                  <th className="pb-2 font-medium text-gray-700">Score minimum</th>
                  <th className="pb-2 font-medium text-gray-700">Statut</th>
                </tr>
              </thead>
              <tbody>
                {recent_rounds.map((round, idx) => {
                  const qualified = total_score >= round.score;
                  return (
                    <tr key={idx} className="border-b border-gray-100 last:border-b-0">
                      <td className="py-2 text-gray-900">
                        {new Date(round.date).toLocaleDateString("fr-CA")}
                      </td>
                      <td className="py-2 text-gray-700">{round.program}</td>
                      <td className="py-2 font-semibold text-gray-900">{round.score}</td>
                      <td className="py-2">
                        {qualified ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                            <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                            Qualifié
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                            Non qualifié
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-6">
          <h3 className="mb-3 text-lg font-semibold text-amber-900">
            Recommandations pour améliorer votre score
          </h3>
          <ul className="space-y-2">
            {recommendations.map((rec, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-amber-900">
                <span className="mt-0.5 inline-block h-1.5 w-1.5 flex-shrink-0 rounded-full bg-amber-600" />
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function formatCategory(key: string): string {
  const labels: Record<string, string> = {
    core_human_capital: "Capital humain (base)",
    spouse_factors: "Facteurs conjoint",
    skill_transferability: "Transférabilité des compétences",
    additional_points: "Points additionnels",
    age: "Âge",
    education: "Éducation",
    language: "Compétences linguistiques",
    canadian_experience: "Expérience canadienne",
    arranged_employment: "Offre d'emploi validée",
    provincial_nomination: "Nomination provinciale",
    sibling: "Frère ou sœur au Canada",
    french_proficiency: "Compétence en français",
  };
  return labels[key] || key;
}
