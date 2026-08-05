# VisaCanada — instructions projet

Plateforme SaaS de gestion de dossiers d'immigration canadienne (consultants + candidats),
avec vérification documentaire IA, monitoring IRCC et moteur d'échéances.

Langue de travail : **français** (réponses, commits, docs, messages d'erreur utilisateur).
Le code, les noms de symboles et les commentaires restent en **anglais**.

## Stack

| Couche | Technologie |
|---|---|
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind 3, shadcn/ui, lucide-react |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 async, Pydantic v2, Celery |
| DB | PostgreSQL 16 + pgvector (SQLite/aiosqlite en test), Alembic |
| Cache / queue | Redis |
| Externe | Claude API, Azure Document Intelligence, Tesseract, AWS S3 (ca-central-1), Twilio WhatsApp, Gmail API / Microsoft Graph |
| Tests | pytest + pytest-asyncio (backend), Vitest + Testing Library, Playwright e2e (frontend) |
| Lint | ruff (backend, line-length 100), eslint-config-next (frontend) |

## Commandes

Backend (`cd backend`) :

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
ruff check .
python -m pytest tests/test_deadlines.py -q
```

Frontend (`cd frontend`) :

```bash
npm run dev
npm run lint && npm run typecheck && npm run test:run
npm run test:e2e
```

Stack complète : `cd docker && docker-compose up -d` (front 3000, API 8000, Swagger `/docs`).

## Règles de test

- **Backend : lancer les fichiers de tests un par un** (`python -m pytest tests/test_X.py -q`).
  Chaque module crée son propre moteur SQLite sur le même `test.db` et réassigne
  `app.dependency_overrides[get_db]` à l'import : dans un seul process le dernier import
  gagne et le `drop_all` autouse d'un module supprime les tables des autres. Artefact du
  harnais, pas un bug applicatif. La CI fait de même via une boucle sur `tests/test_*.py`.
- `tests/conftest.py` réinitialise le `auth_limiter` (singleton process-wide) autour de chaque
  test, sinon le rate limiter en mémoire renvoie des 429 parasites.
- La suite est entièrement verte (495 tests). Aucun échec toléré : un test rouge est un
  vrai signal.
- `bcrypt` est épinglé `<5` : bcrypt 5 a supprimé `__about__.__version__` que passlib 1.7.4
  lit encore, et passlib retombe alors sur un backend qui refuse tout hachage. Ne pas
  désépingler sans vérifier que passlib supporte bcrypt 5.
- Toute dépendance tierce importée doit figurer dans `pyproject.toml`. L'environnement local
  masque les oublis ; la CI part d'un `pip install -e ".[dev]"` propre.
- Avant de présenter un changement : lint + tests des fichiers touchés. Frontend : les trois
  commandes (`lint`, `typecheck`, `test:run`) car la CI les exige.

## Conventions backend

- Un router par domaine dans `app/api/<domaine>.py`, `prefix` + `tags`, puis enregistrement
  explicite dans `app/main.py` (imports et `include_router` groupés en fin de fichier).
- Autorisation : `Depends(require_role(UserRole.admin, UserRole.consultant))` depuis
  `app.api.auth`. Toute nouvelle route doit déclarer son rôle — pas d'endpoint ouvert.
- Session DB : `db: AsyncSession = Depends(get_db)`, requêtes en `select()` + `await db.execute`,
  `scalar_one_or_none()` pour l'unicité.
- Schémas : Pydantic `BaseModel` dans `app/schemas/` pour les contrats partagés ; les modèles
  courts propres à un endpoint (`XCreate` / `XUpdate`) peuvent rester dans le module d'API.
- Sérialisation : helper `_serialize()` local, dates en `.isoformat()`, enums en `.value`.
- Les réponses exposées aux candidats sont volontairement redactées (pas de score de conformité,
  de fraude ni d'IA) — voir les schémas `*CandidateResponse`.
- Messages `HTTPException` en français sans accents (compatibilité encodage existante).
- Datetimes stockés naïfs UTC (`datetime.now(timezone.utc).replace(tzinfo=None)`).
  Ne pas utiliser `datetime.utcnow()`.
- Logique métier dans `app/services/`, tâches planifiées dans `app/tasks/` (Celery Beat,
  fuseau `America/Toronto`).
- Toute modification de modèle exige une migration Alembic numérotée (`alembic/versions/018_...`).
- Vérifier l'enregistrement d'un router via `app.openapi()["paths"]` — `app.routes[].path`
  ressort vide pour ces routers.

## Conventions frontend

- Client API centralisé dans `src/lib/api.ts` (une fonction exportée par endpoint, `ApiError`
  avec `status`). Ne pas appeler `fetch` directement depuis un composant.
- Types partagés dans `src/lib/types.ts`, helpers purs et testables dans `src/lib/`.
- Composants par domaine : `src/components/<domaine>/`, un test `*.test.tsx` colocalisé.
- Auth côté client : `AuthProvider` + `RequireAuth`, tokens via `src/lib/auth-storage.ts`.
- Styles : classes Tailwind fusionnées avec `cn()` (`src/lib/utils.ts`), jetons sémantiques
  (`bg-destructive/10`, `text-destructive`) plutôt que couleurs brutes.
- Accessibilité obligatoire : `role`, `aria-label` en français, `aria-hidden` sur les icônes
  décoratives. Les composants purement informatifs ne rendent rien quand il n'y a rien à dire.
- Textes d'interface en français avec accents.

## Sécurité et conformité

Données personnelles sensibles (passeports, relevés bancaires, dossiers d'immigration) :
PIPEDA + Loi 25, résidence des données au Canada (`ca-central-1`).

- Ne jamais logger ni renvoyer de PII, de token ou de contenu de document.
- Ne pas lire ni afficher le contenu de `.env` ; se référer aux clés par leur nom.
- Journaliser les accès documents via `AuditLog` (kwargs `entity_type` / `entity_id`).
- La config production échoue au démarrage sur `SECRET_KEY` faible, CORS wildcard ou `debug`.
  Ne pas contourner ces garde-fous.
- Le rate limiter `app/core/rate_limit.py` compte dans Redis (`REDIS_URL`) pour que tous les
  workers partagent la même fenêtre. Si Redis est injoignable il se dégrade vers un compteur
  par process (protection réduite mais l'authentification reste disponible) : ce repli est
  volontaire, ne pas le transformer en échec dur.
- Envoi d'email sortant : `app/services/smtp_sender.py`, configuré par `SMTP_HOST`,
  `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS`. Sans `SMTP_HOST`
  l'application se rabat sur des notifications visibles au tableau de bord uniquement.
  Ne pas confondre avec `app/services/email_service.py`, qui lit les emails IRCC entrants.

## Git

- Branches `feat/...`, commits conventionnels en français :
  `feat(frontend): dashboard multi-consultant + shell applicatif (Lot B)`.
- Jamais de commit direct sur `main` ; PR via `gh pr create`.
- Ne commiter que les fichiers liés au changement, jamais `.env` ni `test.db`.

## État du projet

Les phases 1 à 5 du README sont largement implémentées côté backend (25 routers, 23 fichiers
de tests). Le travail en cours est le frontend, découpé en lots documentés dans `docs/plans/`.
Branche courante : `feat/frontend-auth-dashboard`.
