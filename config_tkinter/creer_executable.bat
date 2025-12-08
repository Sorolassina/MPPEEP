@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

REM ================================================================
REM Script de creation d'un executable MPPEEPDashboard (PyInstaller)
REM - Compatible uv / .venv / python global
REM - Dynamique (chemins relatifs)
REM - Integre la creation de raccourci sur le bureau
REM ================================================================

REM Si lance par double-clic, relancer dans une fenetre cmd qui reste ouverte
if "%~1"=="" (
    powershell -NoProfile -Command "$p = '%~f0'; Start-Process cmd -ArgumentList '/k', \"call `\"$p`\" keepopen\" -WindowStyle Normal"
    exit /b
)

setlocal enabledelayedexpansion

REM ----------------------------------------------------------------
REM 1) Se placer a la racine du projet
REM ----------------------------------------------------------------
REM creer_executable.bat est dans config_tkinter\
REM donc la racine du projet = parent de ce dossier
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\.."
set "PROJECT_ROOT=%CD%"

echo ======================================================
echo  Creation de l'executable MPPEEPDashboard
echo ======================================================
echo.
echo [INFO] Racine du projet : %PROJECT_ROOT%
echo.

REM ----------------------------------------------------------------
REM 2) Detection de Python / uv
REM ----------------------------------------------------------------
set "PYTHON_CMD="
set "USE_UV=0"

where uv >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    echo uv detecte -> utilisation de "uv run python"
    set "USE_UV=1"
    set "PYTHON_CMD=uv run python"
) else if exist ".venv\Scripts\python.exe" (
    echo Environnement virtuel .venv detecte
    set "PYTHON_CMD=.venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
    echo Environnement virtuel venv detecte
    set "PYTHON_CMD=venv\Scripts\python.exe"
) else (
    where python >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo Python global detecte
        set "PYTHON_CMD=python"
    ) else (
        echo.
        echo [ERREUR] Aucun interprete Python trouve.
        echo Installez Python ou uv avant de continuer.
        echo.
        pause
        exit /b 1
    )
)

echo.
echo [INFO] Commande Python : %PYTHON_CMD%
echo.

echo [PYTHON] Version :
%PYTHON_CMD% --version
echo.

if !USE_UV! EQU 1 (
    echo [UV] Version :
    uv --version
    echo.
)

REM ----------------------------------------------------------------
REM 3) Verification / installation de PyInstaller
REM ----------------------------------------------------------------
echo ======================================================
echo  Verification de PyInstaller
echo ======================================================
echo.

set "PYINSTALLER_OK=0"

if !USE_UV! EQU 1 (
    uv run pyinstaller --version >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "PYINSTALLER_OK=1"
        echo PyInstaller est deja installe dans l'environnement uv.
    )
) else (
    %PYTHON_CMD% -m PyInstaller --version >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "PYINSTALLER_OK=1"
        echo PyInstaller est deja installe.
    )
)

if !PYINSTALLER_OK! EQU 0 (
    echo PyInstaller n'est pas installe. Installation en cours...
    echo.
    if !USE_UV! EQU 1 (
        REM Ajout en dependance dev du projet (pyproject / uv)
        uv add --dev pyinstaller
    ) else (
        %PYTHON_CMD% -m pip install pyinstaller
    )
    echo.
    echo Re-verification de PyInstaller...
    if !USE_UV! EQU 1 (
        uv run pyinstaller --version >nul 2>&1
        if !ERRORLEVEL! EQU 0 set "PYINSTALLER_OK=1"
    ) else (
        %PYTHON_CMD% -m PyInstaller --version >nul 2>&1
        if !ERRORLEVEL! EQU 0 set "PYINSTALLER_OK=1"
    )
)

if !PYINSTALLER_OK! EQU 0 (
    echo.
    echo [ERREUR] Impossible de confirmer l'installation de PyInstaller.
    echo Verifiez la connexion, OneDrive, ou installez-le manuellement :
    echo   - uv add --dev pyinstaller
    echo   - ou python -m pip install pyinstaller
    echo.
    pause
    exit /b 1
)

echo [OK] PyInstaller operationnel.
echo.

REM ----------------------------------------------------------------
REM 4) Option : nettoyage des anciens builds
REM ----------------------------------------------------------------
if exist "%PROJECT_ROOT%\build_exe\build" (
    echo Des fichiers de build precedents existent.
    set /p CLEAN="Voulez-vous les nettoyer avant de continuer ? (O/N): "
    if /i "!CLEAN!"=="O" (
        echo Nettoyage en cours...
        rmdir /s /q "%PROJECT_ROOT%\build_exe\build" 2>nul
        del /f /q "%PROJECT_ROOT%\build_exe\MPPEEPDashboard.spec" 2>nul
        echo Nettoyage termine.
        echo.
    ) else (
        echo Aucun nettoyage effectue.
        echo.
    )
)

REM ----------------------------------------------------------------
REM 5) Lancer build_exe.py (dans config_tkinter)
REM ----------------------------------------------------------------
echo ======================================================
echo  Lancement de la compilation PyInstaller
echo ======================================================
echo.

cd /d "%SCRIPT_DIR%"

echo [INFO] Dossier courant : %CD%
echo [INFO] Execution de : %PYTHON_CMD% build_exe.py
echo.

%PYTHON_CMD% build_exe.py
set "BUILD_RESULT=%ERRORLEVEL%"

echo.
if !BUILD_RESULT! EQU 0 (
    echo ======================================================
    echo  [OK] EXECUTABLE CREE AVEC SUCCES
    echo ======================================================
    echo.
    echo Fichier attendu :
    echo   %PROJECT_ROOT%\build_exe\dist\MPPEEPDashboard.exe
    echo.

    REM ----------------------------------------------------------------
    REM 6) Proposition de creation d'un raccourci sur le Bureau
    REM ----------------------------------------------------------------
    set /p MAKE_SHORTCUT="Voulez-vous creer un raccourci sur le bureau ? (O/N): "
    if /i "!MAKE_SHORTCUT!"=="O" (
        echo.
        echo Appel de creer_raccourci.bat...
        call "%SCRIPT_DIR%creer_raccourci.bat"
    ) else (
        echo.
        echo Aucun raccourci cree.
    )
) else (
    echo ======================================================
    echo  [ERREUR] ECHEC LORS DE LA CREATION DE L'EXECUTABLE
    echo ======================================================
    echo.
    echo Verifiez les points suivants :
    echo   - Erreurs dans config_tkinter\build_exe.py
    echo   - Fichiers verrouilles (OneDrive, antivirus, editeur)
    echo   - Droits d'ecriture dans build_exe\dist\
    echo.
)

echo.
echo ======================================================
echo  Appuyez sur une touche pour fermer cette fenetre...
echo ======================================================
pause >nul

endlocal
exit /b
