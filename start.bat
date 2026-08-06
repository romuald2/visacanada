@echo off
REM Script de démarrage Windows pour VisaCanada
REM Lance automatiquement backend + frontend

echo.
echo ============================================================
echo          VISACANADA - Demarrage automatique
echo ============================================================
echo.

REM Vérifier Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python non trouve. Installez Python 3.12+
    pause
    exit /b 1
)

REM Lancer le script Python
python start.py

pause
