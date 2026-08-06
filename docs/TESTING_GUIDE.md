# Guide de test VisaCanada

**Guide complet pour tester la plateforme localement et en production**

---

## 🚀 Démarrage rapide

### Option 1 : Docker Compose (recommandé)

```bash
cd docker
docker-compose up -d
```

**Services démarrés** :
- Frontend : http://localhost:3000
- Backend API : http://localhost:8000
- Swagger docs : http://localhost:8000/docs
- PostgreSQL : localhost:5432
- Redis : localhost:6379

**Comptes de test** (voir Section 3) :
- Admin : admin@visacanada.ca / Admin123!
- Consultant : consultant@visacanada.ca / Consultant123!
- Candidat : candidat@visacanada.ca / Candidat123!

---

### Option 2 : Développement local (backend + frontend séparés)

#### Backend

```bash
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Variables d'environnement requises** (`.env`) :
```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/visacanada
SECRET_KEY=votre-secret-key-minimum-32-caracteres
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=sk-ant-...
AZURE_DOC_INTELLIGENCE_ENDPOINT=https://....cognitiveservices.azure.com/
AZURE_DOC_INTELLIGENCE_KEY=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=visacanada-documents
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

**Variables d'environnement requises** (`.env.local`) :
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 🧪 Tests automatisés

### Backend (pytest)

**Lancer tous les tests** (⚠️ un fichier à la fois) :
```bash
cd backend
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_candidates.py -v
python -m pytest tests/test_mfa.py -v
# ... etc pour chaque fichier
```

**Tests par domaine** :
```bash
# Authentification + MFA
python -m pytest tests/test_auth.py tests/test_mfa.py -v

# CRUD métier
python -m pytest tests/test_dossiers.py tests/test_documents.py -v

# IA et compliance
python -m pytest tests/test_verification.py tests/test_compliance.py -v

# Alertes et analytics
python -m pytest tests/test_ircc_alerts.py tests/test_analytics.py -v
```

**Couverture** :
```bash
python -m pytest tests/test_auth.py --cov=app/api --cov-report=html
# Rapport dans htmlcov/index.html
```

**Lint** :
```bash
ruff check .
ruff check . --fix  # Auto-fix
```

---

### Frontend (Vitest + Testing Library)

**Lancer tous les tests** :
```bash
cd frontend
npm run test:run
```

**Mode watch** :
```bash
npm run test
```

**Tests par composant** :
```bash
npm run test -- src/components/auth
npm run test -- src/app/portal
```

**Lint + typecheck** :
```bash
npm run lint
npm run typecheck
npm run test:run
```

---

### E2E (Playwright - à implémenter)

```bash
cd frontend
npm run test:e2e
```

**Scénarios prioritaires** :
- Login + MFA
- Upload document + validation
- RBAC (accès admin/consultant/candidat)
- Chatbot RAG
- Export données

---

## 🔐 Créer des comptes de test

### Via Swagger (http://localhost:8000/docs)

1. **POST /auth/register** :
```json
{
  "email": "test@example.com",
  "password": "Test123!",
  "full_name": "Test User",
  "role": "candidat"
}
```

2. **POST /auth/login** :
```json
{
  "email": "test@example.com",
  "password": "Test123!"
}
```

Copier le `access_token` de la réponse.

3. **Cliquer sur "Authorize"** (🔒 en haut de Swagger) et coller le token.

---

### Via script Python

```python
import asyncio
import httpx

async def create_test_users():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        users = [
            {"email": "admin@test.ca", "password": "Admin123!", "full_name": "Admin Test", "role": "admin"},
            {"email": "consultant@test.ca", "password": "Consultant123!", "full_name": "Consultant Test", "role": "consultant"},
            {"email": "candidat@test.ca", "password": "Candidat123!", "full_name": "Candidat Test", "role": "candidat"},
        ]
        
        for user in users:
            resp = await client.post("/auth/register", json=user)
            print(f"✅ {user['email']} créé : {resp.status_code}")

asyncio.run(create_test_users())
```

---

## 📋 Scénarios de test manuels

### 1. Authentification + MFA

**Scénario** : Admin active MFA et se reconnecte

1. Login admin : http://localhost:3000/login
   - Email : admin@visacanada.ca
   - Password : Admin123!

2. Aller à : http://localhost:3000/portal/settings/mfa

3. Cliquer "Activer MFA"
   - Scanner QR code avec Google Authenticator / Authy
   - OU copier le secret manuel
   - Entrer le code TOTP à 6 chiffres

4. Sauvegarder les 8 backup codes (PDF)

5. Se déconnecter et se reconnecter
   - Entrer email + password
   - Système demande code TOTP
   - Entrer code de l'app (ou backup code)

6. ✅ **Résultat attendu** : Accès au dashboard

---

### 2. Portail candidat complet

**Scénario** : Candidat crée son profil et upload documents

1. Register candidat : http://localhost:3000/register
   - Email : nouveau@test.ca
   - Password : Test123!
   - Nom complet

