export default function PrivacyPolicyPage() {
  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <h1 className="text-3xl font-bold mb-6">Politique de confidentialité</h1>

      <div className="prose max-w-none space-y-6">
        <section>
          <h2 className="text-2xl font-semibold mb-3">1. Introduction</h2>
          <p className="text-gray-700">
            VisaCanada s&apos;engage à protéger la confidentialité de vos données personnelles
            conformément à la Loi sur la protection des renseignements personnels et les documents
            électroniques (PIPEDA) et à la Loi 25 du Québec.
          </p>
          <p className="text-gray-700 mt-2">
            Cette politique explique comment nous collectons, utilisons, conservons et protégeons
            vos informations personnelles.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-3">2. Données collectées</h2>
          <p className="text-gray-700 mb-2">Nous collectons les données suivantes :</p>
          <ul className="list-disc list-inside text-gray-700 space-y-1">
            <li>Informations d&apos;identification : nom, prénom, email, téléphone</li>
            <li>Documents d&apos;identité : passeport, acte de naissance, certificats</li>
            <li>Informations financières : relevés bancaires (pour preuve de fonds)</li>
            <li>Résultats de tests : IELTS, TEF, examens médicaux</li>
            <li>Données professionnelles : CV, lettres de référence</li>
            <li>Données de connexion : adresse IP, logs d&apos;accès (à des fins de sécurité)</li>
          </ul>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-3">3. Utilisation des données</h2>
          <p className="text-gray-700 mb-2">Vos données sont utilisées uniquement pour :</p>
          <ul className="list-disc list-inside text-gray-700 space-y-1">
            <li>Préparer et soumettre votre demande d&apos;immigration canadienne</li>
            <li>Vérifier la conformité de vos documents (via intelligence artificielle)</li>
            <li>Vous notifier des échéances importantes</li>
            <li>Communiquer avec vous concernant votre dossier</li>
            <li>Respecter nos obligations légales et réglementaires</li>
          </ul>
          <p className="text-gray-700 mt-2">
            <strong>Vos données ne sont jamais vendues ni partagées avec des tiers à des fins commerciales.</strong>
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-3">4. Conservation des données</h2>
          <p className="text-gray-700">
            Vos données sont conservées pendant la durée nécessaire au traitement de votre dossier,
            plus 7 ans après la décision finale (conformément aux exigences d&apos;IRCC).
            Passé ce délai, elles sont supprimées de manière sécurisée.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-3">5. Résidence des données</h2>
          <p className="text-gray-700">
            Toutes vos données personnelles sont hébergées au Canada (région AWS ca-central-1).
            Aucun transfert hors du Canada n&apos;est effectué sans votre consentement explicite.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-3">6. Sécurité</h2>
          <p className="text-gray-700 mb-2">Nous mettons en œuvre les mesures suivantes :</p>
          <ul className="list-disc list-inside text-gray-700 space-y-1">
            <li>Chiffrement HTTPS pour toutes les communications</li>
            <li>Chiffrement des documents au repos (AWS S3 SSE)</li>
            <li>Hachage des mots de passe avec bcrypt</li>
            <li>Limitation du nombre de tentatives de connexion</li>
            <li>Journalisation des accès aux documents sensibles</li>
            <li>Contrôle d&apos;accès strict par rôle (admin, consultant, candidat)</li>
          </ul>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-3">7. Vos droits (PIPEDA)</h2>
          <p className="text-gray-700 mb-2">Vous avez le droit de :</p>
          <ul className="list-disc list-inside text-gray-700 space-y-1">
            <li>
              <strong>Accéder</strong> à vos données personnelles : consultez votre profil à tout moment
              via <a href="/portal/profile" className="text-blue-600 hover:underline">/portal/profile</a>
            </li>
            <li>
              <strong>Corriger</strong> vos données : mettez à jour votre profil directement
            </li>
            <li>
              <strong>Exporter</strong> vos données : téléchargez une copie complète via{" "}
              <a href="/portal/export" className="text-blue-600 hover:underline">/portal/export</a>
            </li>
            <li>
              <strong>Retirer votre consentement</strong> : contactez-nous à privacy@visacanada.com
            </li>
            <li>
              <strong>Déposer une plainte</strong> : utilisez le{" "}
              <a href="/portal/complaint" className="text-blue-600 hover:underline">formulaire de plainte</a>
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-3">8. Intelligence artificielle</h2>
          <p className="text-gray-700">
            Nous utilisons l&apos;IA (Claude d&apos;Anthropic, Azure Document Intelligence) pour analyser
            vos documents et détecter les erreurs. Ces analyses sont effectuées de manière sécurisée
            et confidentielle. Les scores de conformité et les résultats d&apos;IA ne vous sont pas
            communiqués directement pour éviter toute incompréhension ; votre consultant les utilise
            pour améliorer votre dossier.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-3">9. Violation de données</h2>
          <p className="text-gray-700">
            En cas de violation de vos données personnelles, nous vous notifierons dans les 72 heures
            suivant la découverte de l&apos;incident, conformément à la Loi 25. Nous informerons
            également le Commissaire à la vie privée du Canada.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-3">10. Cookies</h2>
          <p className="text-gray-700">
            Nous utilisons uniquement des cookies essentiels pour maintenir votre session de connexion.
            Aucun cookie de suivi publicitaire n&apos;est utilisé.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-3">11. Modifications</h2>
          <p className="text-gray-700">
            Cette politique peut être mise à jour périodiquement. La date de dernière modification
            est indiquée ci-dessous. Nous vous notifierons par email en cas de changement majeur.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-3">12. Contact</h2>
          <p className="text-gray-700">
            Pour toute question concernant cette politique ou vos données personnelles :
          </p>
          <ul className="list-none text-gray-700 space-y-1 mt-2">
            <li>
              <strong>Email :</strong>{" "}
              <a href="mailto:privacy@visacanada.com" className="text-blue-600 hover:underline">
                privacy@visacanada.com
              </a>
            </li>
            <li><strong>Téléphone :</strong> +1 (555) 123-4567</li>
            <li>
              <strong>Commissaire à la vie privée du Canada :</strong>{" "}
              <a
                href="https://www.priv.gc.ca"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                www.priv.gc.ca
              </a>
            </li>
          </ul>
        </section>

        <div className="border-t pt-4 mt-8">
          <p className="text-sm text-gray-500">
            <strong>Dernière mise à jour :</strong> 5 août 2026
          </p>
        </div>
      </div>
    </div>
  );
}
