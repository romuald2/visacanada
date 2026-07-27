# Issues GitHub — Projet VisaCanada
# Ordre de priorité pour le développement

Copiez-collez chaque issue sur https://github.com/romuald2/visacanada/issues/new
Ou corrigez les permissions de votre token et je les crée automatiquement.

---

## Issue #1 — Setup projet (Next.js + FastAPI + PostgreSQL + Docker)
**Labels:** `setup`, `infrastructure`, `phase-1`
**Priorité:** 🔴 Critique

### Description
Mettre en place l'architecture de base du projet.

### Tâches
- [ ] Initialiser le monorepo (structure `frontend/`, `backend/`, `docker/`)
- [ ] Setup Next.js 15 avec TypeScript, Tailwind CSS, shadcn/ui
- [ ] Setup FastAPI avec structure modulaire (routers, services, models, schemas)
- [ ] Configurer PostgreSQL 16 avec migrations (Alembic)
- [ ] Ajouter pgvector pour le futur RAG
- [ ] Créer le docker-compose.yml (frontend, backend, db, redis)
- [ ] Configurer les variables d'environnement (.env.example)
- [ ] Setup GitHub Actions (lint, tests, build)
- [ ] README avec instructions d'installation

---

## Issue #2 — Authentification et gestion des rôles (RBAC)
**Labels:** `auth`, `security`, `phase-1`
**Priorité:** 🔴 Critique

### Description
Implémenter le système d'authentification avec 3 rôles : Admin, Consultant, Candidat.

### Tâches
- [ ] Intégrer NextAuth.js (ou Clerk) côté frontend
- [ ] API d'authentification FastAPI (JWT tokens)
- [ ] Modèle User avec rôles (Admin, Consultant, Candidat)
- [ ] Middleware de protection des routes (frontend + backend)
- [ ] Page de login / inscription
- [ ] Gestion des sessions et refresh tokens
- [ ] Page de gestion des utilisateurs (admin)

---

## Issue #3 — Modèle de données (candidats, dossiers, documents, programmes)
**Labels:** `database`, `backend`, `phase-1`
**Priorité:** 🔴 Critique

### Description
Concevoir et implémenter le schéma de base de données complet.

### Tâches
- [ ] Table `candidates` (infos personnelles, contact, statut)
- [ ] Table `dossiers` (programme choisi, statut, dates, score conformité)
- [ ] Table `documents` (type, fichier S3, statut vérification, score)
- [ ] Table `programs` (nom, description, documents requis, critères)
- [ ] Table `notifications` (type, message, lu/non-lu, canal)
- [ ] Table `audit_logs` (actions, utilisateur, timestamp)
- [ ] Relations et contraintes d'intégrité
- [ ] Migrations Alembic
- [ ] Seeds avec les programmes IRCC de base

---

## Issue #4 — CRUD dossiers candidats
**Labels:** `backend`, `frontend`, `phase-1`
**Priorité:** 🔴 Critique

### Description
Interface complète de gestion des dossiers candidats.

### Tâches
- [ ] API REST : créer, lire, modifier, supprimer un dossier
- [ ] API REST : lister les dossiers avec filtres (statut, programme, date)
- [ ] Page liste des dossiers avec recherche et filtres
- [ ] Page détail d'un dossier (infos candidat, documents, historique)
- [ ] Formulaire création/édition de dossier
- [ ] Assignation d'un programme d'immigration au dossier
- [ ] Statuts de dossier (Nouveau, En cours, Documents manquants, Soumis, Approuvé, Refusé)

---

## Issue #5 — Base de connaissances IRCC (programmes + documents requis)
**Labels:** `ai`, `backend`, `phase-2`
**Priorité:** 🟠 Haute

### Description
Créer et maintenir une base de données complète des programmes d'immigration canadiens et leurs exigences documentaires.

### Tâches
- [ ] Recenser tous les programmes IRCC (Express Entry, PNP, IEC, études, travail, famille, etc.)
- [ ] Pour chaque programme : critères d'éligibilité, documents requis, frais, délais
- [ ] Stocker les checklists IMM (IMM 5534, IMM 0199, etc.) en format structuré
- [ ] API pour récupérer la checklist par programme
- [ ] Interface admin pour mettre à jour manuellement les exigences
- [ ] Versionner les changements (historique des modifications)

