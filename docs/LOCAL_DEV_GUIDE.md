# Guide de développement local VisaCanada

**Travailler sur VisaCanada en local - Guide complet**

---

## 🎯 Configuration actuelle

Vous avez déjà :
- ✅ Backend FastAPI sur http://localhost:8000
- ✅ Base de données SQLite (`backend/dev.db`)
- ✅ 3 utilisateurs de test créés
- ✅ Migrations Alembic à jour

---

## 🔧 Démarrage rapide quotidien

### Backend seul (API + Swagger)

```bash
python start.py
```

Ou manuellement :
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Accès** :
- API : http://localhost:8000
- Swagger : http://localhost:8000/docs
- Health : http://localhost:8000/health

### Frontend + Backend (stack complète)

**Terminal 1 - Backend** :
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Frontend** :
```bash
cd frontend
npm run dev
```

**Accès** :
- Frontend : http://localhost:3000
- Backend : http://localhost:8000

---

## 🧪 Tests pendant le développement

### Backend

**Tester un module spécifique** :
```bash
cd backend
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_mfa.py -v
```

**Tester une fonction spécifique** :
```bash
python -m pytest tests/test_auth.py::test_register_success -v
```

**Mode watch (re-run auto)** :
```bash
python -m pytest tests/test_auth.py -v --watch
```

**Avec couverture** :
```bash
python -m pytest tests/test_auth.py --cov=app/api/auth --cov-report=html
# Rapport dans htmlcov/index.html
```

**Lint** :
```bash
ruff check .                    # Vérifier
ruff check . --fix             # Auto-fix
ruff format .                   # Formater code
```

### Frontend

**Tests unitaires** :
```bash
cd frontend
npm run test              # Mode watch
npm run test:run          # Run once
npm run test -- src/components/auth  # Dossier spécifique
```

**Lint + typecheck** :
```bash
npm run lint              # ESLint
npm run typecheck         # TypeScript
npm run lint && npm run typecheck && npm run test:run  # Tout
```

---

## 🗄️ Base de données locale

### SQLite (défaut en dev)

**Fichier** : `backend/dev.db`

**Visualiser avec DB Browser** :
- Télécharger : https://sqlitebrowser.org/
- Ouvrir `backend/dev.db`
- Explorer tables : users, candidates, dossiers, documents, etc.

**Via ligne de commande** :
```bash
cd backend
sqlite3 dev.db

# Exemples requêtes
SELECT * FROM users;
SELECT * FROM dossiers WHERE status = 'actif';
SELECT COUNT(*) FROM documents;
.quit
```

### Migrations Alembic

**Créer une nouvelle migration** :
```bash
cd backend
alembic revision -m "description du changement"
# Éditer le fichier généré dans alembic/versions/
alembic upgrade head
```

**Revenir en arrière** :
```bash
alembic downgrade -1      # 1 migration arrière
alembic downgrade base    # Tout supprimer
```

**Voir historique** :
```bash
alembic history
alembic current
```

**Réinitialiser DB complètement** :
```bash
rm dev.db
alembic upgrade head
python start.py  # Recrée les users de test
```

---

## 🔐 Gestion des comptes

### Créer un nouvel utilisateur

