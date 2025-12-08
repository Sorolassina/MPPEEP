@echo off
REM Script pour lancer l'interface graphique MPPEEP Dashboard
REM Essaie plusieurs methodes pour trouver Python

REM Changer vers le répertoire du script
cd /d "%~dp0"

echo Recherche de Python...

REM Essayer avec uv en priorite (recommandé pour ce projet)
where uv >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo uv trouve, utilisation de uv run python...
    uv run python make_gui.py
    if %ERRORLEVEL% == 0 goto :end
    echo uv a echoue, essai d'autres methodes...
)

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
echo [ERREUR] Python n'a pas ete trouve sur ce systeme.
echo.
echo Veuillez installer Python depuis https://www.python.org/downloads/
echo.
echo Ou si Python est deja installe, ajoutez-le au PATH Windows.
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