---

## Issue #6 — Monitoring IRCC (flux RSS + détection de mises à jour)
**Labels:** `automation`, `backend`, `phase-2`
**Priorité:** 🟠 Haute

### Description
Surveiller le site IRCC 2-3 fois par semaine pour détecter les changements de politique et mises à jour.

### Tâches
- [ ] Intégrer le flux Atom IRCC (api.io.canada.ca)
- [ ] Scraper léger des pages processing times (avec respect robots.txt)
- [ ] Job Celery planifié (lundi, mercredi, vendredi)
- [ ] Parser les mises à jour et catégoriser (nouveau programme, changement critères, délais)
- [ ] Notifier l'admin des changements détectés
- [ ] Historique des mises à jour détectées
- [ ] Dashboard des dernières actualités IRCC

---

## Issue #7 — Upload et stockage sécurisé des documents
**Labels:** `storage`, `security`, `phase-2`
**Priorité:** 🟠 Haute

### Description
Système d'upload sécurisé avec stockage chiffré sur AWS S3 (Canada).

### Tâches
- [ ] Configuration AWS S3 bucket (ca-central-1, chiffrement AES-256, versioning)
- [ ] API d'upload avec validation (formats: PDF, JPG, PNG, DOC — max 10MB)
- [ ] URLs pré-signées pour accès temporaire aux documents
- [ ] Visionneuse de documents sécurisée (pas de téléchargement direct)
- [ ] Organisation des fichiers par candidat/dossier
- [ ] Journalisation des accès aux documents
- [ ] Suppression sécurisée (soft delete + rétention)

---

## Issue #8 — OCR et extraction de données (Azure Document Intelligence)
**Labels:** `ai`, `ocr`, `phase-2`
**Priorité:** 🟠 Haute

### Description
Extraire automatiquement les données des documents uploadés via OCR intelligent.

### Tâches
- [ ] Intégrer Azure Document Intelligence (modèle prebuilt ID pour passeports)
- [ ] Extraction des champs : nom, prénom, date naissance, nationalité, n° document, expiration
- [ ] Extraction données des relevés bancaires (solde, historique)
- [ ] Extraction données des lettres d'emploi (poste, salaire, dates)
- [ ] Tesseract en fallback pour documents non-standards
- [ ] Stocker les données extraites en JSONB (PostgreSQL)
- [ ] Interface de validation manuelle (corriger les erreurs OCR)

---

## Issue #9 — Vérification de conformité IA (score sur 100%)
**Labels:** `ai`, `core-feature`, `phase-2`
**Priorité:** 🟠 Haute

### Description
L'IA analyse les documents fournis et donne un score de conformité par rapport aux exigences du programme choisi.

