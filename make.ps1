# ============================================
# SCRIPT POWERSHELL - MPPEEP DASHBOARD
# ============================================
# Remplacement du Makefile pour Windows
# Usage : .\make.ps1 <commande> [parametres]
# Exemple : .\make.ps1 start
#           .\make.ps1 uv-add -PKG requests
# ============================================

param(
    [Parameter(Position=0)]
    [string]$Command = "help",
    
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

# Fonction d'aide
function Show-Help {
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "MPPEEP Dashboard - Commandes" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "DEMARRAGE RAPIDE:" -ForegroundColor White
    Write-Host "  .\make.ps1 setup [-Python version] - Installation complete (env + deps)"
    Write-Host "    Exemple: .\make.ps1 setup -Python 3.11"
    Write-Host "    Exemple: .\make.ps1 setup -Python python3.12"
    Write-Host "  .\make.ps1 start          - Lancer l'app (config automatique depuis .env)"
    Write-Host "  .\make.ps1 stop           - Arreter l'application"
    Write-Host "  .\make.ps1 restart        - Redemarrer l'application"
    Write-Host ""
    Write-Host "ENVIRONNEMENT:" -ForegroundColor White
    Write-Host "  .\make.ps1 install        - Installer dependances avec uv"
    Write-Host "  .\make.ps1 env-check      - Verifier l'environnement"
    Write-Host "  .\make.ps1 env-info       - Infos sur l'environnement"
    Write-Host ""
    Write-Host "GESTION UV (dependances):" -ForegroundColor White
    Write-Host "  .\make.ps1 uv-sync        - Synchroniser les dependances"
    Write-Host "  .\make.ps1 uv-add -PKG nom - Ajouter une dependance"
    Write-Host "  .\make.ps1 uv-remove -PKG nom - Supprimer une dependance"
    Write-Host "  .\make.ps1 uv-lock        - Verrouiller les dependances"
    Write-Host "  .\make.ps1 uv-list        - Lister les paquets installes"
    Write-Host "  .\make.ps1 uv-outdated    - Voir les paquets obsoletes"
    Write-Host "  .\make.ps1 uv-venv [-Python version] - Creer un environnement virtuel"
    Write-Host ""
    Write-Host "BASE DE DONNEES:" -ForegroundColor White
    Write-Host "  .\make.ps1 db-init        - Initialiser la DB"
    Write-Host "  .\make.ps1 db-reset       - Reinitialiser la DB"
    Write-Host "  .\make.ps1 db-backup      - Sauvegarder la DB"
    Write-Host "  .\make.ps1 create-admin   - Creer un utilisateur admin"
    Write-Host ""
    Write-Host "TESTS:" -ForegroundColor White
    Write-Host "  .\make.ps1 test           - Lancer tous les tests"
    Write-Host "  .\make.ps1 test-unit      - Tests unitaires uniquement"
    Write-Host "  .\make.ps1 test-cov       - Tests avec couverture"
    Write-Host ""
    Write-Host "QUALITE DU CODE:" -ForegroundColor White
    Write-Host "  .\make.ps1 lint           - Verifier le code"
    Write-Host "  .\make.ps1 lint-fix       - Corriger automatiquement"
    Write-Host "  .\make.ps1 format         - Formater le code"
    Write-Host "  .\make.ps1 clean-code     - Nettoyage complet"
    Write-Host ""
    Write-Host "GIT:" -ForegroundColor White
    Write-Host "  .\make.ps1 git-status     - Statut Git"
    Write-Host "  .\make.ps1 pre-commit     - Preparer commit (clean + test)"
    Write-Host "  .\make.ps1 push           - Push vers origin"
    Write-Host ""
    Write-Host "MAINTENANCE:" -ForegroundColor White
    Write-Host "  .\make.ps1 clean          - Nettoyer fichiers temporaires"
    Write-Host "  .\make.ps1 clean-all      - Nettoyage complet (cache + logs)"
    Write-Host "  .\make.ps1 logs           - Voir les logs de l'application"
    Write-Host ""
    Write-Host "DOCKER:" -ForegroundColor White
    Write-Host "  .\make.ps1 docker-dev          - Docker dev"
    Write-Host "  .\make.ps1 docker-prod         - Docker prod"
    Write-Host "  .\make.ps1 docker-rebuild-prod - Rebuild complet production"
    Write-Host "  .\make.ps1 docker-save         - Exporter image (.tar)"
    Write-Host "  .\make.ps1 docker-load         - Importer image (.tar)"
    Write-Host "  .\make.ps1 docker-package      - Package complet (image + config)"
    Write-Host "  .\make.ps1 docker-logs-prod    - Voir les logs"
    Write-Host "  .\make.ps1 docker-status       - Statut des conteneurs"
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "Commande rapide : .\make.ps1 start" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Cyan
}

# ==========================================
# DEMARRAGE RAPIDE
# ==========================================

function Invoke-Setup {
    param([string]$Python)
    Write-Host "Installation complete du projet..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "[1/3] Verification/installation de uv..." -ForegroundColor White
    if (!(Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "uv n'est pas installe. Installation en cours..." -ForegroundColor Yellow
        Write-Host ""
        
        # Vérifier si pip est disponible
        $pipAvailable = $false
        if (Get-Command pip -ErrorAction SilentlyContinue) {
            $pipAvailable = $true
            Write-Host "Utilisation de pip pour installer uv..." -ForegroundColor Gray
        } elseif (Get-Command pip3 -ErrorAction SilentlyContinue) {
            $pipAvailable = $true
            Write-Host "Utilisation de pip3 pour installer uv..." -ForegroundColor Gray
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            # Essayer python -m pip
            try {
                python -m pip --version | Out-Null
                $pipAvailable = $true
                Write-Host "Utilisation de python -m pip pour installer uv..." -ForegroundColor Gray
            } catch {
                $pipAvailable = $false
            }
        }
        
        if (!$pipAvailable) {
            Write-Host "ERREUR: pip n'est pas disponible. Installez Python et pip d'abord." -ForegroundColor Red
            Write-Host "   Ou installez uv manuellement: pip install uv" -ForegroundColor Yellow
            exit 1
        }
        
        # Installer uv
        try {
            if (Get-Command pip -ErrorAction SilentlyContinue) {
                pip install uv
            } elseif (Get-Command pip3 -ErrorAction SilentlyContinue) {
                pip3 install uv
            } else {
                python -m pip install uv
            }
            
            if ($LASTEXITCODE -ne 0) {
                Write-Host "ERREUR: Echec de l'installation de uv" -ForegroundColor Red
                exit 1
            }
            
            # Vérifier que uv est maintenant disponible
            # Attendre un peu pour que le PATH soit mis à jour
            Start-Sleep -Seconds 2
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            
            # Essayer de trouver uv dans le PATH
            $uvFound = $false
            if (Get-Command uv -ErrorAction SilentlyContinue) {
                $uvFound = $true
            } else {
                # Essayer python -m uv comme alternative
                try {
                    python -m uv --version | Out-Null
                    $uvFound = $true
                    Write-Host "Note: Utilisation de 'python -m uv' (uv pas encore dans PATH)" -ForegroundColor Yellow
                    # Créer un alias temporaire pour cette session
                    function global:uv {
                        python -m uv $args
                    }
                } catch {
                    $uvFound = $false
                }
            }
            
            if (!$uvFound) {
                Write-Host "ATTENTION: uv a ete installe mais n'est pas encore dans le PATH" -ForegroundColor Yellow
                Write-Host "   Redemarrez votre terminal pour que uv soit disponible" -ForegroundColor Yellow
                Write-Host "   Ou utilisez: python -m uv ..." -ForegroundColor Gray
                exit 1
            }
            
            Write-Host "OK: uv installe avec succes" -ForegroundColor Green
        } catch {
            Write-Host "ERREUR: Impossible d'installer uv automatiquement" -ForegroundColor Red
            Write-Host "   Installez-le manuellement avec: pip install uv" -ForegroundColor Yellow
            Write-Host "   Erreur: $_" -ForegroundColor Red
            exit 1
        }
    } else {
        $version = uv --version
        Write-Host "OK: uv est deja installe ($version)" -ForegroundColor Green
    }
    Write-Host ""
    Write-Host "[2/3] Creation/verification de l'environnement virtuel..." -ForegroundColor White
    # Vérifier si un environnement virtuel existe déjà
    $venvExists = $false
    if (Test-Path ".venv") {
        Write-Host "OK: Environnement virtuel existe deja (.venv)" -ForegroundColor Green
        $venvExists = $true
    } elseif (Test-Path "venv") {
        Write-Host "OK: Environnement virtuel existe deja (venv)" -ForegroundColor Green
        $venvExists = $true
    } else {
        Write-Host "Creation de l'environnement virtuel..." -ForegroundColor Yellow
        try {
            if ($Python) {
                Write-Host "Utilisation de Python: $Python" -ForegroundColor Gray
                uv venv --python $Python
            } else {
                Write-Host "Utilisation de la version Python par defaut" -ForegroundColor Gray
                uv venv
            }
            Write-Host "OK: Environnement virtuel cree avec succes" -ForegroundColor Green
            $venvExists = $true
        } catch {
            Write-Host "ATTENTION: Impossible de creer l'environnement virtuel explicitement" -ForegroundColor Yellow
            Write-Host "uv sync le creera automatiquement si necessaire" -ForegroundColor Gray
        }
    }
    Write-Host ""
    Write-Host "[3/3] Installation des dependances..." -ForegroundColor White
    # Détecter si on est sur OneDrive (qui ne supporte pas les hardlinks)
    $currentPath = (Get-Location).Path
    if ($currentPath -like "*OneDrive*") {
        Write-Host "Note: Detection OneDrive - utilisation du mode copy pour les liens" -ForegroundColor Yellow
        $env:UV_LINK_MODE = "copy"
    }
    uv sync --extra dev --link-mode=copy
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERREUR: Echec de l'installation des dependances" -ForegroundColor Red
        exit 1
    }
    Write-Host "OK: Dependances installees" -ForegroundColor Green
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "Installation terminee avec succes !" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Pour initialiser la base de donnees :" -ForegroundColor Yellow
    Write-Host "   .\make.ps1 db-init" -ForegroundColor White
    Write-Host ""
    Write-Host "Pour demarrer l'application :" -ForegroundColor Yellow
    Write-Host "   .\make.ps1 start" -ForegroundColor White
    Write-Host ""
}

function Invoke-Start {
    Write-Host "Demarrage de l'application vioda Dashboard..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Configuration : Lecture depuis .env (ou valeurs par defaut)" -ForegroundColor White
    Write-Host "L'application sera accessible sur : http://localhost:9000" -ForegroundColor White
    Write-Host ""
    Write-Host "Pour arreter : Ctrl+C" -ForegroundColor Yellow
    Write-Host ""
    uv run python -m app.main
}

function Invoke-Stop {
    Write-Host "Arret de l'application..." -ForegroundColor Cyan
    Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Host "Application arretee" -ForegroundColor Green
}

function Invoke-Restart {
    Invoke-Stop
    Start-Sleep -Seconds 2
    Invoke-Start
}

# ==========================================
# ENVIRONNEMENT
# ==========================================

function Invoke-Install {
    Write-Host "Installation des dependances..." -ForegroundColor Cyan
    uv sync --extra dev --link-mode=copy
    Write-Host "Dependances installees !" -ForegroundColor Green
}

function Invoke-EnvCheck {
    Write-Host "Verification de l'environnement..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "UV:" -ForegroundColor White
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        $version = uv --version
        Write-Host "   OK: $version" -ForegroundColor Green
    } else {
        Write-Host "   ERREUR: Non installe" -ForegroundColor Red
        Write-Host "      Installez-le avec: pip install uv" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "Python (via uv):" -ForegroundColor White
    uv run python --version
    Write-Host ""
    Write-Host "Dependances principales:" -ForegroundColor White
    uv pip list | Select-String -Pattern "fastapi|uvicorn|sqlmodel"
    Write-Host ""
    Write-Host "Base de donnees:" -ForegroundColor White
    if (Test-Path "app.db") {
        $size = (Get-Item "app.db").Length / 1KB
        Write-Host "   OK: SQLite: app.db ($([math]::Round($size, 2)) KB)" -ForegroundColor Green
    } else {
        Write-Host "   ATTENTION: SQLite: app.db (non initialisee)" -ForegroundColor Yellow
        Write-Host "      Initialisez avec: .\make.ps1 db-init" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "Fichiers de configuration:" -ForegroundColor White
    if (Test-Path ".env") { Write-Host "   OK: .env" -ForegroundColor Green } else { Write-Host "   ATTENTION: .env (manquant)" -ForegroundColor Yellow }
    if (Test-Path "pyproject.toml") { Write-Host "   OK: pyproject.toml" -ForegroundColor Green } else { Write-Host "   ERREUR: pyproject.toml" -ForegroundColor Red }
    Write-Host ""
}

function Invoke-EnvInfo {
    Write-Host "Informations sur l'environnement..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Repertoire de travail:" -ForegroundColor White
    Get-Location
    Write-Host ""
    Write-Host "Python:" -ForegroundColor White
    uv run python --version
    Write-Host ""
    Write-Host "Gestionnaire de paquets:" -ForegroundColor White
    uv --version
    Write-Host ""
    Write-Host "Variables d'environnement (principales):" -ForegroundColor White
    if ($env:DEBUG) { Write-Host "   DEBUG=$env:DEBUG" } else { Write-Host "   DEBUG=(non defini)" }
    if ($env:ENV) { Write-Host "   ENV=$env:ENV" } else { Write-Host "   ENV=(non defini)" }
    if ($env:DATABASE_URL) { Write-Host "   DATABASE_URL=$env:DATABASE_URL" } else { Write-Host "   DATABASE_URL=(non defini)" }
    Write-Host ""
}

# ==========================================
# GESTION UV
# ==========================================

function Invoke-UvSync {
    Write-Host "Synchronisation des dependances..." -ForegroundColor Cyan
    Write-Host ""
    uv sync --link-mode=copy
    Write-Host ""
    Write-Host "Dependances synchronisees !" -ForegroundColor Green
}

function Invoke-UvAdd {
    param([string]$PKG)
    if (!$PKG) {
        Write-Host "ERREUR: Veuillez specifier le nom du paquet" -ForegroundColor Red
        Write-Host "Usage: .\make.ps1 uv-add -PKG nom-du-paquet" -ForegroundColor Yellow
        Write-Host "Exemple: .\make.ps1 uv-add -PKG requests" -ForegroundColor Gray
        exit 1
    }
    Write-Host "Ajout de la dependance: $PKG" -ForegroundColor Cyan
    Write-Host ""
    uv add $PKG --link-mode=copy
    Write-Host ""
    Write-Host "Dependance ajoutee avec succes !" -ForegroundColor Green
}

function Invoke-UvAddDev {
    param([string]$PKG)
    if (!$PKG) {
        Write-Host "ERREUR: Veuillez specifier le nom du paquet" -ForegroundColor Red
        Write-Host "Usage: .\make.ps1 uv-add-dev -PKG nom-du-paquet" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Ajout de la dependance de developpement: $PKG" -ForegroundColor Cyan
    Write-Host ""
    uv add --dev $PKG --link-mode=copy
    Write-Host ""
    Write-Host "Dependance de developpement ajoutee avec succes !" -ForegroundColor Green
}

function Invoke-UvRemove {
    param([string]$PKG)
    if (!$PKG) {
        Write-Host "ERREUR: Veuillez specifier le nom du paquet" -ForegroundColor Red
        Write-Host "Usage: .\make.ps1 uv-remove -PKG nom-du-paquet" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Suppression de la dependance: $PKG" -ForegroundColor Cyan
    Write-Host ""
    uv remove $PKG
    Write-Host ""
    Write-Host "Dependance supprimee avec succes !" -ForegroundColor Green
}

function Invoke-UvLock {
    Write-Host "Verrouillage des dependances..." -ForegroundColor Cyan
    Write-Host ""
    uv lock
    Write-Host ""
    Write-Host "Dependances verrouillees dans uv.lock !" -ForegroundColor Green
}

function Invoke-UvList {
    Write-Host "Paquets installes dans l'environnement:" -ForegroundColor Cyan
    Write-Host ""
    uv pip list
}

function Invoke-UvOutdated {
    Write-Host "Verification des paquets obsoletes..." -ForegroundColor Cyan
    Write-Host ""
    uv pip list --outdated
}

function Invoke-UvTree {
    Write-Host "Arbre des dependances:" -ForegroundColor Cyan
    Write-Host ""
    uv pip show --tree
}

function Invoke-UvUpdate {
    Write-Host "Mise a jour de toutes les dependances..." -ForegroundColor Cyan
    Write-Host ""
    uv sync --upgrade --link-mode=copy
    Write-Host ""
    Write-Host "Dependances mises a jour !" -ForegroundColor Green
}

function Invoke-UvClean {
    Write-Host "Nettoyage du cache UV..." -ForegroundColor Cyan
    Write-Host ""
    uv cache clean
    Write-Host ""
    Write-Host "Cache UV nettoye !" -ForegroundColor Green
}

function Invoke-UvVersion {
    Write-Host "Version de UV:" -ForegroundColor Cyan
    Write-Host ""
    uv --version
    Write-Host ""
    Write-Host "Python (via uv):" -ForegroundColor White
    uv run python --version
}

function Invoke-UvVenv {
    param([string]$Python)
    Write-Host "Creation d'un nouvel environnement virtuel..." -ForegroundColor Cyan
    Write-Host ""
    if ($Python) {
        Write-Host "Utilisation de Python: $Python" -ForegroundColor White
        uv venv --python $Python
    } else {
        Write-Host "Utilisation de la version Python par defaut" -ForegroundColor White
        uv venv
    }
    Write-Host ""
    Write-Host "Environnement virtuel cree !" -ForegroundColor Green
    Write-Host "Note: avec uv, l'environnement est gere automatiquement" -ForegroundColor Gray
}

function Invoke-UvExport {
    Write-Host "Export des dependances vers requirements.txt..." -ForegroundColor Cyan
    Write-Host ""
    uv pip freeze > requirements-exported.txt
    Write-Host ""
    Write-Host "Dependances exportees vers requirements-exported.txt !" -ForegroundColor Green
}

# ==========================================
# BASE DE DONNEES
# ==========================================

function Invoke-DbInit {
    Write-Host "Initialisation de la base de donnees..." -ForegroundColor Cyan
    Write-Host ""
    uv run python scripts/init_db.py
    Write-Host ""
    Write-Host "Base de donnees initialisee !" -ForegroundColor Green
}

function Invoke-DbReset {
    Write-Host "ATTENTION: Toutes les donnees seront supprimees !" -ForegroundColor Red
    Write-Host ""
    Write-Host "Voulez-vous continuer ? (Ctrl+C pour annuler)" -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    Write-Host ""
    Write-Host "Reinitialisation de la base de donnees..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Detection du type de base de donnees..." -ForegroundColor White
    if (Test-Path ".env") {
        $dbUrl = Select-String -Path ".env" -Pattern "^DATABASE_URL=" | ForEach-Object { $_.Line }
        if ($dbUrl -match "sqlite") {
            Write-Host "Type detecte: SQLite" -ForegroundColor White
            if (Test-Path "app.db") { Remove-Item "app.db" -Force; Write-Host "✅ Fichier app.db supprime" -ForegroundColor Green }
            if (Test-Path "vioda.db") { Remove-Item "vioda.db" -Force; Write-Host "✅ Fichier vioda.db supprime" -ForegroundColor Green }
        } elseif ($dbUrl -match "postgresql") {
            Write-Host "Type detecte: PostgreSQL" -ForegroundColor White
            Write-Host "⚠️  Les tables PostgreSQL seront supprimees et recreees par init_db.py" -ForegroundColor Yellow
        } else {
            Write-Host "Type detecte: SQLite (par defaut)" -ForegroundColor White
            if (Test-Path "app.db") { Remove-Item "app.db" -Force; Write-Host "✅ Fichier app.db supprime" -ForegroundColor Green }
        }
    } else {
        Write-Host "Fichier .env non trouve - detection impossible" -ForegroundColor Yellow
        if (Test-Path "app.db") { Remove-Item "app.db" -Force; Write-Host "✅ Fichier app.db supprime" -ForegroundColor Green }
    }
    Write-Host ""
    uv run python scripts/init_db.py
    Write-Host ""
    Write-Host "Base de donnees reinitialisee !" -ForegroundColor Green
}

function Invoke-DbBackup {
    Write-Host "Sauvegarde de la base de donnees..." -ForegroundColor Cyan
    if (!(Test-Path "backups")) { New-Item -ItemType Directory -Path "backups" | Out-Null }
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    if (Test-Path "app.db") {
        Copy-Item "app.db" "backups/app_backup_$timestamp.db"
        Write-Host "Sauvegarde creee: backups/app_backup_$timestamp.db" -ForegroundColor Green
    } else {
        Write-Host "ERREUR: Fichier app.db introuvable" -ForegroundColor Red
    }
}

function Invoke-CreateAdmin {
    Write-Host "Creation d'un administrateur..." -ForegroundColor Cyan
    Write-Host ""
    uv run python scripts/create_user.py
    Write-Host ""
}

function Invoke-Shell {
    Write-Host "Shell Python interactif..." -ForegroundColor Cyan
    Write-Host "   (utilisez 'exit()' pour quitter)" -ForegroundColor Gray
    Write-Host ""
    uv run python
}

# ==========================================
# TESTS
# ==========================================

function Invoke-Test {
    Write-Host "Execution des tests..." -ForegroundColor Cyan
    Write-Host ""
    uv run pytest -v
    Write-Host ""
    Write-Host "Tests termines !" -ForegroundColor Green
}

function Invoke-TestUnit {
    Write-Host "Tests unitaires..." -ForegroundColor Cyan
    Write-Host ""
    uv run pytest tests/unit/ -v
    Write-Host ""
    Write-Host "Tests unitaires termines !" -ForegroundColor Green
}

function Invoke-TestIntegration {
    Write-Host "Tests d'integration..." -ForegroundColor Cyan
    Write-Host ""
    uv run pytest tests/integration/ -v
    Write-Host ""
    Write-Host "Tests d'integration termines !" -ForegroundColor Green
}

function Invoke-TestCritical {
    Write-Host "Tests critiques..." -ForegroundColor Cyan
    Write-Host ""
    uv run pytest -m critical -v
    Write-Host ""
    Write-Host "Tests critiques termines !" -ForegroundColor Green
}

function Invoke-TestCov {
    Write-Host "Tests avec couverture..." -ForegroundColor Cyan
    Write-Host ""
    uv run pytest --cov=app --cov-report=html --cov-report=term-missing
    Write-Host ""
    Write-Host "Rapport HTML : htmlcov/index.html" -ForegroundColor White
    Write-Host "Tests avec couverture termines !" -ForegroundColor Green
}

# ==========================================
# QUALITE DU CODE
# ==========================================

function Invoke-Lint {
    Write-Host "Verification du code avec Ruff..." -ForegroundColor Cyan
    uv run ruff check app/ tests/
}

function Invoke-LintFix {
    Write-Host "Correction automatique avec Ruff..." -ForegroundColor Cyan
    uv run ruff check --fix app/ tests/
}

function Invoke-Format {
    Write-Host "Formatage du code avec Ruff..." -ForegroundColor Cyan
    uv run ruff format app/ tests/
}

function Invoke-FormatCheck {
    Write-Host "Verification du formatage..." -ForegroundColor Cyan
    uv run ruff format --check app/ tests/
}

function Invoke-CleanCode {
    Write-Host "Nettoyage complet du code..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "[1/4] Formatage du code..." -ForegroundColor White
    uv run ruff format app/ tests/
    Write-Host ""
    Write-Host "[2/4] Tri des imports..." -ForegroundColor White
    uv run ruff check --select I --fix app/ tests/
    Write-Host ""
    Write-Host "[3/4] Corrections automatiques..." -ForegroundColor White
    uv run ruff check --fix app/ tests/
    Write-Host ""
    Write-Host "[4/4] Verification finale..." -ForegroundColor White
    uv run ruff check app/ tests/ --statistics
    Write-Host ""
    Write-Host "Code nettoye avec succes !" -ForegroundColor Green
}

function Invoke-CheckAll {
    Invoke-FormatCheck
    Invoke-Lint
}

# ==========================================
# MAINTENANCE
# ==========================================

function Invoke-Logs {
    Write-Host "Logs de l'application..." -ForegroundColor Cyan
    Write-Host ""
    if (Test-Path "logs/app.log") {
        Get-Content "logs/app.log" -Tail 50 -Wait
    } else {
        Write-Host "ERREUR: Fichier de log introuvable" -ForegroundColor Red
    }
}

function Invoke-Clean {
    Write-Host "Nettoyage des fichiers temporaires..." -ForegroundColor Cyan
    Write-Host ""
    if (Test-Path "__pycache__") { Remove-Item -Recurse -Force "__pycache__"; Write-Host "OK: __pycache__ supprime" -ForegroundColor Green }
    if (Test-Path "app/__pycache__") { Remove-Item -Recurse -Force "app/__pycache__"; Write-Host "OK: app/__pycache__ supprime" -ForegroundColor Green }
    if (Test-Path ".pytest_cache") { Remove-Item -Recurse -Force ".pytest_cache"; Write-Host "OK: .pytest_cache supprime" -ForegroundColor Green }
    if (Test-Path ".ruff_cache") { Remove-Item -Recurse -Force ".ruff_cache"; Write-Host "OK: .ruff_cache supprime" -ForegroundColor Green }
    if (Test-Path "htmlcov") { Remove-Item -Recurse -Force "htmlcov"; Write-Host "OK: htmlcov supprime" -ForegroundColor Green }
    if (Test-Path ".coverage") { Remove-Item -Force ".coverage"; Write-Host "OK: .coverage supprime" -ForegroundColor Green }
    Write-Host ""
    Write-Host "Nettoyage termine !" -ForegroundColor Green
}

function Invoke-CleanAll {
    Invoke-Clean
    Write-Host ""
    Write-Host "Nettoyage complet..." -ForegroundColor Cyan
    Write-Host ""
    if (Test-Path "logs/app.log") { Clear-Content "logs/app.log"; Write-Host "OK: Logs vides" -ForegroundColor Green }
    if (Test-Path "logs/error.log") { Clear-Content "logs/error.log"; Write-Host "OK: Error logs vides" -ForegroundColor Green }
    if (Test-Path "logs/access.log") { Clear-Content "logs/access.log"; Write-Host "OK: Access logs vides" -ForegroundColor Green }
    Write-Host ""
    Write-Host "Nettoyage complet termine !" -ForegroundColor Green
}

# ==========================================
# GIT
# ==========================================

function Invoke-GitStatus {
    Write-Host "Statut Git..." -ForegroundColor Cyan
    git status
}

function Invoke-GitLog {
    Write-Host "Historique des commits..." -ForegroundColor Cyan
    git log --oneline --graph --decorate -10
}

function Invoke-GitDiff {
    Write-Host "Modifications non committees..." -ForegroundColor Cyan
    git diff
}

function Invoke-GitBranches {
    Write-Host "Branches Git..." -ForegroundColor Cyan
    git branch -a
}

function Invoke-PreCommit {
    Invoke-CleanCode
    Invoke-Test
    Write-Host ""
    Write-Host "Code pret a etre commite !" -ForegroundColor Green
    Write-Host ""
    Write-Host "Prochaines etapes :" -ForegroundColor Yellow
    Write-Host "  git add ." -ForegroundColor White
    Write-Host "  git commit -m 'feat: description'" -ForegroundColor White
    Write-Host "  git push" -ForegroundColor White
}

function Invoke-Push {
    Write-Host "Push vers origin..." -ForegroundColor Cyan
    $branch = git branch --show-current
    git push origin $branch
}

function Invoke-Pull {
    Write-Host "Pull depuis origin..." -ForegroundColor Cyan
    $branch = git branch --show-current
    git pull origin $branch
}

function Invoke-Sync {
    Invoke-Pull
    Invoke-PreCommit
    Invoke-Push
    Write-Host "Branche synchronisee !" -ForegroundColor Green
}

# ==========================================
# DOCKER
# ==========================================

function Remove-ExistingContainers {
    param([string]$ComposeFile)
    Write-Host "Verification des conteneurs existants..." -ForegroundColor Gray
    
    # Obtenir les noms de conteneurs depuis le fichier docker-compose
    $containers = docker-compose -f $ComposeFile ps -q 2>$null
    if ($containers) {
        $containerNames = docker-compose -f $ComposeFile ps --services 2>$null
        if ($containerNames) {
            Write-Host "Conteneurs existants detectes. Arret et suppression..." -ForegroundColor Yellow
            docker-compose -f $ComposeFile down 2>$null | Out-Null
            Write-Host "Conteneurs existants supprimes" -ForegroundColor Green
        }
    }
    
    # Vérifier aussi les conteneurs par nom (au cas où ils ne sont pas dans docker-compose)
    $commonNames = @("vioda-app", "vioda-db", "vioda-redis", "vioda-nginx")
    foreach ($name in $commonNames) {
        $existing = docker ps -a --filter "name=$name" --format "{{.Names}}" 2>$null
        if ($existing -and $existing -eq $name) {
            Write-Host "Suppression du conteneur orphelin: $name" -ForegroundColor Yellow
            docker rm -f $name 2>$null | Out-Null
        }
    }
}

function Invoke-DockerDev {
    Write-Host "Demarrage en mode developpement..." -ForegroundColor Cyan
    Remove-ExistingContainers -ComposeFile "docker-compose.yml"
    docker-compose -f docker-compose.yml up -d --remove-orphans
    Write-Host ""
    Write-Host "✅ Application demarree en mode developpement" -ForegroundColor Green
    Write-Host "📍 URL: http://localhost:9000" -ForegroundColor White
    Write-Host "📊 Logs: .\make.ps1 docker-logs-dev" -ForegroundColor Gray
}

function Invoke-DockerProd {
    Write-Host "Demarrage en mode production..." -ForegroundColor Cyan
    Remove-ExistingContainers -ComposeFile "docker-compose.prod.yml"
    docker-compose -f docker-compose.prod.yml up -d --remove-orphans
    Write-Host ""
    Write-Host "Application demarree en mode production" -ForegroundColor Green
    Write-Host "URL: http://localhost:9000/vioda (Direct)" -ForegroundColor White
    Write-Host "URL Cloudflare: https://vioda.skpartners.consulting" -ForegroundColor White
    Write-Host "Logs: .\make.ps1 docker-logs-prod" -ForegroundColor Gray
}

function Invoke-DockerBuildDev {
    Write-Host "Construction de l'image de developpement..." -ForegroundColor Cyan
    docker-compose -f docker-compose.yml build --no-cache
    Write-Host "✅ Image de developpement construite" -ForegroundColor Green
}

function Invoke-DockerBuildProd {
    Write-Host "Construction de l'image de production..." -ForegroundColor Cyan
    docker-compose -f docker-compose.prod.yml build --no-cache
    Write-Host "✅ Image de production construite : vioda-dashboard:latest" -ForegroundColor Green
}

function Invoke-DockerRebuildProd {
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "REBUILD COMPLET - PRODUCTION" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "[1/4] Arret et suppression des conteneurs existants..." -ForegroundColor White
    Remove-ExistingContainers -ComposeFile "docker-compose.prod.yml"
    docker-compose -f docker-compose.prod.yml down 2>$null | Out-Null
    Write-Host ""
    Write-Host "[2/4] Reconstruction de l'image (sans cache)..." -ForegroundColor White
    docker-compose -f docker-compose.prod.yml build --no-cache
    Write-Host ""
    Write-Host "[3/4] Demarrage des conteneurs..." -ForegroundColor White
    docker-compose -f docker-compose.prod.yml up -d
    Write-Host ""
    Write-Host "[4/4] Nettoyage des anciennes images..." -ForegroundColor White
    docker image prune -f
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "REBUILD TERMINE AVEC SUCCES !" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Application: http://localhost:80 (Nginx)" -ForegroundColor White
    Write-Host "API Direct: http://localhost:9000" -ForegroundColor White
    Write-Host "PostgreSQL: localhost:5432" -ForegroundColor White
    Write-Host "Redis: localhost:6379" -ForegroundColor White
    Write-Host ""
    Write-Host "Commandes utiles:" -ForegroundColor Yellow
    Write-Host "  .\make.ps1 docker-logs-prod    - Voir les logs" -ForegroundColor Gray
    Write-Host "  .\make.ps1 docker-status       - Statut des conteneurs" -ForegroundColor Gray
    Write-Host "  .\make.ps1 docker-stop-prod    - Arreter" -ForegroundColor Gray
    Write-Host ""
}

function Invoke-DockerStopDev {
    Write-Host "Arret de l'environnement de developpement..." -ForegroundColor Cyan
    docker-compose -f docker-compose.yml down
    Write-Host "✅ Environnement de developpement arrete" -ForegroundColor Green
}

function Invoke-DockerStopProd {
    Write-Host "Arret de l'environnement de production..." -ForegroundColor Cyan
    docker-compose -f docker-compose.prod.yml down
    Write-Host "✅ Environnement de production arrete" -ForegroundColor Green
}

function Invoke-DockerRestartDev {
    Invoke-DockerStopDev
    Invoke-DockerDev
}

function Invoke-DockerRestartProd {
    Invoke-DockerStopProd
    Invoke-DockerProd
}

function Invoke-DockerLogsDev {
    docker-compose -f docker-compose.yml logs -f
}

function Invoke-DockerLogsProd {
    docker-compose -f docker-compose.prod.yml logs -f
}

function Invoke-DockerLogsApp {
    docker-compose -f docker-compose.prod.yml logs -f app
}

function Invoke-DockerStatus {
    Write-Host "Statut des conteneurs Docker:" -ForegroundColor Cyan
    Write-Host ""
    docker-compose -f docker-compose.prod.yml ps
    Write-Host ""
    Write-Host "Images Docker:" -ForegroundColor White
    docker images | Select-String -Pattern "vioda|postgres|nginx|redis|IMAGE"
}

function Invoke-DockerCleanDev {
    Write-Host "Nettoyage de l'environnement de developpement..." -ForegroundColor Cyan
    docker-compose -f docker-compose.yml down -v
    Write-Host "✅ Environnement de developpement nettoye" -ForegroundColor Green
}

function Invoke-DockerCleanProd {
    Write-Host "⚠️  ATTENTION: Les donnees PostgreSQL seront supprimees !" -ForegroundColor Red
    Write-Host "Appuyez sur Ctrl+C pour annuler..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    docker-compose -f docker-compose.prod.yml down -v
    Write-Host "✅ Environnement de production nettoye" -ForegroundColor Green
}

function Invoke-DockerShellApp {
    Write-Host "Ouverture d'un shell dans le conteneur..." -ForegroundColor Cyan
    docker exec -it vioda-app bash
}

function Invoke-DockerShellDb {
    Write-Host "Connexion a PostgreSQL..." -ForegroundColor Cyan
    docker exec -it vioda-db psql -U vioda -d vioda_prod
}

function Invoke-DockerPrune {
    Write-Host "⚠️  ATTENTION: Ceci va supprimer toutes les ressources Docker non utilisees !" -ForegroundColor Red
    Write-Host "Appuyez sur Ctrl+C pour annuler..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    docker system prune -a --volumes -f
    Write-Host "✅ Docker nettoye completement" -ForegroundColor Green
}

function Invoke-DockerInfo {
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "INFORMATIONS DOCKER" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Version Docker:" -ForegroundColor White
    docker --version
    Write-Host ""
    Write-Host "Images vioda:" -ForegroundColor White
    docker images | Select-String -Pattern "vioda|IMAGE"
    Write-Host ""
    Write-Host "Conteneurs en cours:" -ForegroundColor White
    docker ps --filter "name=vioda"
    Write-Host ""
    Write-Host "Utilisation disque:" -ForegroundColor White
    docker system df
    Write-Host ""
}

function Invoke-DockerSave {
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "EXPORT DE L'IMAGE DOCKER" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    if (!(Test-Path "deploiement_docker")) { New-Item -ItemType Directory -Path "deploiement_docker" | Out-Null }
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $filename = "deploiement_docker/vioda-dashboard_$timestamp.tar"
    Write-Host "Export en cours vers : $filename" -ForegroundColor White
    Write-Host "Cela peut prendre plusieurs minutes..." -ForegroundColor Gray
    Write-Host ""
    docker save vioda:latest -o $filename
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "EXPORT TERMINE AVEC SUCCES !" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    $size = [math]::Round((Get-Item $filename).Length / 1MB, 2)
    Write-Host "Fichier cree : $filename" -ForegroundColor White
    Write-Host "Taille : $size MB" -ForegroundColor White
    Write-Host ""
    Write-Host "Pour transferer sur un autre ordinateur :" -ForegroundColor Yellow
    Write-Host "  1. Copiez le fichier .tar sur l'autre ordinateur" -ForegroundColor Gray
    Write-Host "  2. Sur l'autre ordinateur, lancez : .\make.ps1 docker-load" -ForegroundColor Gray
    Write-Host ""
}

function Invoke-DockerLoad {
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "IMPORT DE L'IMAGE DOCKER" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    $files = Get-ChildItem -Path "deploiement_docker" -Filter "vioda-dashboard_*.tar" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
    if ($files.Count -eq 0) {
        Write-Host "ERREUR : Aucun fichier .tar trouve dans deploiement_docker/" -ForegroundColor Red
        Write-Host ""
        Write-Host "Verifiez que le fichier .tar est dans le dossier deploiement_docker/" -ForegroundColor Yellow
        exit 1
    }
    $latestFile = $files[0].FullName
    Write-Host "Fichier detecte : $latestFile" -ForegroundColor White
    Write-Host "Import en cours... (cela peut prendre plusieurs minutes)" -ForegroundColor Gray
    Write-Host ""
    docker load -i $latestFile
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "IMPORT TERMINE AVEC SUCCES !" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "L'image est prete a etre utilisee !" -ForegroundColor White
    Write-Host "Lancez : .\make.ps1 docker-prod" -ForegroundColor Yellow
    Write-Host ""
}

function Invoke-DockerPackage {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $packageDir = "deploiement_docker/vioda-package_$timestamp"
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "PACKAGE COMPLET DE DEPLOIEMENT" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    if (!(Test-Path "deploiement_docker")) { New-Item -ItemType Directory -Path "deploiement_docker" | Out-Null }
    Write-Host "[1/4] Creation du dossier de package..." -ForegroundColor White
    New-Item -ItemType Directory -Path $packageDir -Force | Out-Null
    Write-Host ""
    Write-Host "[2/4] Export de l'image Docker..." -ForegroundColor White
    docker save vioda:latest -o "$packageDir/vioda-image.tar"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host ""
    Write-Host "[3/4] Copie des fichiers de configuration..." -ForegroundColor White
    Copy-Item "docker-compose.prod.yml" "$packageDir/" -ErrorAction Stop
    Copy-Item "env.production.template" "$packageDir/.env.template" -ErrorAction Stop
    Copy-Item "deploiement_docker/nginx.conf" "$packageDir/" -ErrorAction SilentlyContinue
    Write-Host ""
    Write-Host "[4/4] Creation du README de deploiement..." -ForegroundColor White
    $readmeContent = @"
# vioda Dashboard - Package de Deploiement
Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

## Contenu du package
- vioda-image.tar : Image Docker complete
- docker-compose.prod.yml : Configuration Docker Compose
- .env.template : Template des variables d'environnement
- nginx.conf : Configuration Nginx

## Installation sur un nouveau serveur

### 1. Prerequisites
- Docker et Docker Compose installes
- Ports 9010, 5432, 6379 disponibles

### 2. Charger l'image Docker
``````powershell
docker load -i vioda-image.tar
```````

### 3. Configurer les variables d'environnement
``````powershell
# Copier le template
Copy-Item .env.template .env

# Editer .env et renseigner :
# - POSTGRES_PASSWORD
# - SECRET_KEY
# - Autres variables selon vos besoins
```````

### 4. Creer les dossiers necessaires
``````powershell
New-Item -ItemType Directory -Path backups, ssl -Force
```````

### 5. Demarrer les services
``````powershell
docker-compose -f docker-compose.prod.yml up -d
```````

### 6. Verifier le deploiement
``````powershell
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f app
```````

## URLs d'acces
- Application : http://localhost:9010
- API Direct : http://localhost:9010/vioda
- PostgreSQL : localhost:5432 (via host.docker.internal)
- Redis : localhost:6379

## Commandes utiles
``````powershell
# Voir les logs
docker-compose -f docker-compose.prod.yml logs -f

# Arreter les services
docker-compose -f docker-compose.prod.yml down

# Redemarrer les services
docker-compose -f docker-compose.prod.yml restart

# Voir le statut
docker-compose -f docker-compose.prod.yml ps
```````

## Support
Contact : support@vioda.com
"@
    $readmeContent | Set-Content -Path "$packageDir/README.md" -Encoding UTF8
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "PACKAGE CREE AVEC SUCCES !" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    $size = [math]::Round((Get-ChildItem -Path $packageDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
    Write-Host "Dossier : $packageDir" -ForegroundColor White
    Write-Host "Taille totale : $size MB" -ForegroundColor White
    Write-Host ""
    Write-Host "Pour deployer sur un autre ordinateur :" -ForegroundColor Yellow
    Write-Host "  1. Copiez le dossier complet sur l'autre ordinateur" -ForegroundColor Gray
    Write-Host "  2. Suivez les instructions dans README.md" -ForegroundColor Gray
    Write-Host ""
}

function Invoke-DockerTag {
    param([string]$REGISTRY)
    if (!$REGISTRY) {
        Write-Host "ERREUR: Veuillez specifier le registre" -ForegroundColor Red
        Write-Host "Usage: .\make.ps1 docker-tag -REGISTRY registry.example.com" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Tagging de l'image pour : $REGISTRY/vioda-dashboard:latest" -ForegroundColor White
    docker tag vioda:latest "$REGISTRY/vioda-dashboard:latest"
    Write-Host "Image taguee avec succes !" -ForegroundColor Green
}

function Invoke-DockerPush {
    param([string]$REGISTRY)
    if (!$REGISTRY) {
        Write-Host "ERREUR: Veuillez specifier le registre" -ForegroundColor Red
        Write-Host "Usage: .\make.ps1 docker-push -REGISTRY registry.example.com" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Push vers : $REGISTRY/vioda-dashboard:latest" -ForegroundColor White
    docker push "$REGISTRY/vioda-dashboard:latest"
    Write-Host "Image poussee avec succes !" -ForegroundColor Green
}

function Invoke-DockerPull {
    param([string]$REGISTRY)
    if (!$REGISTRY) {
        Write-Host "ERREUR: Veuillez specifier le registre" -ForegroundColor Red
        Write-Host "Usage: .\make.ps1 docker-pull -REGISTRY registry.example.com" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Pull depuis : $REGISTRY/vioda-dashboard:latest" -ForegroundColor White
    docker pull "$REGISTRY/vioda-dashboard:latest"
    docker tag "$REGISTRY/vioda-dashboard:latest" "vioda:latest"
    Write-Host "Image tiree avec succes !" -ForegroundColor Green
}

# ==========================================
# ROUTEUR PRINCIPAL
# ==========================================

# Parser les arguments pour extraire les paramètres
$PKG = $null
$REGISTRY = $null
$Python = $null

if ($Arguments) {
    for ($i = 0; $i -lt $Arguments.Length; $i++) {
        if ($Arguments[$i] -eq "-PKG" -or $Arguments[$i] -eq "PKG=") {
            if ($Arguments[$i] -eq "-PKG") {
                $PKG = $Arguments[$i + 1]
                $i++
            } else {
                $PKG = $Arguments[$i].Substring(4)
            }
        }
        elseif ($Arguments[$i] -eq "-REGISTRY" -or $Arguments[$i].StartsWith("REGISTRY=")) {
            if ($Arguments[$i] -eq "-REGISTRY") {
                $REGISTRY = $Arguments[$i + 1]
                $i++
            } else {
                $REGISTRY = $Arguments[$i].Substring(9)
            }
        }
        elseif ($Arguments[$i] -eq "-Python" -or $Arguments[$i] -eq "Python=" -or $Arguments[$i].StartsWith("--python=")) {
            if ($Arguments[$i] -eq "-Python") {
                $Python = $Arguments[$i + 1]
                $i++
            } elseif ($Arguments[$i].StartsWith("--python=")) {
                $Python = $Arguments[$i].Substring(9)
            } else {
                $Python = $Arguments[$i].Substring(7)
            }
        }
    }
}

# Router vers la fonction appropriée
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "setup" { Invoke-Setup -Python $Python }
    "start" { Invoke-Start }
    "run" { Invoke-Start }
    "stop" { Invoke-Stop }
    "restart" { Invoke-Restart }
    "install" { Invoke-Install }
    "env-check" { Invoke-EnvCheck }
    "env-info" { Invoke-EnvInfo }
    "uv-sync" { Invoke-UvSync }
    "uv-add" { Invoke-UvAdd -PKG $PKG }
    "uv-add-dev" { Invoke-UvAddDev -PKG $PKG }
    "uv-remove" { Invoke-UvRemove -PKG $PKG }
    "uv-lock" { Invoke-UvLock }
    "uv-list" { Invoke-UvList }
    "uv-outdated" { Invoke-UvOutdated }
    "uv-tree" { Invoke-UvTree }
    "uv-update" { Invoke-UvUpdate }
    "uv-clean" { Invoke-UvClean }
    "uv-version" { Invoke-UvVersion }
    "uv-venv" { Invoke-UvVenv -Python $Python }
    "uv-export" { Invoke-UvExport }
    "db-init" { Invoke-DbInit }
    "db-reset" { Invoke-DbReset }
    "db-backup" { Invoke-DbBackup }
    "create-admin" { Invoke-CreateAdmin }
    "shell" { Invoke-Shell }
    "test" { Invoke-Test }
    "test-unit" { Invoke-TestUnit }
    "test-integration" { Invoke-TestIntegration }
    "test-critical" { Invoke-TestCritical }
    "test-cov" { Invoke-TestCov }
    "lint" { Invoke-Lint }
    "lint-fix" { Invoke-LintFix }
    "format" { Invoke-Format }
    "format-check" { Invoke-FormatCheck }
    "clean-code" { Invoke-CleanCode }
    "check-all" { Invoke-CheckAll }
    "logs" { Invoke-Logs }
    "clean" { Invoke-Clean }
    "clean-all" { Invoke-CleanAll }
    "git-status" { Invoke-GitStatus }
    "git-log" { Invoke-GitLog }
    "git-diff" { Invoke-GitDiff }
    "git-branches" { Invoke-GitBranches }
    "pre-commit" { Invoke-PreCommit }
    "push" { Invoke-Push }
    "pull" { Invoke-Pull }
    "sync" { Invoke-Sync }
    "docker-dev" { Invoke-DockerDev }
    "docker-prod" { Invoke-DockerProd }
    "docker-build-dev" { Invoke-DockerBuildDev }
    "docker-build-prod" { Invoke-DockerBuildProd }
    "docker-rebuild-prod" { Invoke-DockerRebuildProd }
    "docker-stop-dev" { Invoke-DockerStopDev }
    "docker-stop-prod" { Invoke-DockerStopProd }
    "docker-restart-dev" { Invoke-DockerRestartDev }
    "docker-restart-prod" { Invoke-DockerRestartProd }
    "docker-logs-dev" { Invoke-DockerLogsDev }
    "docker-logs-prod" { Invoke-DockerLogsProd }
    "docker-logs-app" { Invoke-DockerLogsApp }
    "docker-status" { Invoke-DockerStatus }
    "docker-clean-dev" { Invoke-DockerCleanDev }
    "docker-clean-prod" { Invoke-DockerCleanProd }
    "docker-shell-app" { Invoke-DockerShellApp }
    "docker-shell-db" { Invoke-DockerShellDb }
    "docker-prune" { Invoke-DockerPrune }
    "docker-info" { Invoke-DockerInfo }
    "docker-save" { Invoke-DockerSave }
    "docker-load" { Invoke-DockerLoad }
    "docker-export" { Invoke-DockerSave }
    "docker-import" { Invoke-DockerLoad }
    "docker-package" { Invoke-DockerPackage }
    "docker-tag" { Invoke-DockerTag -REGISTRY $REGISTRY }
    "docker-push" { Invoke-DockerPush -REGISTRY $REGISTRY }
    "docker-pull" { Invoke-DockerPull -REGISTRY $REGISTRY }
    "local-install" { Invoke-Install }
    "local-test" { Invoke-Test }
    default {
        Write-Host "Commande inconnue: $Command" -ForegroundColor Red
        Write-Host ""
        Show-Help
        exit 1
    }
}

