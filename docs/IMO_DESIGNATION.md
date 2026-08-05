# Désignation du responsable de la gestion des incidents (IMO)

**Document officiel - Conformité Loi 25 (Québec)**

Date : 2026-08-05

## 1. Désignation

En vertu de la Loi 25 modernisant des dispositions législatives en matière de protection des renseignements personnels (Article 3.5), l'organisation désigne formellement :

**Nom** : [À COMPLÉTER - Nom du responsable]  
**Titre** : Responsable de la gestion des incidents (IMO - Incident Management Officer)  
**Email** : [À COMPLÉTER]@visacanada.ca  
**Téléphone** : [À COMPLÉTER]  

**Date de désignation** : [À COMPLÉTER - Date signature]  
**Signataire** : [À COMPLÉTER - Nom dirigeant]  
**Titre du signataire** : Président / Directeur général

## 2. Rôle et responsabilités

L'IMO est responsable de :

### 2.1 Gestion des incidents de sécurité
- Coordonner la réponse aux incidents de confidentialité
- Appliquer le plan de réponse aux incidents (INCIDENT_RESPONSE_PLAN.md)
- Déclencher les procédures d'escalade selon la matrice de gravité
- Superviser la containment, l'évaluation et la remédiation

### 2.2 Notification légale (Loi 25, Article 3.5)
- Évaluer si un incident constitue une "atteinte aux renseignements personnels"
- Notifier la Commission d'accès à l'information du Québec (CAI) dans les **72 heures**
- Notifier le Commissaire à la protection de la vie privée du Canada (PIPEDA) si applicable
- Notifier les personnes concernées "avec diligence" si risque de préjudice sérieux
- Documenter tous les incidents et notifications dans le registre

### 2.3 Documentation et conformité
- Maintenir le registre des incidents (Article 3.8 Loi 25)
- Produire les rapports post-incident
- Coordonner avec les autorités (CAI, CPVP, CRTC si télécommunications)
- Former l'équipe aux procédures de réponse

### 2.4 Contacts d'urgence
- **CAI Québec** : 1-888-528-7741 / incident@cai.gouv.qc.ca
- **CPVP Canada** : 1-800-282-1376 / atip.aiprp@priv.gc.ca
- **Équipe technique** : [À COMPLÉTER - contacts DevOps/SRE]
- **Avocat externe** : [À COMPLÉTER si applicable]

## 3. Formation et compétences requises

L'IMO doit :
- ✅ Connaître la Loi 25 (Articles 3.5 à 3.8) et PIPEDA (Principe 4.1.4)
- ✅ Avoir lu et compris le INCIDENT_RESPONSE_PLAN.md du projet
- ✅ Connaître l'architecture technique (backend FastAPI, frontend Next.js, S3, Redis)
- ✅ Avoir accès aux logs d'audit (AuditLog PostgreSQL, logs applicatifs)
- ✅ Savoir évaluer la gravité d'un incident (matrice CRITIQUE/ÉLEVÉ/MOYEN/FAIBLE)
- ✅ Pouvoir rédiger une notification aux autorités en français

## 4. Autorité et moyens

L'IMO dispose de :
- **Autorité décisionnelle** : peut ordonner l'arrêt d'un système compromis
- **Accès prioritaire** : équipe technique, logs, base de données, infrastructure
- **Budget incident** : [À COMPLÉTER - montant pré-approuvé pour urgences]
- **Reporting** : ligne directe avec la direction générale en cas d'incident CRITIQUE

## 5. Délégation et suppléance

En cas d'indisponibilité de l'IMO :

**Suppléant désigné** : [À COMPLÉTER - Nom]  
**Titre** : [À COMPLÉTER]  
**Contact** : [À COMPLÉTER]

Le suppléant dispose des mêmes pouvoirs et accès que l'IMO titulaire.

## 6. Revue et mise à jour

- **Fréquence de revue** : annuelle (ou après chaque incident majeur)
- **Prochaine revue** : 2027-08-05
- **Responsable de la revue** : Direction générale + IMO

## 7. Signatures

**Désignation approuvée par** :

---

**Nom** : [À COMPLÉTER]  
**Titre** : Président / Directeur général  
**Signature** : ______________________  
**Date** : ____________

---

**Acceptation par l'IMO désigné** :

**Nom** : [À COMPLÉTER]  
**Titre** : Responsable de la gestion des incidents (IMO)  
**Signature** : ______________________  
**Date** : ____________

---

## Annexes

- **Annexe A** : INCIDENT_RESPONSE_PLAN.md (procédure 72h)
- **Annexe B** : Contacts d'urgence (équipe technique, fournisseurs, autorités)
- **Annexe C** : Modèles de notification (CAI, CPVP, personnes concernées)

---

**Conservation** : Ce document doit être conservé pendant **7 ans** minimum (Loi 25 Article 3.8).

**Diffusion** :
- ✅ Direction générale
- ✅ IMO désigné + suppléant
- ✅ Équipe DevOps/SRE
- ✅ Conseiller juridique externe (si applicable)
