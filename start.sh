#!/bin/bash
# Script de démarrage Unix/Linux/Mac pour VisaCanada
# Lance automatiquement backend + frontend

set -e

echo ""
echo "============================================================"
echo "          VISACANADA - Démarrage automatique"
echo "============================================================"
echo ""

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "[ERREUR] Python3 non trouvé. Installez Python 3.12+"
    exit 1
fi

# Lancer le script Python
python3 start.py
