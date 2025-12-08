@echo off
REM Script pour lancer l'interface graphique via uv
REM Utilise uv pour executer Python (recommandé si uv est installé)

REM Changer vers le répertoire du script
cd /d "%~dp0"

echo Recherche de uv...

REM Vérifier si uv est disponible
where uv >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo uv trouve, lancement de l'interface...
    uv run python make_gui.py
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [ERREUR] Impossible de lancer l'interface via uv.
        echo.
        pause
        exit /b 1
    )
    goto :end
)

REM Si uv n'est pas disponible, essayer les autres méthodes
echo uv non trouve, recherche de Python...

REM Essayer python
where python >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo Python trouve via 'python'
    python make_gui.py
    goto :end
)

REM Essayer python3
where python3 >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo Python trouve via 'python3'
    python3 make_gui.py
    goto :end
)

REM Essayer py (Python Launcher Windows)
where py >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo Python trouve via 'py'
    py make_gui.py
    goto :end
)

REM Si rien ne fonctionne
echo.
echo [ERREUR] Ni uv ni Python n'ont ete trouves sur ce systeme.
echo.
echo Solutions:
echo   1. Installer uv: pip install uv
echo   2. Installer Python: https://www.python.org/downloads/
echo   3. Ajouter Python au PATH Windows
echo.
pause
exit /b 1

:end
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERREUR] L'interface n'a pas pu demarrer.
    echo Code d'erreur: %ERRORLEVEL%
    echo.
    pause
)


