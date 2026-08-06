#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour ouvrir l'interface graphique VisaCanada
"""

import webbrowser
import time

def print_info(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def main():
    print_info("INTERFACE GRAPHIQUE VISACANADA")

    print("Ouverture de l'interface dans votre navigateur...")
    time.sleep(1)

    # Ouvrir la landing page
    webbrowser.open("http://localhost:3003/landing")

    print_info("INTERFACE OUVERTE")

    print("""
ACCES A L'APPLICATION
---------------------
Landing page : http://localhost:3003/landing
Inscription  : http://localhost:3003/register
Connexion    : http://localhost:3003/login

Backend API  : http://localhost:8000
Swagger docs : http://localhost:8000/docs

COMPTES DE TEST
---------------
Admin:
  Email    : admin@visacanada.ca
  Password : Admin123!

Consultant:
  Email    : consultant@visacanada.ca
  Password : Consultant123!

Candidat:
  Email    : candidat@visacanada.ca
  Password : Candidat123!

PARCOURS UTILISATEUR
--------------------
1. Visitez la landing page (deja ouverte)
2. Cliquez "Commencer gratuitement" ou "Connexion"
3. Creez un compte ou connectez-vous
4. Explorez le dashboard

FONCTIONNALITES DISPONIBLES
----------------------------
- Landing page moderne avec sections features/pricing
- Inscription avec choix du role
- Connexion avec MFA optionnel
- Dashboard personnalise par role
- Portail candidat complet
- Gestion dossiers et documents
- Chatbot IA
- Alertes IRCC
- Analytics et KPIs

POUR ARRETER
------------
Ctrl+C dans les terminaux ou:
- Backend : terminal avec 'python start.py'
- Frontend : terminal avec 'npm run dev'
""")

    print_info("BON TEST !")

if __name__ == "__main__":
    main()
