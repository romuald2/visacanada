#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de démarrage automatique VisaCanada
Lance backend + frontend en mode développement
"""

import os
import sys
import subprocess
import time
import secrets
from pathlib import Path

# Force UTF-8 sur Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Couleurs pour le terminal
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}[OK] {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}[!] {text}{RESET}")

def print_error(text):
    print(f"{RED}[X] {text}{RESET}")

def check_python():
    """Vérifier version Python"""
    version = sys.version_info
    if version < (3, 12):
        print_error(f"Python 3.12+ requis, version actuelle: {version.major}.{version.minor}")
        return False
    print_success(f"Python {version.major}.{version.minor}.{version.micro} détecté")
    return True

def check_node():
    """Vérifier Node.js"""
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print_success(f"Node.js {version} détecté")
            return True
    except FileNotFoundError:
        pass
    print_warning("Node.js non trouvé (frontend ne démarrera pas)")
    return False

def create_backend_env():
    """Créer fichier .env backend si absent"""
    backend_dir = Path("backend")
    env_file = backend_dir / ".env"

    if env_file.exists():
        print_success("Fichier backend/.env existe déjà")
        return True

    print_warning("Création de backend/.env...")

    # Générer SECRET_KEY sécurisée
    secret_key = secrets.token_urlsafe(32)

    env_content = f"""# Configuration développement VisaCanada
# Généré automatiquement le {time.strftime('%Y-%m-%d %H:%M:%S')}

# Database (SQLite pour dev)
DATABASE_URL=sqlite+aiosqlite:///./dev.db

# Sécurité
SECRET_KEY={secret_key}

# Redis (optionnel en dev)
REDIS_URL=redis://localhost:6379/0

# CORS
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# APIs externes (à compléter si nécessaire)
ANTHROPIC_API_KEY=
AZURE_DOC_INTELLIGENCE_ENDPOINT=
AZURE_DOC_INTELLIGENCE_KEY=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
S3_BUCKET_NAME=visacanada-dev

# Email (optionnel)
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=noreply@visacanada.ca
SMTP_USE_TLS=true

# Mode debug
DEBUG=true
"""

    env_file.write_text(env_content, encoding="utf-8")
    print_success(f"Fichier backend/.env créé avec SECRET_KEY sécurisée")
    return True

def create_frontend_env():
    """Créer fichier .env.local frontend si absent"""
    frontend_dir = Path("frontend")
    env_file = frontend_dir / ".env.local"

    if env_file.exists():
        print_success("Fichier frontend/.env.local existe déjà")
        return True

    print_warning("Création de frontend/.env.local...")

    env_content = """# Configuration développement frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