### Tâches
- [ ] Agent IA (Claude API) qui compare documents fournis vs checklist requise
- [ ] Vérification de complétude (documents manquants)
- [ ] Vérification de validité (dates d'expiration, formats acceptés)
- [ ] Cross-référencement entre documents (cohérence noms, dates, montants)
- [ ] Score global sur 100% avec détail par critère
- [ ] Recommandations pour améliorer le score
- [ ] Rapport de conformité PDF exportable

---

## Issue #10 — Détection de documents falsifiés
**Labels:** `ai`, `security`, `phase-2`
**Priorité:** 🟠 Haute

### Description
Détecter les documents potentiellement falsifiés via analyse IA multi-critères.

### Tâches
- [ ] Analyse des métadonnées (EXIF, timestamps création/modification PDF)
- [ ] Vérification MRZ (Machine Readable Zone) pour passeports/visas
- [ ] Analyse de cohérence visuelle (polices, alignement, résolution)
- [ ] Cross-référencement avec les templates de documents officiels connus
- [ ] Détection d'incohérences logiques (dates impossibles, etc.)
- [ ] Score de confiance avec explication des anomalies détectées
- [ ] Flag pour revue humaine (jamais de rejet automatique)
- [ ] Journalisation des alertes de fraude

---

## Issue #11 — Aide au remplissage de profil IRCC
**Labels:** `ai`, `automation`, `phase-3`
**Priorité:** 🟡 Moyenne

### Description
Assister l'admin pour remplir le profil de chaque candidat sur le site IRCC en pré-remplissant les informations extraites des documents.

### Tâches
- [ ] Mapper les champs extraits (OCR) vers les champs des formulaires IRCC
- [ ] Générer un formulaire pré-rempli par programme (Express Entry, PNP, etc.)
- [ ] Détection des champs obligatoires manquants
- [ ] Validation des formats (dates, codes postaux, etc.)
- [ ] Alertes sur incohérences ou informations non conformes
- [ ] Export du profil pré-rempli (PDF ou JSON)
- [ ] Guide étape par étape pour la soumission manuelle

---

## Issue #12 — Connexion email candidats (Gmail API + Microsoft Graph)
**Labels:** `integration`, `automation`, `phase-3`
**Priorité:** 🟡 Moyenne

### Description
Se connecter aux boîtes email des candidats pour détecter les emails de l'IRCC.

### Tâches
- [ ] Flux OAuth2 pour Gmail (Google Cloud Console, Pub/Sub)
- [ ] Flux OAuth2 pour Outlook (Microsoft Graph, webhooks)
- [ ] Filtre emails provenant de *@cic.gc.ca et *@canada.ca
- [ ] Parser le contenu des emails IRCC (type de notification, action requise)
- [ ] Stocker les emails détectés liés à chaque dossier
- [ ] Gestion du consentement candidat (révocation possible)
- [ ] Refresh automatique des tokens OAuth

---

## Issue #13 — Notifications WhatsApp Business API
**Labels:** `integration`, `notifications`, `phase-3`
**Priorité:** 🟡 Moyenne

### Description
Notifier l'admin via WhatsApp quand un événement important survient sur un dossier.

### Tâches
- [ ] Intégrer Twilio WhatsApp Business API
- [ ] Templates de messages (nouvel email IRCC, document manquant, deadline)
- [ ] Envoi de notifications à l'admin (nouveau email IRCC détecté)
- [ ] File d'attente Redis pour éviter le spam
- [ ] Historique des notifications envoyées
- [ ] Configuration des préférences de notification (quels événements)
- [ ] Fallback SMS si WhatsApp échoue

---

## Issue #14 — Dashboard admin
**Labels:** `frontend`, `phase-3`
**Priorité:** 🟡 Moyenne

### Description
Vue globale de tous les dossiers avec indicateurs clés et actions rapides.

### Tâches
- [ ] Vue d'ensemble : nombre de dossiers par statut (graphiques)
- [ ] Liste des actions urgentes (documents expirant, deadlines proches)
- [ ] Dernières notifications (emails IRCC reçus, alertes)
- [ ] Dernières mises à jour IRCC (changements de politique)
- [ ] Accès rapide aux dossiers récents
- [ ] Filtres par programme, statut, consultant
- [ ] Responsive (desktop + mobile)

---

## Issue #15 — Calculateur de points CRS
**Labels:** `feature`, `phase-4`
**Priorité:** 🟢 Normale

### Description
Simuler le score CRS (Comprehensive Ranking System) d'un candidat pour Express Entry.

### Tâches
- [ ] Formulaire avec tous les critères CRS (âge, langue, études, expérience, etc.)
- [ ] Calcul automatique du score selon la grille officielle IRCC
- [ ] Comparaison avec les scores des dernières rondes d'invitation
- [ ] Recommandations pour améliorer le score
- [ ] Pré-remplissage depuis les données du dossier candidat
- [ ] Historique des simulations

---

## Issue #16 — Génération automatique de lettres IA
**Labels:** `ai`, `feature`, `phase-4`
**Priorité:** 🟢 Normale

### Description
Générer des brouillons de lettres adaptés au programme et au profil du candidat.

### Tâches
- [ ] Lettre de motivation (pourquoi le Canada, objectifs)
- [ ] Lettre d'explication (gaps d'emploi, refus antérieur, situation particulière)
- [ ] Lettre de soutien financier
- [ ] Templates par programme d'immigration
- [ ] Personnalisation avec les données du candidat
- [ ] Édition manuelle avant export
- [ ] Export PDF avec mise en page professionnelle

---

## Issue #17 — Portail candidat (lecture seule)
**Labels:** `frontend`, `feature`, `phase-4`
**Priorité:** 🟢 Normale

