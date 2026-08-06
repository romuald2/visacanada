"use client";

import Link from "next/link";
import { ArrowRight, Shield, Zap, Users, BarChart3, MessageSquare, FileCheck, Globe, CheckCircle2 } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      {/* Header / Navigation */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Globe className="h-8 w-8 text-blue-600" />
            <span className="text-2xl font-bold text-blue-900">VisaCanada</span>
          </div>
          <nav className="hidden md:flex items-center gap-6">
            <a href="#features" className="text-gray-600 hover:text-blue-600 transition">Fonctionnalités</a>
            <a href="#security" className="text-gray-600 hover:text-blue-600 transition">Sécurité</a>
            <a href="#pricing" className="text-gray-600 hover:text-blue-600 transition">Tarifs</a>
            <Link href="/login" className="text-gray-600 hover:text-blue-600 transition">Connexion</Link>
            <Link
              href="/register"
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition"
            >
              Commencer gratuitement
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <div className="max-w-4xl mx-auto">
          <div className="inline-block mb-4 px-4 py-2 bg-blue-100 text-blue-700 rounded-full text-sm font-semibold">
            🍁 Plateforme SaaS canadienne conforme PIPEDA et Loi 25
          </div>
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
            Gérez vos dossiers d'immigration
            <span className="text-blue-600"> avec l'IA</span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            Plateforme tout-en-un pour consultants et candidats : vérification documentaire IA,
            alertes IRCC en temps réel, chatbot intelligent et analytics avancés.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/register"
              className="bg-blue-600 text-white px-8 py-4 rounded-lg font-semibold hover:bg-blue-700 transition flex items-center justify-center gap-2"
            >
              Démarrer gratuitement
              <ArrowRight className="h-5 w-5" />
            </Link>
            <Link
              href="/login"
              className="bg-white text-blue-600 border-2 border-blue-600 px-8 py-4 rounded-lg font-semibold hover:bg-blue-50 transition"
            >
              Voir la démo
            </Link>
          </div>
          <p className="text-sm text-gray-500 mt-4">
            ✓ Essai gratuit 14 jours &nbsp;·&nbsp; ✓ Sans carte de crédit &nbsp;·&nbsp; ✓ Support en français
          </p>
        </div>

        {/* Hero Image / Dashboard Preview */}
        <div className="mt-16 max-w-6xl mx-auto">
          <div className="rounded-xl shadow-2xl border-8 border-white bg-gradient-to-br from-blue-500 to-blue-700 p-8">
            <div className="bg-white rounded-lg p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-32"></div>
                  <div className="h-8 bg-blue-100 rounded w-48"></div>
                </div>
                <div className="h-12 w-12 bg-blue-600 rounded-full"></div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4 h-24"></div>
                <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-4 h-24"></div>
                <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-4 h-24"></div>
              </div>
              <div className="h-48 bg-gradient-to-r from-blue-100 via-purple-100 to-pink-100 rounded-lg"></div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Tout ce dont vous avez besoin pour réussir
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Une suite complète d'outils pour optimiser la gestion de vos dossiers d'immigration canadienne
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-6 hover:shadow-lg transition">
              <div className="h-12 w-12 bg-blue-600 rounded-lg flex items-center justify-center mb-4">
                <FileCheck className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Vérification IA des documents
              </h3>
              <p className="text-gray-600">
                Analyse automatique avec Claude AI et Azure Document Intelligence. Détection des erreurs,
                score de conformité et suggestions d'amélioration.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-6 hover:shadow-lg transition">
              <div className="h-12 w-12 bg-green-600 rounded-lg flex items-center justify-center mb-4">
                <Zap className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Alertes IRCC temps réel
              </h3>
              <p className="text-gray-600">
                Surveillance automatique des changements IRCC : quotas, délais de traitement,
                nouvelles exigences. Notifications instantanées.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-6 hover:shadow-lg transition">
              <div className="h-12 w-12 bg-purple-600 rounded-lg flex items-center justify-center mb-4">
                <MessageSquare className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Chatbot RAG intelligent
              </h3>
              <p className="text-gray-600">
                Assistant IA avec base de connaissances IRCC complète. Réponses précises sur
                Entrée Express, PVT, résidence permanente et plus.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-xl p-6 hover:shadow-lg transition">
              <div className="h-12 w-12 bg-orange-600 rounded-lg flex items-center justify-center mb-4">
                <BarChart3 className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Dashboard analytique
              </h3>
              <p className="text-gray-600">
                KPIs en temps réel, charts interactifs, export CSV/PDF. Suivez vos performances
                et optimisez votre processus.
              </p>
            </div>

            {/* Feature 5 */}
            <div className="bg-gradient-to-br from-pink-50 to-pink-100 rounded-xl p-6 hover:shadow-lg transition">
              <div className="h-12 w-12 bg-pink-600 rounded-lg flex items-center justify-center mb-4">
                <Users className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Portail candidat complet
              </h3>
              <p className="text-gray-600">
                Interface intuitive pour les candidats : upload documents, suivi dossier en temps réel,
                notifications personnalisées, profil éditable.
              </p>
            </div>

            {/* Feature 6 */}
            <div className="bg-gradient-to-br from-indigo-50 to-indigo-100 rounded-xl p-6 hover:shadow-lg transition">
              <div className="h-12 w-12 bg-indigo-600 rounded-lg flex items-center justify-center mb-4">
                <Shield className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Sécurité et conformité
              </h3>
              <p className="text-gray-600">
                Conforme PIPEDA et Loi 25. Chiffrement AES-256, MFA, RBAC, audit logs complets.
                Hébergement Canada (ca-central-1).
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Security Section */}
      <section id="security" className="py-20 bg-gradient-to-b from-gray-50 to-white">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="text-4xl font-bold text-gray-900 mb-4">
                Sécurité et confidentialité au cœur
              </h2>
              <p className="text-xl text-gray-600">
                Conformité totale avec les lois canadiennes sur la protection des données
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-8">
              <div className="flex gap-4">
                <CheckCircle2 className="h-6 w-6 text-green-600 flex-shrink-0 mt-1" />
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">PIPEDA conforme</h3>
                  <p className="text-gray-600">
                    10/10 principes respectés : transparence, accès individuel, contestation, sécurité
                  </p>
                </div>
              </div>

              <div className="flex gap-4">
                <CheckCircle2 className="h-6 w-6 text-green-600 flex-shrink-0 mt-1" />
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">Loi 25 Québec</h3>
                  <p className="text-gray-600">
                    Notification 72h, EFVP complété, IMO désigné, registre incidents
                  </p>
                </div>
              </div>

              <div className="flex gap-4">
                <CheckCircle2 className="h-6 w-6 text-green-600 flex-shrink-0 mt-1" />
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">Chiffrement bout en bout</h3>
                  <p className="text-gray-600">
                    HTTPS, S3 SSE AES-256, bcrypt, tokens JWT, Redis chiffré
                  </p>
                </div>
              </div>

              <div className="flex gap-4">
                <CheckCircle2 className="h-6 w-6 text-green-600 flex-shrink-0 mt-1" />
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">Hébergement Canada</h3>
                  <p className="text-gray-600">
                    Données stockées à Montréal (ca-central-1). Aucun transfert hors Canada
                  </p>
                </div>
              </div>

              <div className="flex gap-4">
                <CheckCircle2 className="h-6 w-6 text-green-600 flex-shrink-0 mt-1" />
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">MFA et RBAC</h3>
                  <p className="text-gray-600">
                    Authentification multi-facteurs, contrôle d'accès par rôle, rate limiting
                  </p>
                </div>
              </div>

              <div className="flex gap-4">
                <CheckCircle2 className="h-6 w-6 text-green-600 flex-shrink-0 mt-1" />
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">Audit logs complets</h3>
                  <p className="text-gray-600">
                    Traçabilité de toutes les actions sensibles, export données, plaintes
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Tarifs simples et transparents
            </h2>
            <p className="text-xl text-gray-600">
              Choisissez le plan adapté à votre cabinet
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {/* Starter */}
            <div className="border-2 border-gray-200 rounded-xl p-8 hover:shadow-lg transition">
              <h3 className="text-2xl font-bold text-gray-900 mb-2">Starter</h3>
              <p className="text-gray-600 mb-6">Pour consultants indépendants</p>
              <div className="mb-6">
                <span className="text-4xl font-bold">49$</span>
                <span className="text-gray-600">/mois</span>
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <span>Jusqu'à 50 dossiers actifs</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <span>Vérification IA illimitée</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <span>Alertes IRCC temps réel</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <span>1 utilisateur consultant</span>
                </li>
              </ul>
              <Link
                href="/register"
                className="block w-full bg-gray-900 text-white text-center px-6 py-3 rounded-lg font-semibold hover:bg-gray-800 transition"
              >
                Essayer gratuitement
              </Link>
            </div>

            {/* Professional (Popular) */}
            <div className="border-4 border-blue-600 rounded-xl p-8 relative hover:shadow-xl transition">
              <div className="absolute -top-4 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-4 py-1 rounded-full text-sm font-semibold">
                Populaire
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-2">Professional</h3>
              <p className="text-gray-600 mb-6">Pour petits cabinets</p>
              <div className="mb-6">
                <span className="text-4xl font-bold">149$</span>
                <span className="text-gray-600">/mois</span>
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-blue-600" />
                  <span>Jusqu'à 200 dossiers actifs</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-blue-600" />
                  <span>Vérification IA illimitée</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-blue-600" />
                  <span>Chatbot RAG + analytics</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-blue-600" />
                  <span>Jusqu'à 5 consultants</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-blue-600" />
                  <span>Support prioritaire</span>
                </li>
              </ul>
              <Link
                href="/register"
                className="block w-full bg-blue-600 text-white text-center px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition"
              >
                Essayer gratuitement
              </Link>
            </div>

            {/* Enterprise */}
            <div className="border-2 border-gray-200 rounded-xl p-8 hover:shadow-lg transition">
              <h3 className="text-2xl font-bold text-gray-900 mb-2">Enterprise</h3>
              <p className="text-gray-600 mb-6">Pour grands cabinets</p>
              <div className="mb-6">
                <span className="text-4xl font-bold">Sur mesure</span>
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <span>Dossiers illimités</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <span>Utilisateurs illimités</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <span>API personnalisée</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <span>Support dédié 24/7</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <span>Formation équipe</span>
                </li>
              </ul>
              <Link
                href="/contact"
                className="block w-full bg-gray-900 text-white text-center px-6 py-3 rounded-lg font-semibold hover:bg-gray-800 transition"
              >
                Nous contacter
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-blue-600 to-blue-800">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-4xl font-bold text-white mb-6">
            Prêt à transformer votre cabinet ?
          </h2>
          <p className="text-xl text-blue-100 mb-8 max-w-2xl mx-auto">
            Rejoignez les consultants qui font confiance à VisaCanada pour gérer leurs dossiers d'immigration
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/register"
              className="bg-white text-blue-600 px-8 py-4 rounded-lg font-semibold hover:bg-blue-50 transition inline-flex items-center justify-center gap-2"
            >
              Commencer gratuitement
              <ArrowRight className="h-5 w-5" />
            </Link>
            <Link
              href="/contact"
              className="bg-transparent border-2 border-white text-white px-8 py-4 rounded-lg font-semibold hover:bg-white/10 transition"
            >
              Planifier une démo
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-12">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Globe className="h-6 w-6 text-blue-500" />
                <span className="text-xl font-bold text-white">VisaCanada</span>
              </div>
              <p className="text-sm">
                Plateforme SaaS de gestion de dossiers d'immigration canadienne avec IA
              </p>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">Produit</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#features" className="hover:text-white transition">Fonctionnalités</a></li>
                <li><a href="#pricing" className="hover:text-white transition">Tarifs</a></li>
                <li><a href="#security" className="hover:text-white transition">Sécurité</a></li>
                <li><Link href="/login" className="hover:text-white transition">Connexion</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">Légal</h4>
              <ul className="space-y-2 text-sm">
                <li><Link href="/privacy" className="hover:text-white transition">Politique de confidentialité</Link></li>
                <li><a href="#" className="hover:text-white transition">Conditions d'utilisation</a></li>
                <li><a href="#" className="hover:text-white transition">DPA</a></li>
                <li><a href="#" className="hover:text-white transition">Conformité</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">Contact</h4>
              <ul className="space-y-2 text-sm">
                <li>support@visacanada.ca</li>
                <li>+1 (514) 123-4567</li>
                <li>Montréal, QC, Canada</li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-8 text-sm text-center">
            <p>&copy; 2026 VisaCanada. Tous droits réservés. Conforme PIPEDA et Loi 25.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
