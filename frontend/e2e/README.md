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

- `auth-flow.spec.ts` — parcours d'entrée et de connexion : redirection de la
  racine vers `/login`, erreur sur identifiants invalides, connexion réussie
  jusqu'au tableau de bord. Les appels backend sont interceptés (`page.route`)
  pour que la suite reste autonome (pas de backend requis).

## À étendre

Au fur et à mesure de la construction de l'interface, ajouter les parcours :

- Déconnexion et gardes de rôle (page admin réservée)
- Pagination et filtres de la liste des dossiers
- Détail d'un dossier
- Consentement et export/suppression des données (parcours PIPEDA)
