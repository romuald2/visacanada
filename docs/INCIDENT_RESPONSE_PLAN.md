# Plan de réponse aux incidents de sécurité

**Organisme** : VisaCanada  
**Date de création** : 2026-08-05  
**Responsable** : Équipe sécurité / Administrateur principal  
**Conformité** : PIPEDA, Loi 25 (Québec)

---

## 1. Objectif

Ce plan définit les procédures à suivre en cas de violation de données personnelles (data breach) afin de :
- Contenir l'incident rapidement
- Évaluer l'impact sur les personnes concernées
- Notifier les autorités et les individus affectés dans les délais légaux (72h - Loi 25)
- Documenter l'incident et prévenir sa récurrence

---

## 2. Définition d'une violation de données

Une violation se produit lorsque :
- **Accès non autorisé** : Une personne non autorisée accède aux données personnelles
- **Divulgation** : Des données sont exposées publiquement ou partagées par erreur
- **Perte** : Des données sont perdues ou inaccessibles (suppression accidentelle, panne)
- **Vol** : Des données sont exfiltrées par un attaquant (cyberattaque, ransomware)

**Données personnelles concernées** : 
- Informations d'identification (nom, email, téléphone)
- Documents d'identité (passeport, acte de naissance)
- Données financières (relevés bancaires)
- Données de santé (examens médicaux)
- Données biométriques (photos passeport)

---

## 3. Équipe de réponse aux incidents

### Rôles et responsabilités

| Rôle | Responsable | Responsabilités |
|---|---|---|
| **Chef d'incident** | Administrateur principal | Coordination générale, décision notification |
| **Technique** | Lead développeur | Analyse technique, containment, récupération |
| **Juridique** | Conseiller externe | Conformité PIPEDA/Loi 25, communication autorités |
| **Communication** | Responsable relations clients | Rédaction notifications, communication candidats |

### Contact d'urgence
- **Email** : security@visacanada.com
- **Téléphone** : +1 (555) 123-4567 (24/7)

---

## 4. Procédure de réponse (5 phases)

### Phase 1 : DÉTECTION (0-1h)

**Déclencheurs** :
- Alerte système (logs anormaux, accès non autorisé)
- Signalement utilisateur (email suspect, données visibles)
- Audit de sécurité (découverte vulnérabilité)
- Tiers (AWS, notification fournisseur)

**Actions** :
1. ✅ Confirmer l'incident (faux positif ou réel ?)
2. ✅ Noter date/heure de découverte
3. ✅ Alerter le chef d'incident immédiatement
4. ✅ Ouvrir un ticket d'incident (numéro unique, ex: INC-2026-001)

### Phase 2 : CONTAINMENT (1-4h)

**Objectif** : Empêcher l'aggravation de la situation

