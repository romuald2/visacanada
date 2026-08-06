# Data Processing Agreements (DPA) - Repository

**Conformité PIPEDA / Loi 25**

Ce répertoire contient les copies signées des accords de traitement de données (DPA) avec nos fournisseurs cloud et IA.

## 📄 DPA actifs

### 1. Anthropic (Claude API)
- **Fichier** : `anthropic_dpa_2026.pdf`
- **Date signature** : 2026-08-05
- **Expiration** : 2027-08-05
- **Service** : API Claude pour analyse documentaire, chatbot RAG
- **Région** : Infrastructure cloud conforme SOC 2 Type II
- **Clauses clés** :
  - Pas d'entraînement sur données clients
  - Suppression immédiate après traitement (ephemeral)
  - Chiffrement TLS 1.3 en transit, AES-256 au repos
  - Notification violations < 72h

### 2. Microsoft Azure (Document Intelligence)
- **Fichier** : `azure_dpa_2026.pdf`
- **Date signature** : 2026-08-05
- **Expiration** : 2027-08-05
- **Service** : Azure Document Intelligence (OCR, extraction structurée)
- **Région** : Canada Central (Toronto)
- **Clauses clés** :
  - Data residency locked to Canada
  - Chiffrement AES-256 au repos, TLS 1.2+ en transit
  - Pas de transfert hors Canada sans consentement
  - Audit logs via Azure Monitor

### 3. AWS (S3 Storage)
- **Fichier** : `aws_dpa_2026.pdf`
- **Date signature** : 2026-08-05
- **Expiration** : 2027-08-05
- **Service** : Amazon S3 pour stockage documents candidats
- **Région** : ca-central-1 (Montréal)
- **Clauses clés** :
  - Bucket policy : deny actions hors ca-central-1
  - Chiffrement SSE-S3 (AES-256) par défaut
  - CloudTrail audit activé
  - Notification violations via Security Hub

## 🔄 Processus de renouvellement

**Responsable** : Igor Romuald OUMBE TAKOUGANG (IMO)

**60 jours avant expiration** :
1. Contacter le fournisseur pour renouvellement
2. Réviser les clauses (changements de service, nouvelles régions)
3. Faire réviser par conseiller juridique si modifications importantes
4. Signer le nouveau DPA
5. Archiver l'ancien DPA dans `archive/`
6. Mettre à jour ce README et le registre dans `DPA_REQUIREMENTS.md`

**Alertes calendrier** :
- 2027-06-05 : Début renouvellement Anthropic
- 2027-06-05 : Début renouvellement Azure
- 2027-06-05 : Début renouvellement AWS

## 📋 Conformité légale

Ces DPA satisfont les exigences :
- **Loi 25 Article 3.4** : Protection équivalente hors Québec
- **PIPEDA Principe 4.1.3** : Responsabilité gestion données personnelles
- **GDPR Article 28** : Sous-traitance données (équivalence internationale)

## 🔐 Conservation

- **Durée** : 7 ans minimum après expiration (Loi 25 Article 3.8)
- **Accès** : Direction générale, IMO, conseiller juridique uniquement
- **Backup** : Copies chiffrées dans coffre-fort électronique + physique

## 📞 Contacts fournisseurs

| Fournisseur | Contact renouvellement | Support urgence |
|-------------|------------------------|-----------------|
| Anthropic | sales@anthropic.com | support@anthropic.com |
| Azure | Azure Trust Center | Portal Azure Support |
| AWS | AWS Artifact | AWS Support (plan Business) |

---

**Dernière mise à jour** : 2026-08-05  
**Prochaine revue** : 2027-08-05
