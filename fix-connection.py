#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnostic et correction de connexion frontend-backend
"""

import os
import sys
from pathlib import Path

def print_info(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def check_env_file():
    """Vérifier et corriger le fichier .env backend"""
    backend_env = Path("backend/.env")

    if not backend_env.exists():
        print("[ERREUR] backend/.env n'existe pas")
        return False

    # Lire le contenu
    content = backend_env.read_text(encoding="utf-8")

    # Vérifier CORS_ORIGINS
    if "CORS_ORIGINS" in content:
        print("[OK] CORS_ORIGINS trouvé dans .env")

        # Vérifier si 3003 est inclus
        if "3003" in content or "*" in content:
            print("[OK] Port 3003 déjà autorisé")
            return True
        else:
            print("[!] Port 3003 non autorisé dans CORS_ORIGINS")
            print("[ACTION] Ajout du port 3003...")

            # Remplacer CORS_ORIGINS
            lines = content.split("\n")
            new_lines = []
            for line in lines:
                if line.startswith("CORS_ORIGINS="):
                    # Extraire les origins existantes
                    old_origins = line.split("=", 1)[1] if "=" in line else ""
                    # Ajouter 3003
                    new_origins = f"{old_origins},http://localhost:3003,http://127.0.0.1:3003".strip(",")
                    new_line = f"CORS_ORIGINS={new_origins}"
                    new_lines.append(new_line)
                    print(f"   Ancien: {line}")
                    print(f"   Nouveau: {new_line}")
                else:
                    new_lines.append(line)

            # Écrire le fichier modifié
            backend_env.write_text("\n".join(new_lines), encoding="utf-8")
            print("[OK] Fichier .env mis à jour")
            return "restart"
    else:
        print("[!] CORS_ORIGINS non trouvé, ajout...")
        content += "\n\n# CORS\nCORS_ORIGINS=http://localhost:3000,http://localhost:3003,http://127.0.0.1:3000,http://127.0.0.1:3003\n"
        backend_env.write_text(content, encoding="utf-8")
        print("[OK] CORS_ORIGINS ajouté")
        return "restart"

def check_frontend_env():
    """Vérifier le fichier .env.local frontend"""
    frontend_env = Path("frontend/.env.local")

    if not frontend_env.exists():
        print("[!] frontend/.env.local n'existe pas, création...")
        frontend_env.write_text("NEXT_PUBLIC_API_URL=http://localhost:8000\n", encoding="utf-8")
        print("[OK] frontend/.env.local créé")
        return True

    content = frontend_env.read_text(encoding="utf-8")
    if "NEXT_PUBLIC_API_URL" in content:
        print("[OK] NEXT_PUBLIC_API_URL configuré")
        return True
    else:
        print("[!] NEXT_PUBLIC_API_URL manquant, ajout...")
        content += "\nNEXT_PUBLIC_API_URL=http://localhost:8000\n"
        frontend_env.write_text(content, encoding="utf-8")
        print("[OK] NEXT_PUBLIC_API_URL ajouté")
        return True

def main():
    print_info("DIAGNOSTIC CONNEXION FRONTEND-BACKEND")

    print("1. Vérification fichier backend/.env...")
    backend_status = check_env_file()

    print("\n2. Vérification fichier frontend/.env.local...")
    frontend_status = check_frontend_env()

    print_info("RESULTAT")

    if backend_status == "restart":
        print("""
[IMPORTANT] Le fichier backend/.env a été modifié.

VOUS DEVEZ REDEMARRER LE BACKEND :

1. Dans le terminal où tourne 'python start.py' :
   - Appuyez sur Ctrl+C pour arrêter

2. Relancez :
   python start.py

3. Puis rechargez la page de login dans votre navigateur

Le frontend (npm run dev) peut rester actif.
""")
    else:
        print("""
[OK] Configuration correcte.

Si le problème persiste :

1. Ouvrez la Console du navigateur (F12)
2. Regardez l'onglet "Network" ou "Console"
3. Recherchez les erreurs CORS ou de connexion
4. Vérifiez que :
   - Backend : http://localhost:8000/health retourne {"status":"healthy"}
   - Frontend : http://localhost:3003 charge correctement

Pour tester manuellement :
   curl http://localhost:8000/health
""")

if __name__ == "__main__":
    main()