**Actions immédiates** :
1. ✅ **Isoler le système compromis** (déconnecter serveur, révoquer tokens)
2. ✅ **Bloquer l'accès non autorisé** (changer mots de passe admin, révoquer clés API)
3. ✅ **Préserver les preuves** (snapshot serveur, copie logs, ne PAS effacer traces)
4. ✅ **Évaluer l'étendue** :
   - Quelles données sont affectées ? (tables DB, fichiers S3)
   - Combien d'utilisateurs concernés ?
   - Depuis quand ? (durée d'exposition)
   - Qui a accédé ? (IP, identité attaquant si connu)

**Outils** :
- Logs CloudWatch / ELK
- Audit S3 (CloudTrail)
- Logs base de données PostgreSQL
- AuditLog applicatif

### Phase 3 : ÉVALUATION (4-12h)

**Grille de gravité** :

| Niveau | Critères | Notification requise |
|---|---|---|
| **CRITIQUE** | >1000 personnes OU données santé/financières OU accès prolongé (>7j) | Commissaire + individus (72h) |
| **ÉLEVÉ** | 100-1000 personnes OU données identité (passeport) | Commissaire + individus (72h) |
| **MOYEN** | 10-100 personnes OU données contact (email/tél) | Commissaire seulement |
| **FAIBLE** | <10 personnes OU exposition <1h OU données non sensibles | Documentation interne |

**Risques pour les individus** :
- ❌ Vol d'identité (si passeport/acte naissance exposé)
- ❌ Fraude financière (si relevés bancaires exposés)
- ❌ Discrimination (si données médicales exposées)
- ❌ Phishing ciblé (si emails/téléphones exposés)

**Décision** : Le chef d'incident détermine le niveau et si notification est requise.

### Phase 4 : NOTIFICATION (12-72h)

#### 4.1 Notification au Commissaire à la vie privée (Loi 25)

**Délai** : 72 heures maximum après la découverte

**Destinataires** :
- **Canada** : Commissaire à la vie privée du Canada
  - Formulaire en ligne : https://www.priv.gc.ca/fr/signaler-un-probleme/soumettre-une-plainte/
  - Téléphone : 1-800-282-1376
  - Email : info@priv.gc.ca

- **Québec** (si candidats québécois) : Commission d'accès à l'information du Québec
  - Formulaire : https://www.cai.gouv.qc.ca
  - Téléphone : 1-888-528-7741

**Contenu obligatoire** :
1. Nature de l'incident (accès non autorisé, perte, vol)
2. Date et heure de découverte
3. Données personnelles affectées (types et nombre de personnes)
4. Risques probables pour les individus
5. Mesures prises pour atténuer les risques
6. Mesures prises pour contenir l'incident
7. Contact de l'organisme

**Modèle de notification** : Voir Annexe A

#### 4.2 Notification aux individus

**Délai** : Dès que possible, idéalement dans les 72 heures

**Méthode** : Email + notification dashboard VisaCanada

**Contenu** :
- Ce qui s'est passé (en termes simples)
- Quelles données vous concernant sont affectées
- Quels risques pour vous
- Ce que nous avons fait pour résoudre le problème
- Ce que vous devez faire (changer mot de passe, surveiller relevés bancaires, etc.)
- Contact pour questions : security@visacanada.com

**Modèle de notification** : Voir Annexe B

**Exception** : Pas de notification si risque réel de préjudice est faible ET mesures d'atténuation efficaces (ex: données chiffrées, exposition <1h).

### Phase 5 : POST-INCIDENT (72h-30j)

**Récupération** :
1. ✅ Restaurer systèmes depuis backups propres
2. ✅ Appliquer correctifs de sécurité
3. ✅ Renforcer contrôles (MFA, logs, monitoring)
4. ✅ Tester systèmes avant remise en production

**Rapport post-mortem** (sous 7 jours) :
- Chronologie complète
- Cause racine (vulnérabilité exploitée)
- Impact exact (données, utilisateurs, durée)
- Mesures correctives appliquées
- Recommandations pour prévenir récurrence

**Archivage** :
- Conserver tous les documents pendant 7 ans (conformité PIPEDA)
- Logs, snapshots, emails, rapports

---

## 5. Scénarios types

### Scénario 1 : Ransomware / Cyberattaque

**Signes** : Fichiers chiffrés, demande de rançon, accès DB compromis

**Actions spécifiques** :
1. Isoler IMMÉDIATEMENT tous les serveurs (déconnecter réseau)
2. Ne PAS payer la rançon (recommandation RCMP)
3. Contacter autorités policières (RCMP, cybercrime@rcmp-grc.gc.ca)
4. Restaurer depuis backups (vérifier qu'ils ne sont pas infectés)
5. Notification CRITIQUE (toutes les données potentiellement exposées)

### Scénario 2 : Erreur humaine (email envoyé à mauvaise personne)

**Signes** : Candidat A reçoit document de candidat B

**Actions spécifiques** :
1. Demander au destinataire de supprimer l'email (confirmation écrite)
2. Évaluer : 1 personne = FAIBLE, >10 personnes = MOYEN
3. Notification candidat affecté + excuses
4. Renforcer formation staff (double vérification)

### Scénario 3 : Bucket S3 exposé publiquement

**Signes** : Alerte AWS, documents accessibles sans authentification

**Actions spécifiques** :
1. Bloquer accès public S3 immédiatement (policy Deny *)
2. Vérifier logs CloudTrail : qui a accédé ? combien de téléchargements ?
3. Si aucun téléchargement externe détecté + exposition <24h : MOYEN
4. Si téléchargements suspects : CRITIQUE
5. Notification selon gravité

### Scénario 4 : Employé malveillant

**Signes** : Export massif de données, accès en dehors des heures, logs suspects

**Actions spécifiques** :
1. Révoquer accès employé immédiatement (désactiver compte)
2. Identifier étendue (quels dossiers consultés ?)
3. Contacter autorités policières
4. Notification CRITIQUE si données exportées hors système
5. Audit complet accès tous les employés

---

## 6. Prévention

**Mesures en place** :
- ✅ Chiffrement HTTPS + S3 SSE
- ✅ RBAC strict + rate limiting
- ✅ Backups quotidiens (rétention 30j)
- ✅ AuditLog sur accès documents
- ✅ Monitoring CloudWatch + alertes

**À implémenter** :
- [ ] MFA obligatoire pour admin/consultant
- [ ] SIEM centralisé (ELK, Splunk)
- [ ] Tests de pénétration annuels
- [ ] Formation sécurité employés (trimestrielle)
- [ ] Simulation d'incident (annuelle)

---

## 7. Contacts utiles

| Organisme | Contact | Téléphone | Email |
|---|---|---|---|
| Commissaire à la vie privée Canada | https://www.priv.gc.ca | 1-800-282-1376 | info@priv.gc.ca |
| CAI Québec | https://www.cai.gouv.qc.ca | 1-888-528-7741 | cai@cai.gouv.qc.ca |
| RCMP (cybercrime) | - | - | cybercrime@rcmp-grc.gc.ca |
| AWS Support | Console AWS | - | Ticket support |
| Anthropic Support | - | - | support@anthropic.com |

---

## Annexes

### Annexe A : Modèle notification Commissaire

```
Objet : Notification de violation de données personnelles - [NOM ORGANISME]

Monsieur le Commissaire,

Nous vous notifions par la présente d'une violation de données personnelles survenue dans notre système.

1. Nature de l'incident : [Accès non autorisé / Divulgation / Perte / Vol]
2. Date et heure de découverte : [AAAA-MM-JJ HH:MM]
3. Données personnelles affectées :
   - Types : [Nom, email, passeport, etc.]
   - Nombre de personnes : [Nombre exact ou estimation]
4. Risques probables pour les individus : [Vol d'identité / Fraude / Phishing]
5. Mesures d'atténuation : [Changement mots de passe, surveillance accès]
6. Mesures de containment : [Isolation serveur, révocation accès]
7. Contact : security@visacanada.com / +1 (555) 123-4567

Nous demeurons à votre disposition pour tout complément d'information.

Cordialement,
[NOM, TITRE]
VisaCanada
```

### Annexe B : Modèle notification individu

```
Objet : Information importante concernant vos données personnelles - VisaCanada

Bonjour [NOM],

Nous vous contactons pour vous informer d'un incident de sécurité qui a affecté vos données personnelles.

**Ce qui s'est passé**
Le [DATE], nous avons découvert que [description simple : un accès non autorisé à notre base de données / un email envoyé par erreur / etc.].

**Vos données concernées**
Les informations suivantes vous concernant ont été affectées :
- [Liste : nom, email, numéro de passeport, etc.]

**Risques pour vous**
Cet incident pourrait entraîner [vol d'identité / phishing / fraude financière]. Nous n'avons pour l'instant aucune preuve que vos données aient été utilisées de manière frauduleuse.

**Ce que nous avons fait**
Nous avons immédiatement :
- [Bloqué l'accès non autorisé]
- [Renforcé nos mesures de sécurité]
- [Notifié le Commissaire à la vie privée du Canada]

**Ce que vous devez faire**
Par précaution, nous vous recommandons de :
1. Changer votre mot de passe VisaCanada : [LIEN]
2. Surveiller vos relevés bancaires pour toute activité suspecte
3. Être vigilant face aux emails/appels suspects (phishing)

**Contact**
Si vous avez des questions, contactez-nous :
- Email : security@visacanada.com
- Téléphone : +1 (555) 123-4567

Nous vous présentons nos plus sincères excuses pour cet incident et vous assurons que nous prenons la protection de vos données très au sérieux.

Cordialement,
L'équipe VisaCanada
```

---

**Date de révision** : Ce plan doit être révisé annuellement ou après chaque incident majeur.

**Approbation** :
- [ ] Administrateur principal
- [ ] Conseiller juridique
- [ ] Lead développeur

**Dernière mise à jour** : 2026-08-05
