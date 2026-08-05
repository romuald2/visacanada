# Accords de traitement de données (DPA) - Fournisseurs IA et Cloud

**Document de suivi - Conformité PIPEDA/Loi 25**

Date : 2026-08-05

## 1. Contexte légal

**PIPEDA Principe 4.1.3** : "Une organisation est responsable des renseignements personnels dont elle a la gestion et doit désigner une ou des personnes qui devront s'assurer du respect des principes énoncés ci-dessous."

**Loi 25 Article 3.4** : "Toute personne exploitant une entreprise au Québec qui communique à l'extérieur du Québec un renseignement personnel doit, au préalable, prendre des mesures raisonnables pour s'assurer qu'il bénéficiera d'une protection équivalente à celle prévue par la présente loi."

**Exigence** : Les fournisseurs tiers traitant des données personnelles canadiennes doivent signer un DPA (Data Processing Agreement) garantissant :
- Résidence des données au Canada (ou protection équivalente)
- Chiffrement en transit et au repos
- Non-divulgation à des tiers sans consentement
- Notification des violations dans les 72h
- Suppression des données à la fin du contrat
- Audit de conformité sur demande

## 2. Fournisseurs nécessitant un DPA

### 2.1 Anthropic (Claude API)

**Service** : API Claude pour analyse documentaire, chatbot RAG, vérification conformité  
**Données traitées** :
- Contenu de documents d'immigration (passeports, relevés bancaires, diplômes)
- Messages chatbot (questions candidats sur démarches IRCC)
- Texte extrait par OCR pour vérification IA

**Statut DPA** : ⚠️ **À SIGNER**

**Actions requises** :
1. Contacter Anthropic Sales/Enterprise : sales@anthropic.com
2. Demander un DPA avec clauses :
   - Résidence des données au Canada (ou garantie PIPEDA équivalente)
   - Pas d'entraînement sur nos données (opt-out complet)
   - Suppression automatique après traitement (pas de rétention)
   - Notification violations < 72h
3. Faire réviser par conseiller juridique
4. Signature : Directeur général VisaCanada + Anthropic autorisé
5. Conserver copie signée 7 ans minimum

**Délai** : **15 jours** (priorité haute)

**Alternative si refus** : Héberger modèle open-source (Llama 3, Mistral) sur infrastructure canadienne (Azure Canada Central, AWS ca-central-1) — coût et maintenance élevés.

---

### 2.2 Microsoft Azure (Document Intelligence)

**Service** : Azure Document Intelligence (ex-Form Recognizer) pour OCR et extraction structurée  
**Données traitées** :
- Scans de passeports, permis de travail, diplômes
- Relevés bancaires, lettres d'emploi
- Formulaires IRCC complétés

**Région déployée** : `canadacentral` (Toronto)

**Statut DPA** : ⚠️ **À SIGNER**

**Actions requises** :
1. Accéder au portail Azure Trust Center : https://servicetrust.microsoft.com/
2. Télécharger le DPA standard Microsoft (Online Services Terms + DPA addendum)
3. Vérifier les clauses :
   - ✅ Résidence Canada Central confirmée (datacenter Toronto)
   - ✅ Chiffrement AES-256 au repos, TLS 1.2+ en transit
   - ✅ Pas de transfert hors Canada sans consentement
   - ✅ Notification violations < 72h (conformité Loi 25)
   - ✅ Audit logs disponibles (Azure Monitor)
4. Signer électroniquement via portail Azure ou papier
5. Configurer dans l'abonnement Azure : Settings > Data residency > Lock to Canada

**Délai** : **15 jours** (priorité haute)

**Note** : Azure fournit un DPA standard conforme GDPR/PIPEDA. Pas de négociation nécessaire pour PME, sauf clauses spécifiques secteur immigration.

---

### 2.3 AWS S3 (Stockage documents)

**Service** : Amazon S3 pour stockage chiffré des documents candidats  
**Région déployée** : `ca-central-1` (Montréal)

**Statut DPA** : ⚠️ **À SIGNER**

**Actions requises** :
1. Accéder au AWS Artifact : https://console.aws.amazon.com/artifact/
2. Télécharger le **AWS Data Processing Addendum (DPA)**
3. Vérifier les clauses :
   - ✅ Résidence ca-central-1 confirmée (datacenter Montréal)
   - ✅ Chiffrement SSE-S3 (AES-256) activé par défaut
   - ✅ Pas de réplication hors Canada (S3 bucket policy)
   - ✅ Notification violations via AWS Security Hub
   - ✅ Audit CloudTrail activé
4. Signer via AWS Artifact (électronique) ou contact commercial
5. Configurer S3 Bucket Policy : `Deny` toute action hors `ca-central-1`

**Délai** : **15 jours** (priorité haute)

**Note** : AWS fournit un DPA standard conforme GDPR/PIPEDA. Le DPA couvre tous les services AWS utilisés (S3, éventuellement RDS si migration PostgreSQL vers RDS).

---

## 3. Autres fournisseurs (DPA non requis ou couverts)

