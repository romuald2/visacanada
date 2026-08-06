# Guide de déploiement VisaCanada

**Options de déploiement pour la plateforme VisaCanada**

---

## 🚫 Pourquoi pas Vercel ?

Vercel est **incompatible** avec VisaCanada pour ces raisons :

| Fonctionnalité | Requis | Vercel | Statut |
|----------------|--------|--------|--------|
| Backend Python FastAPI | ✅ | ❌ Limité à 10s timeout | ❌ |
| PostgreSQL hébergé | ✅ | ❌ Service externe requis | ⚠️ |
| Redis | ✅ | ❌ Service externe requis | ⚠️ |
| Celery workers | ✅ | ❌ Pas de background jobs | ❌ |
| Upload > 10 MB | ✅ | ❌ Limite 4.5 MB body | ❌ |
| WebSocket temps réel | ✅ | ❌ Pas supporté Python | ❌ |

**Verdict** : Vercel peut héberger le frontend Next.js uniquement, pas le backend complet.

---

## ✅ Options recommandées

### Option 1 : Railway (recommandé) 💎

**Le plus simple et le plus complet**

#### Avantages
- ✅ Déploiement Git automatique
- ✅ PostgreSQL + Redis inclus gratuit
- ✅ Support natif Celery workers
- ✅ HTTPS automatique
- ✅ Variables d'environnement chiffrées
- ✅ Logs temps réel
- ✅ Rollback 1-clic
- ✅ Free tier : 500h/mois ($5 crédits)

#### Déploiement

**1. Installer Railway CLI**
```bash
npm install -g @railway/cli
railway login
```

**2. Créer projet**
```bash
railway init
railway add  # Sélectionner PostgreSQL + Redis
```

**3. Configurer variables d'environnement**
```bash
railway variables set SECRET_KEY="votre-cle-32-caracteres"
railway variables set ANTHROPIC_API_KEY="sk-ant-..."
railway variables set AZURE_DOC_INTELLIGENCE_ENDPOINT="https://..."
railway variables set AZURE_DOC_INTELLIGENCE_KEY="..."
railway variables set AWS_ACCESS_KEY_ID="..."
railway variables set AWS_SECRET_ACCESS_KEY="..."
railway variables set S3_BUCKET_NAME="visacanada-prod"
railway variables set CORS_ORIGINS="https://votre-frontend.railway.app"
```

**4. Déployer**
```bash
railway up
```

**5. Obtenir l'URL**
```bash
railway domain
# Exemple : https://visacanada-backend-production.up.railway.app
```

**6. Déployer frontend**
```bash
cd frontend
railway init
railway variables set NEXT_PUBLIC_API_URL="https://votre-backend.railway.app"
railway up
```

#### Configuration Railway (automatique)
Railway détecte automatiquement :
- `backend/` → Python + uvicorn
- `frontend/` → Node.js + Next.js
- `requirements.txt` ou `pyproject.toml` → pip install
- `package.json` → npm install

#### Coût
- **Free tier** : 500h/mois ($5 crédits gratuits)
- **Starter** : $5/mois (illimité)
- **Pro** : $20/mois (high performance)

**Pour débuter** : Free tier suffit pour dev/staging

---

### Option 2 : Render.com 🎨

**Alternative gratuite avec limites**

#### Avantages
- ✅ Free tier PostgreSQL (500 MB)
- ✅ Free tier Redis (25 MB)
- ✅ Support Celery workers
- ✅ HTTPS automatique
- ✅ Déploiement Git
- ✅ Configuration `render.yaml` (IaC)

#### Déploiement

**1. Push `render.yaml` sur GitHub**
```bash
git add render.yaml
git commit -m "feat: configuration Render.com"
git push
```

**2. Créer compte sur Render.com**
- Aller sur https://render.com
- Sign up avec GitHub

**3. New Blueprint**
- Connecter repository `visacanada`
- Render détecte `render.yaml`
- Cliquer "Apply"

**4. Configurer variables sensibles**
Dans Render Dashboard :
- Aller dans chaque service
- Environment → Add Secret Files
- Ajouter :
  - `ANTHROPIC_API_KEY`
  - `AZURE_DOC_INTELLIGENCE_KEY`
  - `AWS_SECRET_ACCESS_KEY`

**5. Déployer**
Render déploie automatiquement :
- Backend FastAPI
- Frontend Next.js
- Celery Worker
- Celery Beat
- PostgreSQL
- Redis

#### Limites Free Tier
- ⚠️ Services s'endorment après 15 min inactivité (réveil = 30s)
- ⚠️ 750h/mois de compute gratuit
- ⚠️ PostgreSQL limité à 90 jours (puis payant $7/mois)

#### Coût
- **Free** : 750h/mois + DB 90j gratuit
- **Starter** : $7/mois/service + DB $7/mois
- **Production complète** : ~$35/mois (backend + frontend + worker + beat + DB + Redis)

---

### Option 3 : Fly.io 🚀

**Le plus flexible (Docker)**

#### Avantages
- ✅ Support Docker natif
- ✅ Multi-région (Canada inclus)
- ✅ PostgreSQL + Redis managed
- ✅ Scale automatique
- ✅ Free tier : 3 VM + 3 GB persistent storage

#### Déploiement

**1. Installer Fly CLI**
```bash
curl -L https://fly.io/install.sh | sh  # Linux/Mac
# Windows : https://fly.io/docs/hands-on/install-flyctl/
```

