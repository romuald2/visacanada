# Plan d'implémentation — Moteur d'échéances

## Constat de départ (ce qui existe déjà)

Après lecture du code, le socle est **déjà en place et de bonne qualité** :

- `models/alert.py` — `Alert` (avec `dedup_key`, `severity`, `extra_data`, `is_notified`) et `AlertConfig` (toggles par type + canaux dashboard/email/whatsapp par dossier).
- `services/alert_service.py` — scans passeport / médical / test de langue (basés sur `Document.expires_at`), deadline de soumission, ronde Express Entry, changement de politique IRCC. Déduplication propre par `dedup_key`.
- `api/alerts.py` — `POST /alerts/scan`, liste, dismiss, get/put config.
- Infra Celery (`core/celery_app.py`, `tasks/ircc_tasks.py`) avec Celery Beat opérationnel.

**Le socle est là. Ce n'est donc pas une construction de zéro, mais une complétion.**

## Les 5 manques réels

1. **Aucun déclenchement automatique** — `scan_all()` existe mais n'est appelé que manuellement via l'API. Pas de tâche Celery Beat.
2. **Aucune livraison multi-canal** — le scan crée les `Alert` mais ne les envoie jamais. `is_notified` reste `False`, `AlertConfig.channels` est stocké mais jamais lu. Email et WhatsApp existent comme services mais ne sont pas branchés aux alertes.
3. **`expires_at` jamais calculé** — le champ existe sur `Document` mais rien ne le peuple. Un test de langue (IELTS/TEF valable 2 ans), un ECA (5 ans), un examen médical (12 mois) devraient déduire leur expiration à partir de la date du document.
4. **Échéances propres à l'immigration absentes** — pas de suivi de l'ITA (invitation Express Entry, 60 jours pour soumettre), de la biométrie (valable 10 ans mais délai de fourniture 30 jours), du PPR (passport request), de la date d'expiration d'un permis de travail/études.
5. **`Dossier.submission_deadline` n'existe pas** — le scan le lit via `getattr()` défensif, donc ce scan est mort tant que le champ n'existe pas.

---

## Découpage en lots livrables

Chaque lot est indépendant, testable, et apporte de la valeur seul. Ordre recommandé.

### Lot 1 — Activer l'existant (le plus gros ROI, le moins de code)

**But** : rendre le moteur autonome et communicant, sans nouveau modèle de données.

- **1a. Tâche Celery Beat de scan quotidien**
  - Nouveau `tasks/alert_tasks.py` : `scan_deadlines()` qui appelle `alert_service.scan_all()` puis la livraison (voir 1b).
  - Ajouter au `beat_schedule` : tous les jours à 7h00 ET (`crontab(hour=7, minute=0)`).
  - Miroir du pattern de `ircc_tasks.py` (event loop + `async_session_factory`).

- **1b. Livraison multi-canal**
  - Nouvelle méthode `alert_service.deliver_pending(db)` : sélectionne les `Alert` avec `is_notified=False`, lit `AlertConfig.channels` du dossier, route vers :
    - `dashboard` → crée une `Notification` (modèle existant) pour le consultant assigné.
    - `email` → `email_service` (existant).
    - `whatsapp` → `whatsapp_service` (existant).
  - Marque `is_notified=True` après envoi réussi. Respecte le pattern de dégradation gracieuse déjà utilisé partout (si un canal échoue, on log et on continue).
  - Sévérité → canal : `critical` force email+dashboard même si whatsapp off (à confirmer avec toi).

