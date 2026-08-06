# Plan de tests - VisaCanada

**Date**: 2026-08-05  
**Objectif**: Assurer la qualité, la sécurité et la conformité PIPEDA

---

## 1. État actuel des tests

### 1.1 Couverture backend

**Total**: 509 tests  
**Status**: ~60% passants (échecs liés à l'isolation des fixtures SQLite)

#### Tests passants (exemples)
- ✅ **Compliance** (17/17): Scoring, règles de conformité, détection fraude
- ✅ **Analytics service** (8/8): Agrégations, export CSV/PDF
- ✅ **Deadlines**: Calcul échéances, événements IRCC
- ✅ **Auth validation**: Email invalide, mot de passe faible
- ✅ **Billing logic**: Calcul totaux, taxes, statuts paiement

#### Tests échouants (à investiguer)
- ❌ **API tests**: Échecs dus à l'isolation des fixtures (voir `CLAUDE.md`)
- ❌ **Auth API**: `test_register_success`, `test_login_success` (db override)
- ❌ **Alerts API**: 15 échecs (service layer OK, API layer échoue)
- ❌ **Billing API**: Échecs similaires

**Cause**: Chaque module de test réassigne `app.dependency_overrides[get_db]` à l'import. Dans un seul process pytest, le dernier import gagne et le `drop_all` autouse d'un module supprime les tables des autres.

**Solution**: Exécuter les tests un fichier à la fois (déjà documenté dans `CLAUDE.md`):
```bash
for f in tests/test_*.py; do
  python -m pytest "$f" -q || echo "FAIL: $f"
done
```

### 1.2 Couverture frontend

**Status**: Minimal  
**Fichiers**: `src/components/auth/AuthProvider.test.tsx`, `RequireAuth.test.tsx`, etc.

#### Tests existants
- ✅ **AuthProvider**: Login, logout, refresh
- ✅ **RequireAuth**: Redirection si non authentifié
- ✅ **CriticalBadge**: Rendu badge critique
- ✅ **DossierList**: Rendu liste, filtres
- ✅ **UpcomingDeadlines**: Affichage deadlines

#### Tests manquants
- ❌ **Pages complètes**: `/dashboard`, `/dossiers`, `/alerts`, `/chat`, `/knowledge`
- ❌ **Forms**: Validation, soumission, gestion erreurs
- ❌ **API client**: Gestion erreurs 401, 403, 500

---

## 2. Tests de sécurité à ajouter

### 2.1 Authentification & Autorisation

#### Backend

**Fichier**: `tests/test_security_auth.py`

```python
import pytest
from fastapi import status

class TestAuthSecurity:
    """Tests de sécurité pour l'authentification."""
    
    async def test_rate_limiting_login(self, client):
        """Rate limiter bloque après 5 tentatives en 1 minute."""
        for i in range(6):
            resp = await client.post("/auth/login", json={
                "email": "test@example.com",
                "password": "wrong"
            })
            if i < 5:
                assert resp.status_code in [401, 429]
            else:
                assert resp.status_code == 429
    
    async def test_jwt_expiration(self, client, db, admin_user):
        """Token expiré est rejeté."""
        # Créer token expiré (manipulation manuelle ou mock time)
        expired_token = create_access_token(
            {"sub": admin_user.email},
            expires_delta=timedelta(seconds=-1)
        )
        resp = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_refresh_token_rotation(self, client, db, admin_user):
        """Refresh token est rotaté après usage."""
        # Login
        resp1 = await client.post("/auth/login", json={
            "email": admin_user.email,
            "password": "password123"
        })
        refresh1 = resp1.json()["refresh_token"]
        
        # Refresh
        resp2 = await client.post("/auth/refresh", json={
            "refresh_token": refresh1
        })
        assert resp2.status_code == 200
        refresh2 = resp2.json()["refresh_token"]
        assert refresh1 != refresh2
        
        # Ancien refresh token doit être invalide
        resp3 = await client.post("/auth/refresh", json={
            "refresh_token": refresh1
        })
        assert resp3.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_candidat_cannot_access_admin_endpoints(self, client, db, candidat_user, candidat_token):
        """Candidat ne peut pas accéder aux endpoints admin."""
        admin_endpoints = [
            "/analytics/overview",
            "/billing/invoices",
            "/knowledge/documents",
            "/alerts/scan",
        ]
        for endpoint in admin_endpoints:
            resp = await client.get(
                endpoint,
                headers={"Authorization": f"Bearer {candidat_token}"}
            )
            assert resp.status_code == status.HTTP_403_FORBIDDEN
    
    async def test_candidat_isolation(self, client, db, candidat_user, candidat_token, other_candidat):
        """Candidat A ne peut pas accéder au dossier de candidat B."""
        # Créer dossier pour other_candidat
        other_dossier = Dossier(
            candidate_id=other_candidat.id,
            program_id=1,
            status="en_cours"
        )
        db.add(other_dossier)
        await db.commit()
        
        # Candidat A tente d'accéder au dossier de B
        resp = await client.get(
            f"/portal/dossiers/{other_dossier.id}",
            headers={"Authorization": f"Bearer {candidat_token}"}
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
```

#### Frontend

**Fichier**: `frontend/src/components/auth/RequireAuth.test.tsx`

```typescript
describe('RequireAuth - RBAC', () => {
  it('redirige candidat vers /portal si tentative accès /analytics', () => {
    const mockUser: User = {
      id: 1,
      email: 'candidat@example.com',
      role: 'candidat',
      full_name: 'Test Candidat',
      is_active: true,
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    };
    
    render(
      <AuthProvider value={{ user: mockUser, loading: false, ... }}>
        <RequireAuth allowedRoles={['admin', 'consultant']}>
          <div>Analytics Page</div>
        </RequireAuth>
      </AuthProvider>
    );
    
    expect(mockNavigate).toHaveBeenCalledWith('/portal');
  });
});
```

### 2.2 Validation des entrées

#### Backend

**Fichier**: `tests/test_security_validation.py`

```python
class TestInputValidation:
    """Tests de validation et prévention injection."""
    
    async def test_sql_injection_email(self, client):
        """Tentative d'injection SQL dans email est rejetée."""
        resp = await client.post("/auth/register", json={
            "email": "admin'--@example.com",
            "password": "password123",
            "full_name": "Test",
            "role": "candidat"
        })
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_xss_in_notes(self, client, db, consultant_user, consultant_token, dossier):
        """Script XSS dans notes est échappé."""
        malicious_notes = "<script>alert('XSS')</script>"
        resp = await client.patch(
            f"/dossiers/{dossier.id}",
            json={"notes": malicious_notes},
            headers={"Authorization": f"Bearer {consultant_token}"}
        )
        assert resp.status_code == 200
        
        # Vérifier que le script n'est pas exécutable
        dossier_data = resp.json()
        # Notes devraient être échappées ou nettoyées
        assert "<script>" not in dossier_data["notes"] or \
               dossier_data["notes"] == html.escape(malicious_notes)
    
    async def test_file_upload_executable_rejected(self, client, db, candidat_user, candidat_token, dossier):
        """Upload d'un exécutable déguisé en PDF est rejeté."""
        # Créer un fichier avec extension .pdf mais magic bytes d'un .exe
        fake_pdf = b"MZ\x90\x00" + b"\x00" * 1000  # Magic bytes PE/COFF
        
        resp = await client.post(
            f"/portal/dossiers/{dossier.id}/documents",
            files={"file": ("malware.pdf", fake_pdf, "application/pdf")},
            data={"requirement_id": 1},
            headers={"Authorization": f"Bearer {candidat_token}"}
        )
        # Devrait être rejeté par validation MIME
        assert resp.status_code in [400, 415, 422]
    
    async def test_path_traversal_document_name(self, client, db, candidat_user, candidat_token, dossier):
        """Path traversal dans nom de fichier est bloqué."""
        resp = await client.post(
            f"/portal/dossiers/{dossier.id}/documents",
            files={"file": ("../../../etc/passwd", b"content", "text/plain")},
            data={"requirement_id": 1},
            headers={"Authorization": f"Bearer {candidat_token}"}
        )
        # Devrait être rejeté ou sanitizé
        if resp.status_code == 200:
            doc = resp.json()
            assert "../" not in doc["filename"]
```

### 2.3 Données sensibles

#### Backend

**Fichier**: `tests/test_security_data_protection.py`

```python
class TestDataProtection:
    """Tests de protection des données sensibles."""
    
    async def test_logs_no_pii(self, client, caplog):
        """Logs ne contiennent pas de PII."""
        await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "SecretPass123"
        })
        
        # Vérifier que password n'est pas loggé
        for record in caplog.records:
            assert "SecretPass123" not in record.message
            assert "test@example.com" not in record.message or \
                   record.levelname == "INFO"  # Email peut être en INFO, pas password
    
    async def test_error_no_stack_trace_production(self, client, monkeypatch):
        """Erreurs 500 ne leakent pas de stack traces en production."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        
        # Forcer une erreur interne
        with patch("app.api.dossiers.get_dossiers", side_effect=Exception("Internal error")):
            resp = await client.get("/dossiers/")
        
        assert resp.status_code == 500
        body = resp.json()
        # Pas de traceback en production
        assert "Traceback" not in str(body)
        assert "Internal error" not in str(body)  # Message générique seulement
    
    async def test_tokens_not_in_urls(self, client, db, admin_user, admin_token):
        """Tokens ne sont jamais dans les query params."""
        # Tous les endpoints devraient accepter Bearer header, pas ?token=
        resp = await client.get(f"/auth/me?token={admin_token}")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Même avec Bearer header valide
        resp = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200
    
    async def test_audit_log_document_access(self, client, db, consultant_user, consultant_token, document):
        """Accès aux documents est audité."""
        resp = await client.get(
            f"/documents/{document.id}",
            headers={"Authorization": f"Bearer {consultant_token}"}
        )
        assert resp.status_code == 200
        
        # Vérifier qu'un AuditLog a été créé
        audit = await db.execute(
            select(AuditLog)
            .where(AuditLog.entity_id == document.id)
            .where(AuditLog.action == "document_view")
        )
        assert audit.scalar_one_or_none() is not None
```

---

## 3. Tests end-to-end (E2E)

### 3.1 Frontend (Playwright)

**Fichier**: `frontend/e2e/security.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Security - Candidat flow', () => {
  test('candidat ne peut pas accéder aux pages admin', async ({ page }) => {
    // Login comme candidat
    await page.goto('/login');
    await page.fill('[name="email"]', 'candidat@example.com');
    await page.fill('[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    await expect(page).toHaveURL('/portal');
    
    // Tenter d'accéder à /analytics
    await page.goto('/analytics');
    
    // Devrait rediriger vers /portal
    await expect(page).toHaveURL('/portal');
  });
  
  test('upload document avec validation MIME', async ({ page }) => {
    // Login comme candidat
    await page.goto('/login');
    await page.fill('[name="email"]', 'candidat@example.com');
    await page.fill('[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    // Aller sur dossier
    await page.goto('/portal/dossiers/1');
    
    // Tenter d'uploader un fichier non-PDF
    await page.setInputFiles('input[type="file"]', {
      name: 'malware.pdf',
      mimeType: 'application/x-msdownload',
      buffer: Buffer.from('MZ\x90\x00'),
    });
    
    await page.click('button:has-text("Téléverser")');
    
    // Devrait afficher une erreur
    await expect(page.locator('.error')).toContainText('Type de fichier non autorisé');
  });
});

test.describe('Security - Session management', () => {
  test('logout invalide la session', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('[name="email"]', 'admin@example.com');
    await page.fill('[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    await expect(page).toHaveURL('/dashboard');
    
    // Logout
    await page.click('button:has-text("Déconnexion")');
    
    await expect(page).toHaveURL('/login');
    
    // Tenter de revenir au dashboard
    await page.goto('/dashboard');
    
    // Devrait rediriger vers login
    await expect(page).toHaveURL('/login');
  });
});
```

---

## 4. Tests de charge & performance

### 4.1 Locust (optionnel)

**Fichier**: `tests/load/locustfile.py`

```python
from locust import HttpUser, task, between

class VisaCanadaUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login avant les tests."""
        resp = self.client.post("/auth/login", json={
            "email": "load_test@example.com",
            "password": "password123"
        })
        self.token = resp.json()["access_token"]
    
    @task(3)
    def view_dashboard(self):
        self.client.get(
            "/dashboard/overview",
            headers={"Authorization": f"Bearer {self.token}"}
        )
    
    @task(2)
    def list_dossiers(self):
        self.client.get(
            "/dossiers/",
            headers={"Authorization": f"Bearer {self.token}"}
        )
    
    @task(1)
    def view_alerts(self):
        self.client.get(
            "/alerts/upcoming",
            headers={"Authorization": f"Bearer {self.token}"}
        )
```

**Commande**:
```bash
locust -f tests/load/locustfile.py --host http://localhost:8000
```

---

## 5. CI/CD - Tests automatisés

### 5.1 GitHub Actions

**Fichier**: `.github/workflows/tests.yml`

```yaml
name: Tests & Security

on:
  push:
    branches: [main, feat/**]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -e ".[dev]"
      
      - name: Run tests one file at a time
        run: |
          cd backend
          for f in tests/test_*.py; do
            python -m pytest "$f" -q || exit 1
          done
      
      - name: Security - pip-audit
        run: |
          pip install pip-audit
          cd backend
          pip-audit
  
  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Lint
        run: cd frontend && npm run lint
      
      - name: Typecheck
        run: cd frontend && npm run typecheck
      
      - name: Unit tests
        run: cd frontend && npm run test:run
      
      - name: E2E tests
        run: cd frontend && npm run test:e2e
  
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

---

## 6. Checklist pré-production

### Tests obligatoires
- [ ] Tous les tests backend passent (509/509)
- [ ] Tous les tests frontend passent
- [ ] Tests E2E Playwright passent
- [ ] `pip-audit` ne remonte aucune CVE critique
- [ ] Scan Trivy OK (pas de vulnérabilités HIGH/CRITICAL)

### Tests de sécurité
- [ ] Rate limiting login testé (5 req/min max)
- [ ] JWT expiration testé
- [ ] RBAC candidat/consultant/admin testé
- [ ] Isolation candidats testée (candidat A ne voit pas dossier B)
- [ ] Validation injection SQL testée
- [ ] Validation XSS testée
- [ ] Upload fichier malicieux testé
- [ ] Logs sans PII vérifiés
- [ ] Erreurs 500 sans stack trace en production

### Tests de conformité PIPEDA
- [ ] AuditLog enregistre accès documents
- [ ] Candidat peut lire son profil (`/portal/profile`)
- [ ] Candidat peut corriger son profil (`PUT /portal/profile`)
- [ ] Export données implémenté (`/portal/export`)
- [ ] Politique de confidentialité publiée

### Tests de charge (optionnel)
- [ ] Locust: 100 users concurrents pendant 5 min
- [ ] P95 latency < 500ms
- [ ] Taux d'erreur < 0.1%

---

## 7. Documentation des résultats

**Fichier**: `docs/TEST_RESULTS.md`

Structure:
```markdown
# Résultats des tests - [DATE]

## Backend
- Tests passants: 509/509
- Couverture: 85%
- Durée: 45s

## Frontend
- Tests passants: 42/42
- Couverture: 78%
- Durée: 12s

## E2E
- Tests passants: 15/15
- Durée: 3m 20s

## Sécurité
- pip-audit: 0 CVE
- Trivy: 0 vulnérabilités HIGH/CRITICAL
- OWASP ZAP: Aucune alerte HIGH

## Performance
- Locust 100 users:
  - RPS: 250
  - P95: 380ms
  - Taux d'erreur: 0.02%
```

---

## 8. Prochaines étapes

1. **Implémenter tests de sécurité** (section 2)
2. **Fixer échecs API tests** (isolation fixtures)
3. **Ajouter tests E2E** (section 3)
4. **Configurer CI/CD** (section 5)
5. **Exécuter tests avant merge PR**
6. **Audit externe** (pentest professionnel recommandé)
