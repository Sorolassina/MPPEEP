@echo off
REM Script pour nettoyer UNIQUEMENT les dossiers temporaires de PyInstaller
REM Nettoie SEULEMENT build_exe/ à la racine du projet
REM Ne touche JAMAIS le dossier config_tkinter/

REM Changer vers le répertoire du script
cd /d "%~dp0"

echo ========================================
echo Nettoyage des fichiers temporaires
echo ========================================
echo.
echo [SECURITE] Ce script nettoie UNIQUEMENT le dossier build_exe/
echo            Le dossier config_tkinter/ n'est JAMAIS modifie.
echo.

REM Vérifier qu'on est bien dans config_tkinter
if not exist "make_gui.py" (
    echo [ERREUR] Ce script doit etre execute depuis le dossier config_tkinter/
    echo.
    pause
    exit /b 1
)

REM Définir le chemin absolu vers build_exe (à la racine du projet)
set "BUILD_EXE_DIR=%~dp0..\build_exe"

REM Vérifier que build_exe existe et n'est pas config_tkinter (sécurité)
if "%BUILD_EXE_DIR%"=="%~dp0build_exe" (
    echo [ERREUR] Erreur de chemin detectee. Arret par securite.
    echo.
    pause
    exit /b 1
)

REM Attendre un peu pour que OneDrive libère les fichiers
echo Attente de 2 secondes pour que les fichiers soient liberes...
timeout /t 2 /nobreak >nul

REM Supprimer les dossiers temporaires dans build_exe (à la racine du projet)
if exist "%BUILD_EXE_DIR%" (
    echo.
    echo Nettoyage de: %BUILD_EXE_DIR%
    echo.
    
    REM Nettoyer le dossier build/
    if exist "%BUILD_EXE_DIR%\build" (
        echo [1/2] Suppression du dossier build_exe\build...
        rmdir /s /q "%BUILD_EXE_DIR%\build" 2>nul
        if exist "%BUILD_EXE_DIR%\build" (
            echo [ATTENTION] Impossible de supprimer build_exe\build
            echo Les fichiers sont peut-etre verrouilles par OneDrive ou un autre processus.
            echo.
            echo Solutions:
            echo   1. Fermez tous les programmes qui utilisent ces fichiers
            echo   2. Pausez temporairement la synchronisation OneDrive
            echo   3. Reessayez plus tard
        ) else (
            echo [OK] Dossier build_exe\build supprime.
        )
    ) else (
        echo [INFO] Dossier build_exe\build n'existe pas (deja propre).
    )
    
    REM Nettoyer le fichier .spec
    if exist "%BUILD_EXE_DIR%\MPPEEPDashboard.spec" (
        echo [2/2] Suppression du fichier build_exe\MPPEEPDashboard.spec...
        del /f /q "%BUILD_EXE_DIR%\MPPEEPDashboard.spec" 2>nul
        if exist "%BUILD_EXE_DIR%\MPPEEPDashboard.spec" (
            echo [ATTENTION] Impossible de supprimer build_exe\MPPEEPDashboard.spec
            echo Le fichier est peut-etre verrouille.
        ) else (
            echo [OK] Fichier build_exe\MPPEEPDashboard.spec supprime.
        )
    ) else (
        echo [INFO] Fichier build_exe\MPPEEPDashboard.spec n'existe pas (deja propre).
    )
    
    echo.
    echo ========================================
    echo Nettoyage termine
    echo ========================================
    echo.
    echo Note: Le dossier build_exe\dist (contenant l'executable) est preserve.
    echo       Pour le supprimer aussi, supprimez-le manuellement.
    echo.
    echo [SECURITE] Le dossier config_tkinter/ n'a pas ete modifie.
) else (
    echo [INFO] Dossier build_exe n'existe pas a la racine du projet.
    echo        Rien a nettoyer.
    echo.
)

echo.
pause


