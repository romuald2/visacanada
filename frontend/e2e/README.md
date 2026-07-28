# Tests E2E (Playwright)

Suite de tests bout-en-bout pour le frontend VisaCanada.

## Installation

Playwright est déclaré dans `devDependencies`. Après `npm install`, installez
les navigateurs :

```bash
npm run test:e2e:install
```

## Exécution

```bash
# Lance le serveur Next.js automatiquement puis exécute la suite
npm run test:e2e

# Interface interactive
npm run test:e2e:ui
```

Pour cibler un environnement déjà démarré (ex. préproduction), définissez
`E2E_BASE_URL` ; le serveur local ne sera alors pas démarré :

```bash
E2E_BASE_URL=https://staging.visacanada.example npm run test:e2e
```

## Structure

- `home.spec.ts` — smoke tests de la page d'accueil (fondation).

## À étendre

Au fur et à mesure de la construction de l'interface, ajouter les parcours :

- Authentification (connexion, déconnexion, rôles)
- Tableau de bord consultant
- Portail candidat (lecture seule, téléversement de documents)
- Facturation (création de facture, paiement)
- Consentement et export/suppression des données (parcours PIPEDA)
