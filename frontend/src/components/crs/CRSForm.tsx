"use client";

import { useState } from "react";
import type { CRSCalculateRequest, LanguageScore } from "@/lib/types";

interface CRSFormProps {
  onSubmit: (data: CRSCalculateRequest) => void;
  loading?: boolean;
}

const MARITAL_STATUS_OPTIONS = [
  { value: "single", label: "Célibataire" },
  { value: "married", label: "Marié(e) / Conjoint(e) de fait" },
];

const EDUCATION_OPTIONS = [
  { value: "none", label: "Aucune éducation formelle" },
  { value: "secondary", label: "Diplôme d'études secondaires" },
  { value: "one_year_post_secondary", label: "1 an post-secondaire" },
  { value: "two_year_post_secondary", label: "2 ans post-secondaire" },
  { value: "bachelors", label: "Baccalauréat (3+ ans)" },
  { value: "two_or_more_post_secondary", label: "Deux diplômes ou plus" },
  { value: "masters", label: "Maîtrise" },
  { value: "doctoral", label: "Doctorat" },
];

const CANADIAN_EDU_OPTIONS = [
  { value: "none", label: "Aucun" },
  { value: "one_year", label: "1 an" },
  { value: "two_year", label: "2 ans" },
  { value: "three_plus", label: "3 ans ou plus" },
];

const TEST_TYPE_OPTIONS = [
  { value: "ielts", label: "IELTS" },
  { value: "celpip", label: "CELPIP" },
  { value: "tef", label: "TEF" },
  { value: "tcf", label: "TCF" },
];

const NOC_OPTIONS = [
  { value: "00", label: "NOC 00 (direction)" },
  { value: "0ab", label: "NOC 0, A ou B" },
  { value: "other", label: "Autre / Aucun" },
];

const FRENCH_PROF_OPTIONS = [
  { value: "none", label: "Aucun" },
  { value: "clb7", label: "NCLC 7 ou plus" },
  { value: "clb7_plus", label: "NCLC 7+ (avec anglais CLB 5+)" },
];