### 3.1 Redis (cache/queue)
- **Hébergement** : Auto-hébergé (même serveur que FastAPI) ou Redis Cloud ca-central-1
- **Données** : Sessions temporaires, rate limiting (pas de PII)
- **DPA requis** : Non (données non-identifiantes) sauf si Redis Cloud → alors DPA standard Redis Labs

### 3.2 PostgreSQL
- **Hébergement** : Auto-hébergé ou AWS RDS ca-central-1
- **DPA requis** : Non si auto-hébergé ; Oui si RDS (couvert par AWS DPA ci-dessus)

### 3.3 Twilio (WhatsApp Business - futur)
- **Statut** : Pas encore déployé
- **Action** : DPA requis avant activation (Twilio fournit DPA standard GDPR/PIPEDA)

### 3.4 Gmail API / Microsoft Graph (email IRCC - futur)
- **Statut** : Pas encore déployé
- **Action** : DPA Google Workspace / Microsoft 365 requis avant activation

---

## 4. Checklist de mise en conformité

### Actions immédiates (15 jours)

- [ ] **Anthropic** : Contacter sales@anthropic.com pour DPA entreprise
- [ ] **Azure** : Télécharger DPA depuis Trust Center, signer, configurer data residency lock
- [ ] **AWS** : Télécharger DPA depuis Artifact, signer, configurer S3 bucket policy ca-central-1

### Validation juridique

- [ ] Faire réviser les 3 DPA par conseiller juridique externe (optionnel mais recommandé)
- [ ] Vérifier conformité clauses Loi 25 Article 3.4 (protection équivalente hors Québec)

### Signatures

- [ ] Directeur général VisaCanada signe les 3 DPA
- [ ] Conserver copies signées dans `docs/contracts/DPA/` (7 ans minimum)

### Documentation

- [ ] Ajouter les DPA signés au registre EFVP (Annexe "Accords tiers")
- [ ] Mettre à jour la politique de confidentialité `/privacy` avec noms fournisseurs + liens DPA publics

### Audit

- [ ] Vérifier annuellement que les fournisseurs respectent leurs engagements DPA
- [ ] Renouveler/réviser les DPA à chaque changement de service ou de région

---

## 5. Modèle d'email pour demande DPA

**Objet** : Demande de Data Processing Agreement (DPA) - Conformité PIPEDA/Loi 25 Canada

---

Bonjour,

Nous sommes **VisaCanada**, une plateforme SaaS de gestion de dossiers d'immigration canadienne. Nous utilisons [SERVICE] pour [USAGE].

Dans le cadre de notre conformité avec la **Loi 25 (Québec)** et **PIPEDA (Canada)**, nous devons obtenir un **Data Processing Agreement (DPA)** avec tous nos fournisseurs traitant des données personnelles.

**Données traitées** : [DÉCRIRE : documents d'immigration, informations candidats, etc.]

**Région requise** : Canada (ca-central-1 / canadacentral) ou garantie de protection équivalente PIPEDA

**Clauses requises** :
- Résidence des données au Canada
- Chiffrement en transit (TLS 1.2+) et au repos (AES-256)
- Pas de transfert à des tiers sans consentement explicite
- Notification des violations < 72h
- Suppression des données à la fin du contrat
- Droit d'audit de conformité

Pourriez-vous nous fournir votre DPA standard ou nous indiquer la procédure pour le signer ?

**Contact** :  
[NOM]  
[TITRE]  
VisaCanada  
[EMAIL]  
[TÉLÉPHONE]

Merci,  
[SIGNATURE]

---

## 6. Registre des DPA (à mettre à jour après signature)

| Fournisseur | Service | Statut | Date signature | Date expiration | Contact renouvellement |
|-------------|---------|--------|----------------|-----------------|------------------------|
| Anthropic | Claude API | ⚠️ À signer | - | - | sales@anthropic.com |
| Microsoft Azure | Document Intelligence | ⚠️ À signer | - | - | Azure Trust Center |
| AWS | S3 Storage | ⚠️ À signer | - | - | AWS Artifact |
| Redis Cloud | Cache/Queue | N/A (auto-hébergé) | - | - | - |

**Instructions** : Mettre à jour ce registre après chaque signature. Ajouter une alerte calendrier 60 jours avant l'expiration pour renouvellement.

---

## 7. Conséquences du non-respect

**Si DPA non signés avant production** :
- ⚠️ Non-conformité Loi 25 Article 3.4 → amende jusqu'à 25 M$ CAD ou 4% CA mondial
- ⚠️ Non-conformité PIPEDA Principe 4.1.3 → plainte au Commissaire à la vie privée
- ⚠️ Risque juridique en cas d'incident : responsabilité solidaire avec le fournisseur

**Recommandation** : **Ne pas lancer en production avant signature des 3 DPA**.

---

**Responsable de suivi** : [À COMPLÉTER - Nom IMO ou Directeur général]  
**Échéance** : 2026-08-20 (15 jours)  
**Statut global** : 🔴 **BLOQUANT PRODUCTION**
