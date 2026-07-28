# Plan de réponse aux incidents de sécurité

**VisaCanada**
**Version 1.0.0 — 27 juillet 2026**

Ce plan décrit la procédure à suivre en cas d'atteinte à la protection des
renseignements personnels ou de tout incident de sécurité, conformément aux
obligations de déclaration de la LPRPDE (PIPEDA) et de la Loi 25 du Québec.

## 1. Objectifs

- Détecter, contenir et corriger rapidement tout incident de sécurité.
- Évaluer le risque de préjudice pour les personnes concernées.
- Notifier les personnes et les autorités lorsque la loi l'exige.
- Documenter chaque incident dans le registre (modèle `BreachIncident`).

## 2. Définitions

- **Incident de sécurité** : tout événement compromettant la confidentialité,
  l'intégrité ou la disponibilité des données.
- **Atteinte aux mesures de sécurité** : accès, communication, perte ou vol de
  renseignements personnels non autorisé.
- **Risque réel de préjudice grave (RRPG)** : critère déclencheur de la
  notification obligatoire (humiliation, dommage à la réputation, vol
  d'identité, perte financière, etc.).

## 3. Rôles et responsabilités

| Rôle | Responsabilité |
|---|---|
| Responsable vie privée | Coordination, évaluation du RRPG, notifications |
| Équipe technique | Confinement, investigation, correction |
| Direction | Décisions, communication externe |

## 4. Procédure en cinq étapes

### Étape 1 — Détection et signalement
Tout membre du personnel qui soupçonne un incident le signale immédiatement au
responsable vie privée. L'incident est consigné dans le registre via
`POST /privacy/breaches` avec statut `open`.

### Étape 2 — Confinement
L'équipe technique isole les systèmes touchés (révocation de jetons, rotation
des secrets, blocage d'accès) pour limiter la portée. Le statut passe à
`investigating` puis `contained`.

### Étape 3 — Évaluation du risque
Le responsable vie privée évalue le RRPG selon :
- la sensibilité des données touchées ;
- la probabilité d'usage malveillant ;
- le nombre de personnes concernées.

Le système calcule une recommandation via
`PrivacyService.assess_breach_notification` (gravité élevée/critique, données
sensibles, ou ≥ 100 personnes → notification requise). Cette recommandation
appuie la décision, sans s'y substituer.

### Étape 4 — Notification
Si le RRPG est confirmé, et dès que possible :
- **Personnes concernées** : notification directe (courriel), décrivant
  l'incident, les données touchées et les mesures de protection recommandées.
  Marquer `users_notified = true`.
- **Commissariat à la protection de la vie privée du Canada** (et Commission
  d'accès à l'information du Québec le cas échéant) : déclaration.
  Marquer `reported_to_authority = true`.

### Étape 5 — Clôture et suivi
Après correction, le statut passe à `resolved` (`resolved_at` renseigné). Un
bilan post-incident identifie les mesures correctives pour éviter la récurrence.

## 5. Registre des atteintes

Chaque incident, qu'il déclenche ou non une notification, est conservé dans le
registre. Les organisations doivent tenir ce registre et le fournir sur demande
au Commissariat.

## 6. Délais

Aucun délai fixe n'est imposé, mais la notification doit être faite « le plus
tôt possible » après la conclusion qu'une atteinte présentant un RRPG est
survenue. Toute lenteur injustifiée constitue un manquement.

## 7. Révision

Ce plan est révisé au moins une fois par an et après tout incident majeur.