- **1c. Endpoint `GET /alerts/upcoming`**
  - Vue agrégée « échéances à venir » triée par date, pour le dashboard consultant (aujourd'hui on ne peut que lister les alertes déjà générées).

**Tests** : `test_alert_tasks.py` (scan + livraison mockée), extension de `test_alerts.py`. Le service de livraison se teste avec les mocks email/whatsapp déjà en place.

### Lot 2 — Calcul automatique des expirations de documents

**But** : peupler `Document.expires_at` automatiquement pour que les scans existants aient de la matière.

- **2a. Table de règles de validité** (`services/document_validity.py`)
  - Dictionnaire déclaratif : `language_test` → 24 mois, `education_credential` (ECA) → 60 mois, `medical_exam` → 12 mois, `police_certificate` → contextuel, etc.
  - Fonction `compute_expiry(document_type, issue_date) -> datetime | None`.
- **2b. Extraction de la date d'émission**
  - Brancher sur le service `extraction`/OCR existant (déjà en place) pour récupérer `issue_date`/`expiry_date`. Si l'OCR fournit déjà une date d'expiration explicite (passeport), l'utiliser directement ; sinon la déduire via 2a.
- **2c. Remplissage au moment de l'upload**
  - Au `POST` document (ou à la fin de l'analyse), calculer et stocker `expires_at`.
  - Commande de rattrapage pour les documents existants (script one-shot).

**Tests** : `test_document_validity.py` (unitaire pur, pas de DB) + intégration sur l'upload.

### Lot 3 — Échéances spécifiques à l'immigration

**But** : modéliser les jalons à délai qui ne sont pas des documents.

- **3a. Nouveau modèle `Deadline`** (`models/deadline.py`)
  - Champs : `dossier_id`, `deadline_type` (enum : `ita_response`, `biometrics`, `ppr`, `medical_request`, `work_permit_expiry`, `study_permit_expiry`, `custom`), `due_date`, `description`, `is_completed`, `completed_at`, `source` (manuel / dérivé).
  - Migration Alembic `017`.
- **3b. Scan `scan_deadlines()`** dans `alert_service`
  - Génère des alertes sur les `Deadline` ouvertes selon des seuils par type (ITA : alerte à J-30, J-15, J-7, J-3 ; biométrie : J-15, J-7 ; etc.).
  - Réutilise `_emit()` + `dedup_key` existants.
- **3c. CRUD API `/deadlines`**
  - Créer/lister/compléter une échéance manuelle par dossier.
  - `Dossier.submission_deadline` : soit ajouter la colonne (active le scan mort 1b existant), soit modéliser comme un `Deadline` de type dédié. **Recommandation : le modéliser comme `Deadline`** pour éviter d'éparpiller les dates sur le dossier — et retirer le `getattr` défensif.

**Tests** : `test_deadlines.py` (modèle + scan + API).

### Lot 4 — Restitution et pilotage (optionnel, dépend du frontend)

- Widget « échéances des 30 prochains jours » sur le dashboard.
- Vue calendrier par consultant.
- Compteur d'échéances critiques dans `analytics`.

Ce lot n'a de sens qu'une fois le frontend étoffé — à garder pour plus tard.

---

## Décisions à trancher avec toi

1. **`submission_deadline`** : colonne sur `Dossier` (simple, active le code existant) **ou** unifié dans le nouveau modèle `Deadline` (plus propre, recommandé) ?
2. **Escalade par sévérité** : une alerte `critical` doit-elle forcer l'email même si le canal email est désactivé dans la config du dossier ?
3. **Fréquence de scan** : quotidien à 7h ET suffit-il, ou veux-tu deux passages (matin + après-midi) ?
4. **Destinataire des notifications** : le consultant assigné au dossier uniquement, ou aussi le candidat (via le portail) ?
5. **Périmètre pour un premier jet** : je recommande de livrer **Lot 1 seul d'abord** (autonomie + livraison, gros impact, ~pas de nouveau modèle), puis Lot 2, puis Lot 3.

## Estimation relative

| Lot | Ampleur | Nouveau modèle | Valeur immédiate |
|-----|---------|----------------|------------------|
| 1   | Moyenne | Non            | Très forte       |
| 2   | Moyenne | Non            | Forte            |
| 3   | Grande  | Oui (`Deadline`) | Forte          |
| 4   | Variable| Non            | Dépend du front  |

## Vérification / non-régression

- Tests fichier par fichier (contrainte connue du projet — voir mémoire projet).
- Nouveaux fichiers de test par lot.
- Migrations Alembic à la suite de `016`.
- Dégradation gracieuse sur tous les canaux externes (email/whatsapp), comme le reste du codebase.
- Le limiteur de débit et la logique existants ne sont pas touchés.