export function CRSForm({ onSubmit, loading }: CRSFormProps) {
  const [age, setAge] = useState(30);
  const [maritalStatus, setMaritalStatus] = useState("single");
  const [education, setEducation] = useState("bachelors");
  const [canadianEdu, setCanadianEdu] = useState("none");

  const [firstLang, setFirstLang] = useState<LanguageScore>({
    reading: 7.0,
    writing: 7.0,
    listening: 7.0,
    speaking: 7.0,
    test_type: "ielts",
  });

  const [hasSecondLang, setHasSecondLang] = useState(false);
  const [secondLang, setSecondLang] = useState<LanguageScore>({
    reading: 0,
    writing: 0,
    listening: 0,
    speaking: 0,
    test_type: "ielts",
  });

  const [canadianExp, setCanadianExp] = useState(0);
  const [foreignExp, setForeignExp] = useState(0);

  const [spouseEdu, setSpouseEdu] = useState("none");
  const [hasSpouseLang, setHasSpouseLang] = useState(false);
  const [spouseLang, setSpouseLang] = useState<LanguageScore>({
    reading: 0,
    writing: 0,
    listening: 0,
    speaking: 0,
    test_type: "ielts",
  });
  const [spouseCanExp, setSpouseCanExp] = useState(0);

  const [hasPNP, setHasPNP] = useState(false);
  const [hasJobOffer, setHasJobOffer] = useState(false);
  const [jobNOC, setJobNOC] = useState("other");
  const [hasSibling, setHasSibling] = useState(false);
  const [frenchProf, setFrenchProf] = useState("none");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data: CRSCalculateRequest = {
      age,
      marital_status: maritalStatus,
      education_level: education,
      canadian_education: canadianEdu,
      first_language: firstLang,
      second_language: hasSecondLang ? secondLang : undefined,
      canadian_experience_years: canadianExp,
      foreign_experience_years: foreignExp,
      spouse_education: spouseEdu,
      spouse_language: hasSpouseLang ? spouseLang : undefined,
      spouse_canadian_experience_years: spouseCanExp,
      has_provincial_nomination: hasPNP,
      has_arranged_employment: hasJobOffer,
      arranged_employment_noc: jobNOC,
      has_canadian_sibling: hasSibling,
      french_language_proficiency: frenchProf,
    };
    onSubmit(data);
  };

  const isMarried = maritalStatus === "married";

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {/* Personal Information */}
      <section className="rounded-lg border border-gray-200 bg-white p-6">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">
          Informations personnelles
        </h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="age" className="block text-sm font-medium text-gray-700 mb-1">
              Âge
            </label>
            <input
              type="number"
              id="age"
              min="18"
              max="65"
              value={age}
              onChange={(e) => setAge(Number(e.target.value))}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              required
            />
          </div>
          <div>
            <label htmlFor="marital" className="block text-sm font-medium text-gray-700 mb-1">
              État civil
            </label>
            <select
              id="marital"
              value={maritalStatus}
              onChange={(e) => setMaritalStatus(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {MARITAL_STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* Education */}
      <section className="rounded-lg border border-gray-200 bg-white p-6">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">Éducation</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="education" className="block text-sm font-medium text-gray-700 mb-1">
              Niveau d&apos;éducation
            </label>
            <select
              id="education"
              value={education}
              onChange={(e) => setEducation(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {EDUCATION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="can-edu" className="block text-sm font-medium text-gray-700 mb-1">
              Éducation canadienne
            </label>
            <select
              id="can-edu"
              value={canadianEdu}
              onChange={(e) => setCanadianEdu(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {CANADIAN_EDU_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* First Language */}
      <section className="rounded-lg border border-gray-200 bg-white p-6">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">
          Première langue officielle
        </h3>
        <div className="mb-4">
          <label htmlFor="test-type" className="block text-sm font-medium text-gray-700 mb-1">
            Type de test
          </label>
          <select
            id="test-type"
            value={firstLang.test_type}
            onChange={(e) => setFirstLang({ ...firstLang, test_type: e.target.value })}
            className="w-full max-w-xs rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {TEST_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div className="grid gap-4 sm:grid-cols-4">
          {(["reading", "writing", "listening", "speaking"] as const).map((skill) => (
            <div key={skill}>
              <label
                htmlFor={`first-${skill}`}
                className="block text-sm font-medium text-gray-700 mb-1 capitalize"
              >
                {skill === "reading" && "Lecture"}
                {skill === "writing" && "Écriture"}
                {skill === "listening" && "Écoute"}
                {skill === "speaking" && "Expression orale"}
              </label>
              <input
                type="number"
                id={`first-${skill}`}
                min="0"
                max="10"
                step="0.5"
                value={firstLang[skill]}
                onChange={(e) =>
                  setFirstLang({ ...firstLang, [skill]: Number(e.target.value) })
                }
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                required
              />
            </div>
          ))}
        </div>
      </section>

      {/* Second Language (Optional) */}
      <section className="rounded-lg border border-gray-200 bg-white p-6">
        <div className="mb-4 flex items-center">
          <input
            type="checkbox"
            id="has-second-lang"
            checked={hasSecondLang}
            onChange={(e) => setHasSecondLang(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <label htmlFor="has-second-lang" className="ml-2 text-sm font-medium text-gray-700">
            J&apos;ai un résultat pour une deuxième langue officielle
          </label>
        </div>
        {hasSecondLang && (
          <>
            <div className="mb-4">
              <label htmlFor="second-test-type" className="block text-sm font-medium text-gray-700 mb-1">
                Type de test
              </label>
              <select
                id="second-test-type"
                value={secondLang.test_type}
                onChange={(e) => setSecondLang({ ...secondLang, test_type: e.target.value })}
                className="w-full max-w-xs rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {TEST_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid gap-4 sm:grid-cols-4">
              {(["reading", "writing", "listening", "speaking"] as const).map((skill) => (
                <div key={skill}>
                  <label
                    htmlFor={`second-${skill}`}
                    className="block text-sm font-medium text-gray-700 mb-1 capitalize"
                  >
                    {skill === "reading" && "Lecture"}
                    {skill === "writing" && "Écriture"}
                    {skill === "listening" && "Écoute"}
                    {skill === "speaking" && "Expression orale"}
                  </label>
                  <input
                    type="number"
                    id={`second-${skill}`}
                    min="0"
                    max="10"
                    step="0.5"
                    value={secondLang[skill]}
                    onChange={(e) =>
                      setSecondLang({ ...secondLang, [skill]: Number(e.target.value) })
                    }
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              ))}
            </div>
          </>
        )}
      </section>

      {/* Work Experience */}
      <section className="rounded-lg border border-gray-200 bg-white p-6">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">Expérience de travail</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="can-exp" className="block text-sm font-medium text-gray-700 mb-1">
              Expérience canadienne (années)
            </label>
            <input
              type="number"
              id="can-exp"
              min="0"
              max="10"
              value={canadianExp}
              onChange={(e) => setCanadianExp(Number(e.target.value))}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="foreign-exp" className="block text-sm font-medium text-gray-700 mb-1">
              Expérience étrangère (années)
            </label>
            <input
              type="number"
              id="foreign-exp"
              min="0"
              max="10"
              value={foreignExp}
              onChange={(e) => setForeignExp(Number(e.target.value))}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>
      </section>

      {/* Spouse/Partner (if married) */}
      {isMarried && (
        <section className="rounded-lg border border-gray-200 bg-white p-6">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">
            Conjoint(e) / Partenaire de fait
          </h3>
          <div className="mb-4">
            <label htmlFor="spouse-edu" className="block text-sm font-medium text-gray-700 mb-1">
              Niveau d&apos;éducation du conjoint
            </label>
            <select
              id="spouse-edu"
              value={spouseEdu}
              onChange={(e) => setSpouseEdu(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {EDUCATION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="mb-4 flex items-center">
            <input
              type="checkbox"
              id="has-spouse-lang"
              checked={hasSpouseLang}
              onChange={(e) => setHasSpouseLang(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="has-spouse-lang" className="ml-2 text-sm font-medium text-gray-700">
              Le conjoint a des résultats de test de langue
            </label>
          </div>

          {hasSpouseLang && (
            <>
              <div className="mb-4">
                <label htmlFor="spouse-test-type" className="block text-sm font-medium text-gray-700 mb-1">
                  Type de test
                </label>
                <select
                  id="spouse-test-type"
                  value={spouseLang.test_type}
                  onChange={(e) => setSpouseLang({ ...spouseLang, test_type: e.target.value })}
                  className="w-full max-w-xs rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  {TEST_TYPE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid gap-4 sm:grid-cols-4 mb-4">
                {(["reading", "writing", "listening", "speaking"] as const).map((skill) => (
                  <div key={skill}>
                    <label
                      htmlFor={`spouse-${skill}`}
                      className="block text-sm font-medium text-gray-700 mb-1 capitalize"
                    >
                      {skill === "reading" && "Lecture"}
                      {skill === "writing" && "Écriture"}
                      {skill === "listening" && "Écoute"}
                      {skill === "speaking" && "Expression orale"}
                    </label>
                    <input
                      type="number"
                      id={`spouse-${skill}`}
                      min="0"
                      max="10"
                      step="0.5"
                      value={spouseLang[skill]}
                      onChange={(e) =>
                        setSpouseLang({ ...spouseLang, [skill]: Number(e.target.value) })
                      }
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                ))}
              </div>
            </>
          )}

          <div>
            <label htmlFor="spouse-can-exp" className="block text-sm font-medium text-gray-700 mb-1">
              Expérience canadienne du conjoint (années)
            </label>
            <input
              type="number"
              id="spouse-can-exp"
              min="0"
              max="5"
              value={spouseCanExp}
              onChange={(e) => setSpouseCanExp(Number(e.target.value))}
              className="w-full max-w-xs rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </section>
      )}

      {/* Additional Points */}
      <section className="rounded-lg border border-gray-200 bg-white p-6">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">Points additionnels</h3>
        <div className="space-y-4">
          <div className="flex items-center">
            <input
              type="checkbox"
              id="pnp"
              checked={hasPNP}
              onChange={(e) => setHasPNP(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="pnp" className="ml-2 text-sm font-medium text-gray-700">
              Nomination provinciale (PNP)
            </label>
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="job-offer"
              checked={hasJobOffer}
              onChange={(e) => setHasJobOffer(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="job-offer" className="ml-2 text-sm font-medium text-gray-700">
              Offre d&apos;emploi valide (EIMT)
            </label>
          </div>

          {hasJobOffer && (
            <div>
              <label htmlFor="noc" className="block text-sm font-medium text-gray-700 mb-1">
                Niveau NOC de l&apos;offre
              </label>
              <select
                id="noc"
                value={jobNOC}
                onChange={(e) => setJobNOC(e.target.value)}
                className="w-full max-w-xs rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {NOC_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="flex items-center">
            <input
              type="checkbox"
              id="sibling"
              checked={hasSibling}
              onChange={(e) => setHasSibling(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="sibling" className="ml-2 text-sm font-medium text-gray-700">
              Frère ou sœur au Canada (citoyen ou résident permanent)
            </label>
          </div>

          <div>
            <label htmlFor="french" className="block text-sm font-medium text-gray-700 mb-1">
              Compétence en français
            </label>
            <select
              id="french"
              value={frenchProf}
              onChange={(e) => setFrenchProf(e.target.value)}
              className="w-full max-w-xs rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {FRENCH_PROF_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* Submit */}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {loading ? "Calcul en cours..." : "Calculer le score CRS"}
        </button>
      </div>
    </form>
  );
}
