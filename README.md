# 🇨🇦 VisaCanada — Plateforme IA de Gestion d'Immigration

Application web intelligente pour accompagner les candidats à l'immigration canadienne, avec des agents IA pour automatiser la gestion des dossiers de A à Z.

## 🎯 Vision

Plateforme SaaS permettant aux consultants en immigration de gérer efficacement leurs dossiers clients grâce à l'IA : vérification automatique des documents, suivi des procédures IRCC, notifications intelligentes et aide au remplissage des formulaires.

## ✨ Fonctionnalités Principales

### 1. Gestion des programmes d'immigration
- Liste complète des programmes IRCC (Express Entry, PNP, IEC/PVT, Permis d'études, etc.)
- Documents requis par programme, mis à jour automatiquement
- Monitoring IRCC 2-3x/semaine pour détecter les changements de politique

### 2. Vérification intelligente des documents
- Analyse IA de conformité avec score sur 100%
- OCR et extraction automatique des données (passeports, relevés bancaires, diplômes)
- Détection de documents falsifiés (métadonnées, cohérence visuelle, cross-référencement)

### 3. Aide au remplissage de profil IRCC
- Pré-remplissage intelligent basé sur les documents du candidat
- Détection des informations manquantes ou non conformes
- Validation avant soumission

### 4. Monitoring email et notifications
- Connexion aux boîtes email des candidats (Gmail, Outlook)
- Détection automatique des emails IRCC
- Notifications admin via Dashboard + WhatsApp

### 5. Gestion des dossiers candidats
- Dossier unique par candidat avec tous ses documents
- Suivi de l'avancement de la procédure
- Historique complet des actions

## 🏗️ Architecture Technique

```
Frontend:      Next.js 15 (App Router, TypeScript, Tailwind, shadcn/ui)
Backend:       Python FastAPI (async, Pydantic, Celery)
Database:      PostgreSQL 16 (pgvector, JSONB, RLS)
Cache/Queue:   Redis (caching, jobs, notifications)
Stockage:      AWS S3 (ca-central-1, chiffré AES-256)
OCR:           Azure Document Intelligence + Tesseract
IA/LLM:        Claude API (Anthropic)
Agents IA:     LangGraph (orchestration multi-agents)
RAG:           pgvector + recherche hybride
WhatsApp:      Twilio WhatsApp Business API
Email:         Gmail API + Microsoft Graph
Auth:          NextAuth.js + RBAC
Déploiement:   AWS ca-central-1 (résidence données Canada)
CI/CD:         GitHub Actions
Monitoring:    Sentry + LangSmith
```

## 📋 Programmes IRCC Supportés

| Programme | Description |
|-----------|-------------|
| Express Entry | FSW, CEC, FST — immigration économique fédérale |
| PNP | Programmes des Nominees Provinciaux (11 provinces) |
| IEC/PVT | Working Holiday, Young Professionals, Co-op |
| Permis d'études | Incluant les nouvelles règles PAL 2024 |
| Permis de travail | LMIA + Programme de Mobilité Internationale |
| Parrainage familial | Conjoint, parents, grands-parents, enfants |
| Super Visa | Visa multi-entrées parents/grands-parents |
| Visa temporaire | Visa de résident temporaire |
| Réfugiés | GAR, PSR, BVOR, demandes d'asile |

## 🚀 Phases de Développement

### Phase 1 — Fondations (Semaines 1-4)
- Setup projet (Next.js + FastAPI + PostgreSQL + Docker)
- Authentification et gestion des rôles (Admin, Consultant, Candidat)
- Modèle de données (candidats, dossiers, documents, programmes)
- CRUD dossiers candidats

### Phase 2 — Intelligence documentaire (Semaines 5-8)
- Base de connaissances IRCC (programmes + documents requis)
- Monitoring IRCC (flux RSS/Atom + Open Data)
- Upload et stockage sécurisé des documents (S3, chiffrement)
- OCR et extraction de données (Azure Document Intelligence)
- Vérification de conformité IA (score sur 100%)
- Détection de documents falsifiés

### Phase 3 — Automatisation (Semaines 9-12)
- Aide au remplissage de profil IRCC
- Connexion email candidats (Gmail API + Microsoft Graph)
- Notifications WhatsApp Business API
- Dashboard admin (vue globale des dossiers)

### Phase 4 — Fonctionnalités avancées (Semaines 13-16)
- Calculateur de points CRS (Express Entry)
- Génération automatique de lettres (motivation, explication)
- Portail candidat (lecture seule)
- Système d'alertes intelligentes (deadlines, rondes EE, changements IRCC)
- Analytics et reporting

### Phase 5 — Polish (Semaines 17-20)
- Dossiers familiaux multi-candidats
- Gestion des paiements et facturation
- Base de connaissances IA (chatbot RAG)
- Tests, sécurité, conformité PIPEDA/Loi 25

## 🔒 Sécurité et Conformité

- **PIPEDA** : Conformité loi fédérale sur la protection des données
- **Loi 25 (Québec)** : Évaluation d'impact sur la vie privée
- **Résidence des données** : Hébergement exclusif au Canada (AWS ca-central-1)
- **Chiffrement** : AES-256 au repos, TLS 1.3 en transit
- **RBAC** : Contrôle d'accès basé sur les rôles
- **Audit** : Journalisation complète des accès aux documents

## 🛠️ Installation

### Prérequis
- Docker & Docker Compose
- Node.js 20+ (pour le développement frontend)
- Python 3.12+ (pour le développement backend)

### Démarrage rapide (Docker)

```bash
# Cloner le repo
git clone https://github.com/romuald2/visacanada.git
cd visacanada

# Copier les variables d'environnement
cp .env.example .env

# Lancer tous les services
cd docker
docker-compose up -d
```

L'application sera accessible sur :
- Frontend : http://localhost:3000
- Backend API : http://localhost:8000
- API Docs (Swagger) : http://localhost:8000/docs

### Développement local (sans Docker)

**Backend :**
```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

**Frontend :**
```bash
cd frontend
npm install
npm run dev
```

### Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm run test:run
```

## 📁 Structure du Projet

```
visacanada/
├── frontend/              # Next.js 15 (App Router)
│   ├── src/
│   │   ├── app/           # Pages et layouts
│   │   ├── components/    # Composants React
│   │   └── lib/           # Utilitaires
│   └── package.json
├── backend/               # Python FastAPI
│   ├── app/
│   │   ├── api/           # Routes API
│   │   ├── core/          # Config, sécurité
│   │   ├── models/        # Modèles SQLAlchemy
│   │   └── services/      # Logique métier
│   ├── alembic/           # Migrations DB
│   ├── tests/             # Tests pytest
│   └── pyproject.toml
├── docker/                # Docker Compose + Dockerfiles
├── .github/workflows/     # CI/CD GitHub Actions
└── .env.example           # Variables d'environnement
```

## 📄 Licence

Propriétaire — Tous droits réservés.