"""

    env_file.write_text(env_content, encoding="utf-8")
    print_success("Fichier frontend/.env.local créé")
    return True

def install_backend_deps():
    """Installer dépendances backend"""
    print_warning("Installation des dépendances backend...")
    backend_dir = Path("backend")

    # Vérifier si déjà installé
    if (backend_dir / "app").exists():
        result = subprocess.run(
            [sys.executable, "-c", "import fastapi"],
            capture_output=True
        )
        if result.returncode == 0:
            print_success("Dépendances backend déjà installées")
            return True

    # Installer
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
        cwd=backend_dir,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print_success("Dépendances backend installées")
        return True
    else:
        print_error("Échec installation backend:")
        print(result.stderr)
        return False

def install_frontend_deps():
    """Installer dépendances frontend"""
    print_warning("Installation des dépendances frontend...")
    frontend_dir = Path("frontend")

    # Vérifier si node_modules existe
    if (frontend_dir / "node_modules").exists():
        print_success("Dépendances frontend déjà installées")
        return True

    # Installer
    result = subprocess.run(
        ["npm", "install"],
        cwd=frontend_dir,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print_success("Dépendances frontend installées")
        return True
    else:
        print_error("Échec installation frontend:")
        print(result.stderr)
        return False

def run_migrations():
    """Exécuter migrations Alembic"""
    print_warning("Exécution des migrations de base de données...")
    backend_dir = Path("backend")

    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=backend_dir,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print_success("Migrations appliquées")
        return True
    else:
        print_warning("Migrations échouées (normal si première fois)")
        print(result.stderr[:200])
        return True  # Continuer quand même

def create_test_users():
    """Créer utilisateurs de test via API"""
    import asyncio
    try:
        import httpx
    except ImportError:
        print_warning("httpx non installé, utilisateurs de test non créés")
        return

    async def _create_users():
        try:
            async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=5.0) as client:
                users = [
                    {
                        "email": "admin@visacanada.ca",
                        "password": "Admin123!",
                        "full_name": "Admin Test",
                        "role": "admin"
                    },
                    {
                        "email": "consultant@visacanada.ca",
                        "password": "Consultant123!",
                        "full_name": "Consultant Test",
                        "role": "consultant"
                    },
                    {
                        "email": "candidat@visacanada.ca",
                        "password": "Candidat123!",
                        "full_name": "Candidat Test",
                        "role": "candidat"
                    },
                ]

                for user in users:
                    try:
                        resp = await client.post("/auth/register", json=user)
                        if resp.status_code in [200, 201]:
                            print_success(f"Utilisateur créé: {user['email']}")
                        elif resp.status_code == 400:
                            print_warning(f"Utilisateur existe déjà: {user['email']}")
                        else:
                            print_warning(f"Échec création {user['email']}: {resp.status_code}")
                    except Exception as e:
                        print_warning(f"Erreur création {user['email']}: {e}")
        except Exception as e:
            print_warning(f"Impossible de créer les utilisateurs: {e}")

    print_warning("Création des utilisateurs de test...")
    time.sleep(2)  # Attendre que le backend démarre
    asyncio.run(_create_users())

def start_backend():
    """Démarrer le backend"""
    print_warning("Démarrage du backend FastAPI sur http://localhost:8000...")
    backend_dir = Path("backend")

    # Lancer uvicorn en subprocess
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
        cwd=backend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    print_success("Backend démarré (PID: {})".format(process.pid))
    return process

def start_frontend():
    """Démarrer le frontend"""
    print_warning("Démarrage du frontend Next.js sur http://localhost:3000...")
    frontend_dir = Path("frontend")

    # Lancer npm run dev en subprocess
    process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    print_success("Frontend démarré (PID: {})".format(process.pid))
    return process

def print_access_info():
    """Afficher les informations d'accès"""
    print_header("APPLICATION DEMARREE")

    print(f"{GREEN}[WEB] Frontend:{RESET}     http://localhost:3000")
    print(f"{GREEN}[API] Backend API:{RESET}   http://localhost:8000")
    print(f"{GREEN}[DOC] Swagger docs:{RESET}  http://localhost:8000/docs")
    print(f"{GREEN}[CHK] Health check:{RESET} http://localhost:8000/health")

    print(f"\n{YELLOW}Comptes de test:{RESET}")
    print(f"   Admin:       admin@visacanada.ca / Admin123!")
    print(f"   Consultant:  consultant@visacanada.ca / Consultant123!")
    print(f"   Candidat:    candidat@visacanada.ca / Candidat123!")

    print(f"\n{BLUE}Guide de test:{RESET} docs/TESTING_GUIDE.md")
    print(f"{BLUE}Documentation:{RESET} docs/PROJECT_SUMMARY.md")

    print(f"\n{RED}Pour arreter:{RESET} Ctrl+C dans ce terminal\n")

def main():
    """Point d'entrée principal"""
    print_header("VISACANADA - Démarrage automatique")

    # Vérifications
    if not check_python():
        sys.exit(1)

    has_node = check_node()

    # Configuration
    if not create_backend_env():
        sys.exit(1)

    if has_node:
        create_frontend_env()

    # Installation dépendances
    if not install_backend_deps():
        sys.exit(1)

    if has_node:
        install_frontend_deps()

    # Migrations
    run_migrations()

    # Démarrage
    backend_process = start_backend()

    # Attendre que le backend soit prêt
    time.sleep(3)

    # Créer utilisateurs de test
    create_test_users()

    frontend_process = None
    if has_node:
        frontend_process = start_frontend()
        time.sleep(2)

    # Afficher info
    print_access_info()

    # Garder le script actif et afficher les logs
    try:
        while True:
            # Lire logs backend
            if backend_process.poll() is None:
                line = backend_process.stdout.readline()
                if line:
                    print(f"[BACKEND] {line.strip()}")

            # Lire logs frontend
            if frontend_process and frontend_process.poll() is None:
                line = frontend_process.stdout.readline()
                if line:
                    print(f"[FRONTEND] {line.strip()}")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Arret des services...{RESET}")
        backend_process.terminate()
        if frontend_process:
            frontend_process.terminate()
        time.sleep(1)
        print_success("Services arretes. A bientot!")

if __name__ == "__main__":
    main()
