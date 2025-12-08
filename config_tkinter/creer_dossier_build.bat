@echo off
REM Script pour créer le dossier build_exe manuellement
REM (Normalement créé automatiquement lors de la création de l'exécutable)

REM Changer vers le répertoire du script
cd /d "%~dp0"

REM Aller à la racine du projet (parent de config_tkinter)
cd /d "%~dp0.."

echo Creation du dossier build_exe a la racine du projet...

if not exist "build_exe" (
    mkdir "build_exe"
    echo [OK] Dossier build_exe cree.
) else (
    echo Dossier build_exe existe deja.
)

if not exist "build_exe\dist" (
    mkdir "build_exe\dist"
    echo [OK] Dossier build_exe\dist cree.
) else (
    echo Dossier build_exe\dist existe deja.
)

if not exist "build_exe\build" (
    mkdir "build_exe\build"
    echo [OK] Dossier build_exe\build cree.
) else (
    echo Dossier build_exe\build existe deja.
)

echo.
echo Structure creee a la racine du projet:
echo   build_exe/
echo   ├── dist/     (contiendra l'executable)
echo   └── build/    (fichiers temporaires)
echo.
echo Vous pouvez maintenant executer creer_executable.bat
echo.
pause