### Description
Accès limité pour que le candidat puisse suivre son dossier.

### Tâches
- [ ] Page de login candidat (lien d'invitation par email)
- [ ] Vue de l'état du dossier (progression visuelle)
- [ ] Liste des documents fournis / manquants
- [ ] Notifications de progression
- [ ] Upload de documents par le candidat
- [ ] Pas d'accès aux outils admin ni aux scores internes
- [ ] Multi-langue (français / anglais)

---

## Issue #18 — Système d'alertes intelligentes
**Labels:** `ai`, `automation`, `phase-4`
**Priorité:** 🟢 Normale

### Description
Alertes proactives basées sur les deadlines, événements IRCC et état des dossiers.

### Tâches
- [ ] Alerte : passeport expire dans < 6 mois
- [ ] Alerte : examen médical expire bientôt
- [ ] Alerte : résultats de langue expirent
- [ ] Alerte : nouvelle ronde Express Entry (score compatible)
- [ ] Alerte : changement de politique IRCC impactant un dossier
- [ ] Alerte : deadline de soumission approche
- [ ] Configuration par dossier (activer/désactiver)
- [ ] Multi-canal : dashboard + email + WhatsApp

---

## Issue #19 — Analytics et reporting
**Labels:** `feature`, `phase-4`
**Priorité:** 🟢 Normale

### Description
Tableaux de bord analytiques pour suivre la performance de l'entreprise.

### Tâches
- [ ] Taux de réussite par programme
- [ ] Temps moyen de traitement des dossiers
- [ ] Nombre de dossiers actifs / complétés / refusés
- [ ] Revenus par dossier et par période
- [ ] Prévisions de charge de travail
- [ ] Export de rapports (PDF, CSV)
- [ ] Graphiques interactifs (Chart.js ou Recharts)

---

## Issue #20 — Dossiers familiaux multi-candidats
**Labels:** `feature`, `phase-5`
**Priorité:** 🔵 Basse

### Description
Gérer les dossiers liés (conjoint, enfants) avec documents partagés.

### Tâches
- [ ] Lier plusieurs candidats dans un dossier familial
- [ ] Documents partagés entre membres de la famille
- [ ] Suivi coordonné des procédures liées
- [ ] Vue famille sur le dashboard

---

## Issue #21 — Gestion des paiements et facturation
**Labels:** `feature`, `phase-5`
**Priorité:** 🔵 Basse

### Description
Suivi des paiements clients et frais gouvernementaux.

### Tâches
- [ ] Intégration Stripe (paiements récurrents et one-shot)
- [ ] Suivi frais IRCC par dossier
- [ ] Factures automatiques
- [ ] Rappels de paiement automatiques
- [ ] Tableau de bord financier

---

## Issue #22 — Base de connaissances IA (chatbot RAG)
**Labels:** `ai`, `feature`, `phase-5`
**Priorité:** 🔵 Basse

### Description
Assistant IA interne répondant aux questions sur les procédures IRCC.

### Tâches
- [ ] Ingestion des documents IRCC dans pgvector (chunking sémantique)
- [ ] Pipeline RAG : recherche hybride + reranking + génération
- [ ] Interface chatbot dans le dashboard
- [ ] Citations des sources (liens vers les pages IRCC)
- [ ] Mise à jour automatique quand le monitoring détecte des changements
- [ ] Historique des conversations

---

## Issue #23 — Tests, sécurité et conformité PIPEDA
**Labels:** `security`, `testing`, `phase-5`
**Priorité:** 🔵 Basse (mais obligatoire avant production)

### Description
Assurer la qualité, la sécurité et la conformité légale avant le lancement.

### Tâches
- [ ] Tests unitaires (couverture > 80%)
- [ ] Tests d'intégration (API, base de données)
- [ ] Tests E2E (Playwright)
- [ ] Audit de sécurité (OWASP Top 10)
- [ ] Évaluation d'impact sur la vie privée (PIA)
- [ ] Politique de confidentialité et conditions d'utilisation
- [ ] Mécanisme de consentement explicite
- [ ] Droit d'accès et de suppression des données
- [ ] Plan de réponse aux incidents (breach notification)
- [ ] Penetration testing
