@echo off
setlocal enabledelayedexpansion

echo ========================================
echo  Creation d'un raccourci sur le bureau
echo ========================================
echo.

REM ----------------------------------------
REM 1) Déterminer la racine du projet
REM ----------------------------------------
REM creer_raccourci.bat est dans:   config_tkinter/
REM donc le projet est le dossier parent
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\.."
set "PROJECT_ROOT=%CD%"

echo [INFO] Racine du projet détectée :
echo    %PROJECT_ROOT%
echo.

REM ----------------------------------------
REM 2) Chemin vers l'exécutable
REM ----------------------------------------
set "EXE_PATH=%PROJECT_ROOT%\build_exe\dist\MPPEEPDashboard.exe"
echo Chemin exécutable : %EXE_PATH%

if not exist "%EXE_PATH%" (
    echo.
    echo [ERREUR] L'exécutable est introuvable !
    echo Vérifiez que build_exe.py a bien généré :
    echo    %EXE_PATH%
    echo.
    pause
    exit /b 1
)

echo.

REM ----------------------------------------
REM 3) Déterminer le chemin du Bureau
REM ----------------------------------------
set "DESKTOP_PATH=%USERPROFILE%\Desktop"

REM Si Desktop n'existe pas, essayer OneDrive
if not exist "%DESKTOP_PATH%" (
    if exist "%USERPROFILE%\OneDrive\Bureau" (
        set "DESKTOP_PATH=%USERPROFILE%\OneDrive\Bureau"
    )
)

echo Chemin du Bureau : %DESKTOP_PATH%
echo.

REM ----------------------------------------
REM 4) Définition du raccourci
REM ----------------------------------------
set "SHORTCUT_PATH=%DESKTOP_PATH%\MPPEEP Dashboard.lnk"
echo Chemin raccourci : %SHORTCUT_PATH%
echo.

REM ----------------------------------------
REM 5) Chemin dynamique de l'icône
REM ----------------------------------------
set "ICON_PATH=%PROJECT_ROOT%\app\static\favicon.ico"
echo Icône potentielle : %ICON_PATH%
echo.

REM ----------------------------------------
REM 6) Si le raccourci existe déjà
REM ----------------------------------------
if exist "%SHORTCUT_PATH%" (
    echo Le raccourci existe déjà.
    set /p REPLACE="Voulez-vous le remplacer ? (O/N): "
    if /i not "!REPLACE!"=="O" (
        echo Opération annulée.
        goto end
    )
    del /f /q "%SHORTCUT_PATH%" 2>nul
)

echo Création du raccourci...
echo.

REM ----------------------------------------
REM 7) Construction de la commande PowerShell
REM ----------------------------------------
set "PS_CMD=$W = New-Object -ComObject WScript.Shell;"
set "PS_CMD=%PS_CMD% $S = $W.CreateShortcut('%SHORTCUT_PATH%');"
set "PS_CMD=%PS_CMD% $S.TargetPath = '%EXE_PATH%';"
set "PS_CMD=%PS_CMD% $S.WorkingDirectory = '%PROJECT_ROOT%\build_exe\dist';"

if exist "%ICON_PATH%" (
    echo ✔ Icône trouvée – application en cours...
    set "PS_CMD=%PS_CMD% $S.IconLocation = '%ICON_PATH%';"
) else (
    echo ⚠ Icône NON trouvée – icône par défaut utilisée
)

set "PS_CMD=%PS_CMD% $S.Save();"

REM ----------------------------------------
REM 8) Exécuter la commande PowerShell
REM ----------------------------------------
powershell -NoProfile -Command "%PS_CMD%"

if %ERRORLEVEL%==0 (
    echo.
    echo ========================================
    echo ✔ Raccourci créé avec succès !
    echo ========================================
    echo Emplacement :
    echo    %SHORTCUT_PATH%
) else (
    echo.
    echo ========================================
    echo ⚠ Une erreur est survenue !
    echo ========================================
)

:end
echo.
echo Appuyez sur une touche pour continuer...
pause >nul
endlocal
exit /b
