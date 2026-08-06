#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test automatique VisaCanada
Ouvre toutes les pages importantes dans le navigateur
"""

import webbrowser
import time
import sys

def print_info(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def main():
    print_info("TEST AUTOMATIQUE VISACANADA")

    print("Ouverture automatique des pages dans votre navigateur...")
    print("1. Swagger API (pour tester les endpoints)")
    print("2. Health check (verification backend)")
    time.sleep(2)

    # Liste des URLs a ouvrir
    urls = [
        ("Swagger API Documentation", "http://localhost:8000/docs"),
        ("Health Check", "http://localhost:8000/health"),
    ]

    print_info("OUVERTURE DES PAGES")

    for name, url in urls:
        print(f"[OK] Ouverture: {name}")
        print(f"     URL: {url}")
        webbrowser.open(url)
        time.sleep(1)  # Pause entre chaque ouverture

    print_info("INSTRUCTIONS DE TEST")

    print("""
ETAPE 1 : TESTER L'AUTHENTIFICATION
------------------------------------
Dans l'onglet Swagger (http://localhost:8000/docs):

1. Chercher "POST /auth/login"
2. Cliquer "Try it out"
3. Copier ce JSON dans le champ:

{
  "email": "admin@visacanada.ca",
  "password": "Admin123!"
}

4. Cliquer "Execute"
5. Copier le "access_token" de la reponse
6. Cliquer sur le bouton [Authorize] en haut de la page
7. Coller le token dans le champ
8. Cliquer "Authorize"

Maintenant vous pouvez tester TOUS les endpoints !

ETAPE 2 : TESTER LES ENDPOINTS
-------------------------------
Exemples d'endpoints a essayer:

GET /portal/profile
  -> Voir votre profil utilisateur

GET /api/dossiers
  -> Liste des dossiers (vide au debut)

POST /api/dossiers
  -> Creer un nouveau dossier

POST /auth/mfa/setup
  -> Generer un QR code pour activer MFA

GET /api/ircc-alerts
  -> Liste des alertes IRCC

GET /portal/export
  -> Telecharger vos donnees (JSON)

POST /portal/complaint
  -> Deposer une plainte

ETAPE 3 : TESTER AVEC D'AUTRES COMPTES
---------------------------------------
Vous pouvez vous connecter avec:

Admin:
  email: admin@visacanada.ca
  password: Admin123!

Consultant:
  email: consultant@visacanada.ca
  password: Consultant123!

Candidat:
  email: candidat@visacanada.ca
  password: Candidat123!

ETAPE 4 : CREER DES DONNEES DE TEST
------------------------------------
Pour rendre les tests plus interessants:

1. Connectez-vous en tant que consultant
2. Utilisez POST /api/candidates pour creer un candidat
3. Utilisez POST /api/dossiers pour creer un dossier
4. Utilisez POST /api/documents pour uploader un document

ETAPE 5 : VERIFIER LA SECURITE
-------------------------------
Testez le RBAC (controle d'acces):

1. Connectez-vous en tant que "candidat"
2. Essayez GET /admin/users (doit retourner 403 Forbidden)
3. Essayez GET /api/dossiers (doit fonctionner)

Testez le rate limiting:

1. Faites POST /auth/login avec un mauvais mot de passe
2. Repetez 6 fois rapidement
3. Doit retourner 429 Too Many Requests

ASTUCES
-------
- Le bouton "Schemas" en bas de Swagger montre tous les modeles
- Cliquer sur un endpoint montre les exemples de reponse
- Les codes 200/201 = succes, 400/403/404 = erreur
- Les endpoints /portal/* sont pour les candidats
- Les endpoints /api/* sont pour admin/consultant
- Les endpoints /admin/* sont uniquement pour admin

PROBLEME ?
----------
Si le backend ne repond pas:
1. Verifier que python start.py est toujours en cours
2. Aller sur http://localhost:8000/health
3. Doit afficher: {"status": "healthy"}
""")

    print_info("BON TEST !")
    print("\nPour arreter le backend: Ctrl+C dans le terminal ou 'python start.py' tourne\n")

if __name__ == "__main__":
    main()