**Via Swagger** (http://localhost:8000/docs) :
1. POST `/auth/register`
2. Body :
```json
{
  "email": "nouveau@test.ca",
  "password": "Password123!",
  "full_name": "Nouveau User",
  "role": "candidat"
}
```

**Via script Python** :
```python
# backend/scripts/create_user.py
import asyncio
from app.core.database import get_db_session
from app.models.user import User, UserRole
from app.core.security import get_password_hash

async def create_user():
    async with get_db_session() as db:
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("Password123!"),
            full_name="Test User",
            role=UserRole.consultant,
            is_active=True
        )
        db.add(user)
        await db.commit()
        print(f"✓ User créé: {user.email}")

asyncio.run(create_user())
```

```bash
cd backend
python scripts/create_user.py
```

### Activer MFA sur un compte

1. Login avec admin ou consultant
2. POST `/auth/mfa/setup` → Récupérer QR code
3. Scanner avec Google Authenticator
4. POST `/auth/mfa/verify-setup` avec code TOTP
5. Sauvegarder backup codes

---

## 📁 Structure projet

```
visacanada/
├── backend/
│   ├── app/
│   │   ├── api/          # Routes FastAPI (25 routers)
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Logique métier
│   │   ├── tasks/        # Celery tasks
│   │   └── core/         # Config, security, database
│   ├── tests/            # 495 tests pytest
│   ├── alembic/          # Migrations DB (19 versions)
│   ├── dev.db            # SQLite local
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/          # Pages Next.js 15
│   │   ├── components/   # Composants React
│   │   └── lib/          # Utils, API client, types
│   ├── tests/            # 89 tests Vitest
│   └── package.json
├── docs/                 # 8 fichiers documentation
├── start.py              # Script démarrage auto
└── render.yaml           # Config déploiement
```

---

## 🛠️ Workflows courants

### Ajouter un nouvel endpoint backend

**1. Créer le router** :
```python
# backend/app/api/mon_feature.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.auth import require_role
from app.models.user import UserRole

router = APIRouter(prefix="/api/mon-feature", tags=["Mon Feature"])

@router.get("/")
async def list_items(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role(UserRole.admin))
):
    return {"items": []}
```

**2. Enregistrer dans main.py** :
```python
# backend/app/main.py
from app.api import mon_feature

app.include_router(mon_feature.router)
```

**3. Créer les tests** :
```python
# backend/tests/test_mon_feature.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_list_items(client: AsyncClient, admin_token: str):
    response = await client.get(
        "/api/mon-feature/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
```

**4. Tester** :
```bash
python -m pytest tests/test_mon_feature.py -v
```

### Ajouter une page frontend

**1. Créer la page** :
```tsx
// frontend/src/app/portal/ma-page/page.tsx
"use client";

import { useAuth } from "@/components/auth/AuthProvider";

export default function MaPage() {
  const { user } = useAuth();

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Ma nouvelle page</h1>
      <p>Bienvenue {user?.full_name}</p>
    </div>
  );
}
```

**2. Ajouter au menu** (si applicable) :
```tsx
// frontend/src/components/layout/Navigation.tsx
<Link href="/portal/ma-page">Ma page</Link>
```

**3. Tester** :
- Ouvrir http://localhost:3000/portal/ma-page
- Vérifier responsive, accessibilité, styles

### Modifier un modèle de données

**1. Modifier le modèle** :
```python
# backend/app/models/candidate.py
class Candidate(Base):
    __tablename__ = "candidates"
    
    # Ajouter nouveau champ
    linkedin_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

**2. Créer migration** :
```bash
cd backend
alembic revision -m "add linkedin_url to candidates"
```

**3. Éditer la migration** :
```python
# backend/alembic/versions/020_add_linkedin.py
def upgrade():
    op.add_column('candidates', sa.Column('linkedin_url', sa.String(255), nullable=True))

def downgrade():
    op.drop_column('candidates', 'linkedin_url')
```

**4. Appliquer** :
```bash
alembic upgrade head
```

---

## 🐛 Debugging

### Backend

**Logs détaillés** :
```python
# backend/app/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Breakpoint Python** :
```python
import pdb; pdb.set_trace()
# Ou
breakpoint()  # Python 3.7+
```

**Logs SQL** :
```python
# backend/app/core/database.py
engine = create_async_engine(
    DATABASE_URL,
    echo=True  # Affiche toutes les requêtes SQL
)
```

### Frontend

**Console React DevTools** :
```tsx
console.log("Debug:", variable);
console.table(array);
console.trace();
```

**Breakpoint Chrome DevTools** :
- F12 → Sources → Placer breakpoint
- Ou ajouter : `debugger;` dans le code

---

## 📦 Dépendances

### Ajouter une dépendance backend

```bash
cd backend
pip install nom-package
pip freeze | grep nom-package  # Voir version
```

Puis ajouter dans `pyproject.toml` :
```toml
[project]
dependencies = [
    "nom-package==1.2.3",
]
```

### Ajouter une dépendance frontend

```bash
cd frontend
npm install nom-package
# Ou pour dev seulement
npm install -D nom-package
```

---

## 🔄 Workflow Git

### Créer une branche feature

```bash
git checkout -b feat/ma-fonctionnalite
```

### Commits réguliers

```bash
git add .
git commit -m "feat(domaine): description du changement

- Détail 1
- Détail 2

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

### Push et PR

```bash
git push -u origin feat/ma-fonctionnalite
gh pr create --title "feat: Ma fonctionnalité" --body "Description"
```

---

## 🎯 Checklist avant commit

Backend :
- [ ] Tests passent : `pytest tests/test_X.py`
- [ ] Lint OK : `ruff check .`
- [ ] Pas de secrets dans le code
- [ ] Migration créée si modèle changé

Frontend :
- [ ] Tests passent : `npm run test:run`
- [ ] Lint OK : `npm run lint`
- [ ] TypeCheck OK : `npm run typecheck`
- [ ] Responsive vérifié (mobile/tablet)
- [ ] Accessibilité (aria-label en français)

---

## 📞 Ressources utiles

**Documentation** :
- FastAPI : https://fastapi.tiangolo.com/
- Next.js : https://nextjs.org/docs
- SQLAlchemy : https://docs.sqlalchemy.org/
- Tailwind : https://tailwindcss.com/docs

**Outils** :
- Swagger local : http://localhost:8000/docs
- DB Browser SQLite : https://sqlitebrowser.org/
- Postman : https://www.postman.com/ (alternative à Swagger)

**Projet** :
- README : `README.md`
- Conventions : `CLAUDE.md`
- Tests : `docs/TEST_PLAN.md`
- Sécurité : `docs/SECURITY_AUDIT.md`

---

**Bon développement ! 🚀**