2. Login : http://localhost:3000/login

3. Compléter profil : http://localhost:3000/portal/profile
   - Numéro passeport
   - Date naissance
   - Nationalité
   - Téléphone
   - Adresse Canada

4. Upload document : http://localhost:3000/portal/documents
   - Cliquer "Upload Document"
   - Sélectionner type : "Passeport"
   - Choisir fichier PDF/JPG (< 10 MB)
   - Ajouter notes (optionnel)
   - Soumettre

5. Vérifier dashboard : http://localhost:3000/portal
   - 1 dossier actif
   - 1 document uploadé
   - Statut "pending"

6. ✅ **Résultat attendu** : Document visible dans la liste avec statut

---

### 3. Consultant gère un candidat

**Scénario** : Consultant crée un dossier et vérifie un document

1. Login consultant : http://localhost:3000/login
   - consultant@visacanada.ca / Consultant123!

2. Dashboard : http://localhost:3000/portal
   - Voir statistiques (dossiers actifs, taux approbation)
   - Charts par statut et programme

3. Liste candidats : http://localhost:3000/portal/candidates
   - Cliquer sur un candidat

4. Créer dossier : http://localhost:3000/portal/dossiers/new
   - Candidat : sélectionner
   - Programme : "Express Entry - FSW"
   - Description
   - Date limite
   - Soumettre

5. Vérifier document : Documents > Actions > Vérifier
   - IA lance analyse (Claude + Azure OCR)
   - Voir score conformité (0-100)
   - Voir issues détectées
   - Approuver / Rejeter

6. ✅ **Résultat attendu** : Dossier créé, document vérifié avec score

---

### 4. Alertes IRCC

**Scénario** : Configurer alertes pour un programme

1. Login consultant

2. Aller à : http://localhost:3000/portal/alerts

3. Configurer alerte :
   - Programme : "Entrée Express"
   - Types : Quotas + Délais + Exigences
   - Activer

4. Voir historique : 90 derniers jours de changements IRCC

5. Backend : Task Celery Beat scanne IRCC quotidiennement

6. ✅ **Résultat attendu** : Alertes visibles, historique affiché

---

### 5. Dashboard analytics

**Scénario** : Consultant consulte statistiques

1. Login consultant

2. Dashboard : http://localhost:3000/portal

3. KPIs :
   - Dossiers actifs
   - Taux approbation
   - Revenus mensuels
   - Documents en attente

4. Filtres temporels : 7j / 30j / 90j / 365j / Tout

5. Charts :
   - Répartition par statut (pie chart)
   - Répartition par programme (bar chart)
   - Timeline (line chart)

6. Export CSV : Télécharger données filtrées

7. Export PDF : Générer rapport avec ReportLab

8. ✅ **Résultat attendu** : KPIs corrects, charts interactifs, exports fonctionnels

---

### 6. Chatbot RAG

**Scénario** : Candidat pose questions sur démarches IRCC

1. Login candidat

2. Aller à : http://localhost:3000/portal/chat

3. Poser questions :
   - "Comment fonctionne Entrée Express ?"
   - "Quels documents pour PVT ?"
   - "Délais de traitement résidence permanente ?"

4. Chatbot :
   - Recherche sémantique pgvector
   - Génère réponse via Claude
   - Cite sources base de connaissances

5. Admin : http://localhost:3000/admin/knowledge-base
   - Ajouter article
   - Programme : Express Entry
   - Contenu markdown

6. ✅ **Résultat attendu** : Réponses précises avec sources

---

### 7. Conformité PIPEDA

**Scénario** : Candidat exerce ses droits

1. Login candidat

2. **Politique de confidentialité** : http://localhost:3000/privacy
   - Lire 12 sections
   - Vérifier liens vers export/plainte

3. **Export données** : http://localhost:3000/portal/export
   - Cliquer "Télécharger mes données"
   - Recevoir JSON complet :
     - Profil utilisateur
     - Profil candidat
     - Dossiers
     - Documents (métadonnées)
     - Audit logs

4. **Déposer plainte** : http://localhost:3000/portal/complaint
   - Sujet : "Accès non autorisé"
   - Description
   - Soumettre
   - Admin reçoit email notification

5. Admin : Backend `/admin/complaints`
   - Voir plaintes
   - Répondre
   - Résoudre

6. ✅ **Résultat attendu** : Export JSON complet, plainte enregistrée

---

## 🐛 Tests de sécurité

### Rate limiting

```bash
# Tester 10 tentatives login rapides
for i in {1..10}; do
  curl -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@test.ca","password":"wrong"}'
done
# Attendu : 429 Too Many Requests après 5 tentatives
```

### RBAC

```bash
# Candidat tente d'accéder endpoint admin
TOKEN_CANDIDAT="..." # Token d'un candidat
curl http://localhost:8000/admin/users \
  -H "Authorization: Bearer $TOKEN_CANDIDAT"
# Attendu : 403 Forbidden
```

### Validation upload