**2. Login**
```bash
fly auth login
```

**3. Backend**
```bash
cd backend
fly launch  # Détecte Python automatiquement
fly deploy
```

**4. PostgreSQL**
```bash
fly postgres create --name visacanada-db
fly postgres attach visacanada-db
```

**5. Redis**
```bash
fly redis create --name visacanada-redis
```

**6. Frontend**
```bash
cd frontend
fly launch
fly deploy
```

#### Coût
- **Free** : 3 VM 256 MB + 3 GB storage
- **Production** : ~$20-40/mois selon trafic

---

### Option 4 : AWS (production entreprise) ☁️

**Pour conformité Loi 25 stricte**

#### Architecture
- **Backend** : ECS Fargate (ca-central-1)
- **Frontend** : CloudFront + S3
- **Database** : RDS PostgreSQL (ca-central-1)
- **Cache** : ElastiCache Redis (ca-central-1)
- **Storage** : S3 (ca-central-1)
- **Workers** : ECS Fargate (Celery)

#### Avantages
- ✅ **Résidence données 100% Canada** (Montréal)
- ✅ Conformité Loi 25 garantie
- ✅ Haute disponibilité (multi-AZ)
- ✅ Auto-scaling
- ✅ CloudWatch logs centralisés
- ✅ IAM fine-grained

#### Déploiement
Complexe, nécessite :
- Terraform ou CloudFormation
- VPC + Security Groups
- Load balancer
- CI/CD (GitHub Actions → ECR → ECS)

#### Coût
- **Dev/staging** : ~$50-100/mois
- **Production** : ~$200-500/mois selon trafic

---

## 📊 Comparatif

| Critère | Railway | Render | Fly.io | AWS |
|---------|---------|--------|--------|-----|
| **Simplicité** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| **Coût free tier** | $5 crédits | Gratuit 90j | Gratuit | Gratuit 12m |
| **Coût production** | $5-20/mois | $35/mois | $20-40/mois | $200+/mois |
| **Setup temps** | 10 min | 15 min | 30 min | 2-4h |
| **Celery support** | ✅ Natif | ✅ Natif | ✅ Docker | ✅ ECS |
| **Résidence Canada** | ❌ US | ❌ US | ✅ ca-central | ✅ ca-central |
| **Loi 25 compliant** | ⚠️ DPA requis | ⚠️ DPA requis | ✅ Oui | ✅ Oui |
| **Auto-scaling** | ✅ | ❌ | ✅ | ✅ |
| **Rollback 1-clic** | ✅ | ✅ | ✅ | ❌ Manuel |

---

## 🎯 Recommandation finale

### Pour développement/MVP
**→ Railway** (le plus simple)
```bash
npm install -g @railway/cli
railway login
railway init
railway up
```
**Coût** : Gratuit ($5 crédits) ou $5/mois

### Pour production (< 1000 users)
**→ Render.com** (bon rapport qualité/prix)
```bash
git push  # Auto-déploiement via render.yaml
```
**Coût** : $35/mois (4 services + DB + Redis)

### Pour production (conformité Loi 25 stricte)
**→ Fly.io région ca-central** ou **AWS ca-central-1**
- Résidence données 100% Canada
- Conforme Loi 25 Article 3.4
- DPA avec hébergeur

---

## 🔧 Configuration post-déploiement

**Après déploiement, vérifier** :

1. **Variables d'environnement**
```bash
# Backend
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
SECRET_KEY=...
ANTHROPIC_API_KEY=...
CORS_ORIGINS=https://frontend-url.com
```

2. **Migrations**
```bash
railway run alembic upgrade head  # Railway
# OU
render exec backend alembic upgrade head  # Render
```

3. **Health check**
```bash
curl https://votre-backend.railway.app/health
# Doit retourner : {"status": "healthy", "database": "connected", "redis": "connected"}
```

4. **Créer utilisateur admin**
```bash
railway run python -c "
import asyncio
from app.core.database import get_db_session
from app.models.user import User
from app.core.security import get_password_hash

async def create_admin():
    async with get_db_session() as db:
        admin = User(
            email='admin@visacanada.ca',
            hashed_password=get_password_hash('Admin123!'),
            full_name='Admin',
            role='admin',
            is_active=True
        )
        db.add(admin)
        await db.commit()
        print('Admin créé')

asyncio.run(create_admin())
"
```

5. **Tester frontend**
- Ouvrir `https://votre-frontend.railway.app`
- Login avec admin@visacanada.ca
- Vérifier dashboard charge

---

## 📝 Checklist pré-production

- [ ] DPA signés (Anthropic, Azure, AWS, hébergeur)
- [ ] IMO désigné formellement
- [ ] Variables sensibles chiffrées
- [ ] HTTPS activé (certificat SSL)
- [ ] CORS configuré (pas de wildcard)
- [ ] Rate limiting actif (Redis)
- [ ] Backups DB automatiques (quotidiens)
- [ ] Monitoring logs (Sentry, LogDNA)
- [ ] Alertes erreurs 5xx
- [ ] Tests de charge (Locust)
- [ ] Plan de reprise après sinistre

---

**Quelle option préférez-vous ?**
1. **Railway** (déploiement immédiat, 10 min)
2. **Render** (gratuit 90j, configuration IaC)
3. **Fly.io** (Canada région, conformité Loi 25)
4. **AWS** (production entreprise, $$$)