1. Tenter upload fichier > 10 MB
2. Tenter upload type non autorisé (.exe)
3. Tenter upload avec nom malicieux (`../../etc/passwd`)

**Attendu** : 400 Bad Request avec message d'erreur

---

## 📊 Monitoring en production

### Health check

```bash
curl http://localhost:8000/health
# {"status": "healthy", "database": "connected", "redis": "connected"}
```

### Logs audit

```sql
-- PostgreSQL : voir dernières actions
SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 100;
```

### Métriques Redis

```bash
redis-cli INFO stats
```

---

## 🔥 Tests de charge (optionnel)

### Locust (à installer)

```python
# locustfile.py
from locust import HttpUser, task, between

class VisaCanadaUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        resp = self.client.post("/auth/login", json={
            "email": "test@test.ca",
            "password": "Test123!"
        })
        self.token = resp.json()["access_token"]
    
    @task
    def get_dashboard(self):
        self.client.get("/portal/dashboard", headers={
            "Authorization": f"Bearer {self.token}"
        })
    
    @task
    def list_dossiers(self):
        self.client.get("/api/dossiers", headers={
            "Authorization": f"Bearer {self.token}"
        })
```

```bash
locust -f locustfile.py --host http://localhost:8000
# Ouvrir http://localhost:8089
# Configurer : 100 users, spawn rate 10
```

---

## ✅ Checklist de test complète

### Backend
- [ ] Tous les tests pytest passent (495 tests)
- [ ] Ruff lint sans erreur
- [ ] Health check retourne 200
- [ ] Swagger docs accessibles
- [ ] Rate limiting fonctionne
- [ ] RBAC bloque accès non autorisés
- [ ] MFA setup + login fonctionnent
- [ ] Upload validation refuse fichiers invalides
- [ ] Export données retourne JSON complet
- [ ] Plaintes enregistrées + email admin

### Frontend
- [ ] Tous les tests Vitest passent (89 tests)
- [ ] ESLint + TypeCheck sans erreur
- [ ] Login + logout fonctionnent
- [ ] MFA setup avec QR code
- [ ] Upload document avec preview
- [ ] Dashboard charts affichés
- [ ] Chatbot répond correctement
- [ ] Export télécharge JSON
- [ ] Politique de confidentialité affichée
- [ ] Responsive mobile (Tailwind)

### Sécurité
- [ ] Pas de secrets dans logs
- [ ] HTTPS en production
- [ ] CORS configuré (pas de wildcard)
- [ ] JWT expirent (24h)
- [ ] Passwords hashed (bcrypt)
- [ ] S3 bucket privé (pas de public access)
- [ ] Rate limiting actif (Redis)
- [ ] Validation Pydantic stricte

### Compliance
- [ ] EFVP complet
- [ ] INCIDENT_RESPONSE_PLAN testé (drill)
- [ ] DPA signés (Anthropic, Azure, AWS)
- [ ] IMO désigné formellement
- [ ] Registre incidents vide
- [ ] Audit logs enregistrent actions sensibles

---

## 🆘 Dépannage

### Backend ne démarre pas

**Erreur** : `SECRET_KEY must be at least 32 characters`
**Solution** : Générer clé forte :
```bash
openssl rand -hex 32
# Copier dans .env
```

**Erreur** : `redis.exceptions.ConnectionError`
**Solution** : Démarrer Redis :
```bash
docker run -d -p 6379:6379 redis:alpine
```

**Erreur** : `asyncpg.exceptions.InvalidCatalogNameError`
**Solution** : Créer base de données :
```bash
psql -U postgres -c "CREATE DATABASE visacanada;"
alembic upgrade head
```

---

### Frontend ne démarre pas

**Erreur** : `NEXT_PUBLIC_API_URL is not defined`
**Solution** : Créer `.env.local` :
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Erreur** : `Module not found: Can't resolve 'lucide-react'`
**Solution** :
```bash
rm -rf node_modules package-lock.json
npm install
```

---

### Tests backend échouent

**Erreur** : `database is locked`
**Solution** : Lancer 1 fichier de test à la fois (isolation SQLite)

**Erreur** : `429 Too Many Requests`
**Solution** : `tests/conftest.py` reset le rate limiter, vérifier qu'il est exécuté

---

### Docker Compose échoue

**Erreur** : `port 5432 already in use`
**Solution** : Arrêter PostgreSQL local :
```bash
sudo systemctl stop postgresql  # Linux
brew services stop postgresql   # Mac
```

**Erreur** : `no configuration file provided`
**Solution** : Vérifier `docker/.env` existe

---

## 📞 Support

**Documentation** :
- Backend API : http://localhost:8000/docs
- Frontend : http://localhost:3000
- Logs backend : `backend/logs/`
- Logs frontend : Console navigateur

**Contacts** :
- Issues GitHub : https://github.com/romuald2/visacanada/issues
- Email : support@visacanada.ca

---

*Document généré le 2026-08-05 par Claude Opus 5*
