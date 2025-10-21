# ============================================
# MAKEFILE - MPPEEP DASHBOARD
# ============================================
# Commandes simplifiées pour le développement
# Usage : make help
# ============================================

# Configuration PowerShell pour Windows
SHELL := pwsh.exe
.SHELLFLAGS := -NoProfile -Command

.PHONY: help
help: ## Afficher l'aide
	@echo "=========================================="
	@echo "MPPEEP Dashboard - Commandes"
	@echo "=========================================="
	@echo ""
	@echo "DEMARRAGE RAPIDE:"
	@echo "  make setup          - Installation complete (env + deps + db)"
	@echo "  make start          - Lancer l'app (config automatique depuis .env)"
	@echo "  make stop           - Arreter l'application"
	@echo "  make restart        - Redemarrer l'application"
	@echo ""
	@echo "ENVIRONNEMENT:"
	@echo "  make install        - Installer dependances avec uv"
	@echo "  make env-check      - Verifier l'environnement"
	@echo "  make env-info       - Infos sur l'environnement"
	@echo ""
	@echo "GESTION UV (dependances):"
	@echo "  make uv-sync        - Synchroniser les dependances"
	@echo "  make uv-add         - Ajouter une dependance (PKG=nom)"
	@echo "  make uv-remove      - Supprimer une dependance (PKG=nom)"
	@echo "  make uv-lock        - Verrouiller les dependances"
	@echo "  make uv-list        - Lister les paquets installes"
	@echo "  make uv-outdated    - Voir les paquets obsoletes"
	@echo ""
	@echo "BASE DE DONNEES:"
	@echo "  make db-init        - Initialiser la DB"
	@echo "  make db-reset       - Reinitialiser la DB"
	@echo "  make db-backup      - Sauvegarder la DB"
	@echo "  make create-admin   - Creer un utilisateur admin"
	@echo ""
	@echo "TESTS:"
	@echo "  make test           - Lancer tous les tests"
	@echo "  make test-unit      - Tests unitaires uniquement"
	@echo "  make test-cov       - Tests avec couverture"
	@echo ""
	@echo "QUALITE DU CODE:"
	@echo "  make lint           - Verifier le code"
	@echo "  make lint-fix       - Corriger automatiquement"
	@echo "  make format         - Formater le code"
	@echo "  make clean-code     - Nettoyage complet"
	@echo ""
	@echo "GIT:"
	@echo "  make git-status     - Statut Git"
	@echo "  make pre-commit     - Preparer commit (clean + test)"
	@echo "  make push           - Push vers origin"
	@echo ""
	@echo "MAINTENANCE:"
	@echo "  make clean          - Nettoyer fichiers temporaires"
	@echo "  make clean-all      - Nettoyage complet (cache + logs)"
	@echo "  make logs           - Voir les logs de l'application"
	@echo ""
	@echo "DOCKER:"
	@echo "  make docker-dev          - Docker dev"
	@echo "  make docker-prod         - Docker prod"
	@echo "  make docker-rebuild-prod - Rebuild complet production"
	@echo "  make docker-save         - Exporter image (.tar)"
	@echo "  make docker-load         - Importer image (.tar)"
	@echo "  make docker-package      - Package complet (image + config)"
	@echo "  make docker-logs-prod    - Voir les logs"
	@echo "  make docker-status       - Statut des conteneurs"
	@echo ""
	@echo "=========================================="
	@echo "Commande rapide : make start"
	@echo "=========================================="

# ==========================================
# DEMARRAGE RAPIDE - COMMANDES PRINCIPALES
# ==========================================

.PHONY: setup
setup: ## Installation complete (premiere utilisation)
	@echo "Installation complete du projet..."
	@echo ""
	@echo "[1/3] Verification de l'environnement..."
	@if (!(Get-Command uv -ErrorAction SilentlyContinue)) { \
		echo "ERREUR: uv n'est pas installe. Installez-le avec:"; \
		echo "   pip install uv"; \
		exit 1; \
	}
	@echo "OK: uv est installe"
	@echo ""
	@echo "[2/3] Installation des dependances..."
	uv sync --extra dev
	@echo ""
	@echo "[3/3] Initialisation de la base de donnees..."
	uv run python scripts/init_db.py
	@echo ""
	@echo "=========================================="
	@echo "Installation terminee avec succes !"
	@echo "=========================================="
	@echo ""
	@echo "Pour demarrer l'application :"
	@echo "   make start"
	@echo ""

.PHONY: start
start: ## Lancer l'application (configuration automatique selon .env)
	@echo "Demarrage de l'application MPPEEP Dashboard..."
	@echo ""
	@echo "Configuration : Lecture depuis .env (ou valeurs par defaut)"
	@echo "L'application sera accessible sur : http://localhost:9000"
	@echo ""
	@echo "Pour arreter : Ctrl+C"
	@echo ""
	uv run python -m app.main
	

.PHONY: stop
stop: ## Arreter l'application
	@echo "Arret de l'application..."
	@Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | Stop-Process -Force
	@echo "Application arretee"

.PHONY: restart
restart: stop start ## Redemarrer l'application

.PHONY: run
run: start ## Alias pour 'make start'

# ==========================================
# ENVIRONNEMENT
# ==========================================

.PHONY: install
install: ## Installer les dependances
	@echo "Installation des dependances..."
	uv sync --extra dev
	@echo "Dependances installees !"

.PHONY: env-check
env-check: ## Verifier l'environnement et les dependances
	@echo "Verification de l'environnement..."
	@echo ""
	@echo "UV:"
	@if (Get-Command uv -ErrorAction SilentlyContinue) { \
		$$version = (uv --version); \
		echo "   OK: $$version"; \
	} else { \
		echo "   ERREUR: Non installe"; \
		echo "      Installez-le avec: pip install uv"; \
	}
	@echo ""
	@echo "Python (via uv):"
	@uv run python --version
	@echo ""
	@echo "Dependances principales:"
	@uv pip list | Select-String -Pattern "fastapi|uvicorn|sqlmodel"
	@echo ""
	@echo "Base de donnees:"
	@if (Test-Path "app.db") { \
		$$size = (Get-Item "app.db").Length / 1KB; \
		echo "   OK: SQLite: app.db ($${size} KB)"; \
	} else { \
		echo "   ATTENTION: SQLite: app.db (non initialisee)"; \
		echo "      Initialisez avec: make db-init"; \
	}
	@echo ""
	@echo "Fichiers de configuration:"
	@if (Test-Path ".env") { echo "   OK: .env" } else { echo "   ATTENTION: .env (manquant)" }
	@if (Test-Path "pyproject.toml") { echo "   OK: pyproject.toml" } else { echo "   ERREUR: pyproject.toml" }
	@echo ""

.PHONY: env-info
env-info: ## Afficher les informations sur l'environnement
	@echo "Informations sur l'environnement..."
	@echo ""
	@echo "Repertoire de travail:"
	@Get-Location
	@echo ""
	@echo "Python:"
	@uv run python --version
	@echo ""
	@echo "Gestionnaire de paquets:"
	@uv --version
	@echo ""
	@echo "Variables d'environnement (principales):"
	@if ($$env:DEBUG) { echo "   DEBUG=$$env:DEBUG" } else { echo "   DEBUG=(non defini)" }
	@if ($$env:ENV) { echo "   ENV=$$env:ENV" } else { echo "   ENV=(non defini)" }
	@if ($$env:DATABASE_URL) { echo "   DATABASE_URL=$$env:DATABASE_URL" } else { echo "   DATABASE_URL=(non defini)" }
	@echo ""

# ==========================================
# GESTION UV (DEPENDANCES)
# ==========================================

.PHONY: uv-sync
uv-sync: ## Synchroniser les dependances depuis pyproject.toml
	@echo "Synchronisation des dependances..."
	@echo ""
	uv sync
	@echo ""
	@echo "Dependances synchronisees !"

.PHONY: uv-add
uv-add: ## Ajouter une dependance (usage: make uv-add PKG=package-name)
	@if (-not $$env:PKG) { \
		echo "ERREUR: Veuillez specifier le nom du paquet"; \
		echo "Usage: make uv-add PKG=nom-du-paquet"; \
		echo "Exemple: make uv-add PKG=requests"; \
		exit 1; \
	}
	@echo "Ajout de la dependance: $$env:PKG"
	@echo ""
	uv add $$env:PKG
	@echo ""
	@echo "Dependance ajoutee avec succes !"

.PHONY: uv-add-dev
uv-add-dev: ## Ajouter une dependance de dev (usage: make uv-add-dev PKG=package-name)
	@if (-not $$env:PKG) { \
		echo "ERREUR: Veuillez specifier le nom du paquet"; \
		echo "Usage: make uv-add-dev PKG=nom-du-paquet"; \
		echo "Exemple: make uv-add-dev PKG=pytest"; \
		exit 1; \
	}
	@echo "Ajout de la dependance de developpement: $$env:PKG"
	@echo ""
	uv add --dev $$env:PKG
	@echo ""
	@echo "Dependance de developpement ajoutee avec succes !"

.PHONY: uv-remove
uv-remove: ## Supprimer une dependance (usage: make uv-remove PKG=package-name)
	@if (-not $$env:PKG) { \
		echo "ERREUR: Veuillez specifier le nom du paquet"; \
		echo "Usage: make uv-remove PKG=nom-du-paquet"; \
		echo "Exemple: make uv-remove PKG=requests"; \
		exit 1; \
	}
	@echo "Suppression de la dependance: $$env:PKG"
	@echo ""
	uv remove $$env:PKG
	@echo ""
	@echo "Dependance supprimee avec succes !"

.PHONY: uv-lock
uv-lock: ## Verrouiller les dependances (mise a jour de uv.lock)
	@echo "Verrouillage des dependances..."
	@echo ""
	uv lock
	@echo ""
	@echo "Dependances verrouillees dans uv.lock !"

.PHONY: uv-list
uv-list: ## Lister tous les paquets installes
	@echo "Paquets installes dans l'environnement:"
	@echo ""
	uv pip list

.PHONY: uv-outdated
uv-outdated: ## Voir les paquets obsoletes (qui peuvent etre mis a jour)
	@echo "Verification des paquets obsoletes..."
	@echo ""
	uv pip list --outdated

.PHONY: uv-tree
uv-tree: ## Afficher l'arbre des dependances
	@echo "Arbre des dependances:"
	@echo ""
	uv pip show --tree

.PHONY: uv-update
uv-update: ## Mettre a jour toutes les dependances
	@echo "Mise a jour de toutes les dependances..."
	@echo ""
	uv sync --upgrade
	@echo ""
	@echo "Dependances mises a jour !"

.PHONY: uv-clean
uv-clean: ## Nettoyer le cache UV
	@echo "Nettoyage du cache UV..."
	@echo ""
	uv cache clean
	@echo ""
	@echo "Cache UV nettoye !"

.PHONY: uv-version
uv-version: ## Afficher la version de UV
	@echo "Version de UV:"
	@echo ""
	uv --version
	@echo ""
	@echo "Python (via uv):"
	uv run python --version

.PHONY: uv-venv
uv-venv: ## Creer un nouvel environnement virtuel
	@echo "Creation d'un nouvel environnement virtuel..."
	@echo ""
	uv venv
	@echo ""
	@echo "Environnement virtuel cree !"
	@echo "Note: avec uv, l'environnement est gere automatiquement"

.PHONY: uv-pip-install
uv-pip-install: ## Installer un paquet avec uv pip (usage: make uv-pip-install PKG=package-name)
	@if (-not $$env:PKG) { \
		echo "ERREUR: Veuillez specifier le nom du paquet"; \
		echo "Usage: make uv-pip-install PKG=nom-du-paquet"; \
		echo "Exemple: make uv-pip-install PKG=requests"; \
		exit 1; \
	}
	@echo "Installation du paquet: $$env:PKG"
	@echo ""
	uv pip install $$env:PKG
	@echo ""
	@echo "Paquet installe avec succes !"

.PHONY: uv-export
uv-export: ## Exporter les dependances vers requirements.txt
	@echo "Export des dependances vers requirements.txt..."
	@echo ""
	uv pip freeze > requirements-exported.txt
	@echo ""
	@echo "Dependances exportees vers requirements-exported.txt !"

# ==========================================
# BASE DE DONNEES
# ==========================================

.PHONY: db-init
db-init: ## Initialiser la base de donnees
	@echo "Initialisation de la base de donnees..."
	@echo ""
	uv run python scripts/init_db.py
	@echo ""
	@echo "Base de donnees initialisee !"

.PHONY: db-drop-tables
db-drop-tables: ## Supprimer TOUTES les tables de la base (PostgreSQL ou SQLite)
	@echo "Suppression de toutes les tables..."
	@echo ""
	uv run python scripts/drop_all_tables.py
	@echo ""

.PHONY: db-reset
db-reset: ## Reinitialiser la DB (supprime toutes les donnees - detecte SQLite ou PostgreSQL)
	@echo "ATTENTION: Toutes les donnees seront supprimees !"
	@echo ""
	@echo "Voulez-vous continuer ? (Ctrl+C pour annuler)"
	@timeout /t 5
	@echo ""
	@echo "Reinitialisation de la base de donnees..."
	@echo ""
	@echo "Detection du type de base de donnees..."
	@if (Test-Path ".env") { $$dbUrl = Select-String -Path ".env" -Pattern "^DATABASE_URL=" | ForEach-Object { $$_.Line }; if ($$dbUrl -match "sqlite") { echo "Type detecte: SQLite"; if (Test-Path "app.db") { Remove-Item "app.db" -Force; echo "✅ Fichier app.db supprime" }; if (Test-Path "mppeep.db") { Remove-Item "mppeep.db" -Force; echo "✅ Fichier mppeep.db supprime" } } elseif ($$dbUrl -match "postgresql") { echo "Type detecte: PostgreSQL"; echo "⚠️  Les tables PostgreSQL seront supprimees et recreees par init_db.py" } else { echo "Type detecte: SQLite (par defaut)"; if (Test-Path "app.db") { Remove-Item "app.db" -Force; echo "✅ Fichier app.db supprime" } } } else { echo "Fichier .env non trouve - detection impossible"; if (Test-Path "app.db") { Remove-Item "app.db" -Force; echo "✅ Fichier app.db supprime" } }
	@echo ""
	uv run python scripts/init_db.py
	@echo ""
	@echo "Base de donnees reinitialisee !"

.PHONY: db-backup
db-backup: ## Sauvegarder la base de donnees SQLite
	@echo "Sauvegarde de la base de donnees..."
	@if (!(Test-Path "backups")) { New-Item -ItemType Directory -Path "backups" | Out-Null }
	@$$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
	@if (Test-Path "app.db") { \
		Copy-Item "app.db" "backups/app_backup_$$timestamp.db"; \
		echo "Sauvegarde creee: backups/app_backup_$$timestamp.db"; \
	} else { \
		echo "ERREUR: Fichier app.db introuvable"; \
	}

.PHONY: create-admin
create-admin: ## Creer un utilisateur admin
	@echo "Creation d'un administrateur..."
	@echo ""
	uv run python scripts/create_user.py
	@echo ""

.PHONY: shell
shell: ## Ouvrir un shell Python
	@echo "Shell Python interactif..."
	@echo "   (utilisez 'exit()' pour quitter)"
	@echo ""
	uv run python

# ==========================================
# TESTS
# ==========================================

.PHONY: test
test: ## Lancer tous les tests
	@echo "Execution des tests..."
	@echo ""
	uv run pytest -v
	@echo ""
	@echo "Tests termines !"

.PHONY: test-unit
test-unit: ## Lancer les tests unitaires uniquement
	@echo "Tests unitaires..."
	@echo ""
	uv run pytest tests/unit/ -v
	@echo ""
	@echo "Tests unitaires termines !"

.PHONY: test-integration
test-integration: ## Lancer les tests d'integration
	@echo "Tests d'integration..."
	@echo ""
	uv run pytest tests/integration/ -v
	@echo ""
	@echo "Tests d'integration termines !"

.PHONY: test-critical
test-critical: ## Tests critiques uniquement (CI/CD)
	@echo "Tests critiques..."
	@echo ""
	uv run pytest -m critical -v
	@echo ""
	@echo "Tests critiques termines !"

.PHONY: test-cov
test-cov: ## Tests avec couverture
	@echo "Tests avec couverture..."
	@echo ""
	uv run pytest --cov=app --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "Rapport HTML : htmlcov/index.html"
	@echo "Tests avec couverture termines !"

# ==========================================
# QUALITE DU CODE
# ==========================================

.PHONY: lint
lint: ## Verifier le code avec Ruff
	@echo "Verification du code avec Ruff..."
	uv run ruff check app/ tests/

.PHONY: lint-fix
lint-fix: ## Corriger automatiquement les problemes
	@echo "Correction automatique avec Ruff..."
	uv run ruff check --fix app/ tests/

.PHONY: format
format: ## Formater le code avec Ruff
	@echo "Formatage du code avec Ruff..."
	uv run ruff format app/ tests/

.PHONY: format-check
format-check: ## Verifier le formatage sans modifier
	@echo "Verification du formatage..."
	uv run ruff format --check app/ tests/

.PHONY: clean-code
clean-code: ## Nettoyer et formater le code (format + lint-fix)
	@echo "Nettoyage complet du code..."
	@echo ""
	@echo "[1/4] Formatage du code..."
	uv run ruff format app/ tests/
	@echo ""
	@echo "[2/4] Tri des imports..."
	uv run ruff check --select I --fix app/ tests/
	@echo ""
	@echo "[3/4] Corrections automatiques..."
	uv run ruff check --fix app/ tests/
	@echo ""
	@echo "[4/4] Verification finale..."
	uv run ruff check app/ tests/ --statistics
	@echo ""
	@echo "Code nettoye avec succes !"

.PHONY: check-all
check-all: format-check lint ## Verifier tout (format + lint) sans modifier

# ==========================================
# MAINTENANCE
# ==========================================

.PHONY: logs
logs: ## Voir les logs de l'application
	@echo "Logs de l'application..."
	@echo ""
	@if (Test-Path "logs/app.log") { Get-Content "logs/app.log" -Tail 50 -Wait } else { echo "ERREUR: Fichier de log introuvable" }

.PHONY: clean
clean: ## Nettoyer les fichiers temporaires
	@echo "Nettoyage des fichiers temporaires..."
	@echo ""
	@if (Test-Path "__pycache__") { Remove-Item -Recurse -Force "__pycache__"; echo "OK: __pycache__ supprime" }
	@if (Test-Path "app/__pycache__") { Remove-Item -Recurse -Force "app/__pycache__"; echo "OK: app/__pycache__ supprime" }
	@if (Test-Path ".pytest_cache") { Remove-Item -Recurse -Force ".pytest_cache"; echo "OK: .pytest_cache supprime" }
	@if (Test-Path ".ruff_cache") { Remove-Item -Recurse -Force ".ruff_cache"; echo "OK: .ruff_cache supprime" }
	@if (Test-Path "htmlcov") { Remove-Item -Recurse -Force "htmlcov"; echo "OK: htmlcov supprime" }
	@if (Test-Path ".coverage") { Remove-Item -Force ".coverage"; echo "OK: .coverage supprime" }
	@echo ""
	@echo "Nettoyage termine !"

.PHONY: clean-all
clean-all: clean ## Nettoyage complet (cache + logs + backups)
	@echo ""
	@echo "Nettoyage complet..."
	@echo ""
	@if (Test-Path "logs/app.log") { Clear-Content "logs/app.log"; echo "OK: Logs vides" }
	@if (Test-Path "logs/error.log") { Clear-Content "logs/error.log"; echo "OK: Error logs vides" }
	@if (Test-Path "logs/access.log") { Clear-Content "logs/access.log"; echo "OK: Access logs vides" }
	@echo ""
	@echo "Nettoyage complet termine !"

# ==========================================
# GIT & VERSION CONTROL
# ==========================================

.PHONY: git-status
git-status: ## Voir le statut Git
	@echo "Statut Git..."
	git status

.PHONY: git-log
git-log: ## Voir les derniers commits
	@echo "Historique des commits..."
	git log --oneline --graph --decorate -10

.PHONY: git-diff
git-diff: ## Voir les modifications
	@echo "Modifications non committees..."
	git diff

.PHONY: git-branches
git-branches: ## Lister les branches
	@echo "Branches Git..."
	git branch -a

.PHONY: pre-commit
pre-commit: clean-code test ## Preparation avant commit (clean + test)
	@echo ""
	@echo "Code pret a etre commite !"
	@echo ""
	@echo "Prochaines etapes :"
	@echo "  git add ."
	@echo "  git commit -m 'feat: description'"
	@echo "  git push"

.PHONY: push
push: ## Push vers origin
	@echo "Push vers origin..."
	git push origin $$(git branch --show-current)

.PHONY: pull
pull: ## Pull depuis origin
	@echo "Pull depuis origin..."
	git pull origin $$(git branch --show-current)

.PHONY: sync
sync: pull pre-commit push ## Synchroniser (pull + clean + test + push)
	@echo "Branche synchronisee !"

# ==========================================
# DOCKER (PRODUCTION & DEVELOPPEMENT)
# ==========================================

.PHONY: docker-dev
docker-dev: ## Demarrer en mode developpement avec Docker
	@echo "Demarrage en mode developpement..."
	docker-compose -f docker-compose.yml up -d
	@echo ""
	@echo "✅ Application demarree en mode developpement"
	@echo "📍 URL: http://localhost:9000"
	@echo "📊 Logs: make docker-logs-dev"

.PHONY: docker-prod
docker-prod: ## Demarrer en mode production avec Docker
	@echo "Demarrage en mode production..."
	docker-compose -f docker-compose.prod.yml up -d
	@echo ""
	@echo "✅ Application demarree en mode production"
	@echo "📍 URL: http://localhost:80 (Nginx)"
	@echo "📍 API: http://localhost:9000 (Direct)"
	@echo "📊 Logs: make docker-logs-prod"

.PHONY: docker-build-dev
docker-build-dev: ## Construire l'image de developpement
	@echo "Construction de l'image de developpement..."
	docker-compose -f docker-compose.yml build --no-cache
	@echo "✅ Image de developpement construite"

.PHONY: docker-build-prod
docker-build-prod: ## Construire l'image de production
	@echo "Construction de l'image de production..."
	docker-compose -f docker-compose.prod.yml build --no-cache
	@echo "✅ Image de production construite : mppeep-dashboard:latest"

.PHONY: docker-rebuild-prod
docker-rebuild-prod: ## 🚀 REBUILD COMPLET - Arreter, reconstruire et redemarrer (PRODUCTION)
	@Write-Host "==========================================" -ForegroundColor Cyan
	@Write-Host "REBUILD COMPLET - PRODUCTION" -ForegroundColor Yellow
	@Write-Host "==========================================" -ForegroundColor Cyan
	@Write-Host ""
	@Write-Host "[1/3] Arret des conteneurs..." -ForegroundColor White
	docker-compose -f docker-compose.prod.yml down
	@Write-Host ""
	@Write-Host "[2/3] Reconstruction de l'image (sans cache)..." -ForegroundColor White
	docker-compose -f docker-compose.prod.yml build --no-cache
	@Write-Host ""
	@Write-Host "[3/4] Demarrage des conteneurs..." -ForegroundColor White
	docker-compose -f docker-compose.prod.yml up -d
	@Write-Host ""
	@Write-Host "[4/4] Nettoyage des anciennes images..." -ForegroundColor White
	docker image prune -f
	@Write-Host ""
	@Write-Host "==========================================" -ForegroundColor Cyan
	@Write-Host "REBUILD TERMINE AVEC SUCCES !" -ForegroundColor Green
	@Write-Host "==========================================" -ForegroundColor Cyan
	@Write-Host ""
	@Write-Host "Application: http://localhost:80 (Nginx)" -ForegroundColor White
	@Write-Host "API Direct: http://localhost:9000" -ForegroundColor White
	@Write-Host "PostgreSQL: localhost:5432" -ForegroundColor White
	@Write-Host "Redis: localhost:6379" -ForegroundColor White
	@Write-Host ""
	@Write-Host "Commandes utiles:" -ForegroundColor Yellow
	@Write-Host "  make docker-logs-prod    - Voir les logs" -ForegroundColor Gray
	@Write-Host "  make docker-status       - Statut des conteneurs" -ForegroundColor Gray
	@Write-Host "  make docker-stop-prod    - Arreter" -ForegroundColor Gray
	@Write-Host ""

.PHONY: docker-stop-dev
docker-stop-dev: ## Arreter Docker dev
	@echo "Arret de l'environnement de developpement..."
	docker-compose -f docker-compose.yml down
	@echo "✅ Environnement de developpement arrete"

.PHONY: docker-stop-prod
docker-stop-prod: ## Arreter Docker prod
	@echo "Arret de l'environnement de production..."
	docker-compose -f docker-compose.prod.yml down
	@echo "✅ Environnement de production arrete"

.PHONY: docker-restart-dev
docker-restart-dev: docker-stop-dev docker-dev ## Redemarrer Docker dev

.PHONY: docker-restart-prod
docker-restart-prod: docker-stop-prod docker-prod ## Redemarrer Docker prod

.PHONY: docker-logs-dev
docker-logs-dev: ## Voir les logs Docker dev
	docker-compose -f docker-compose.yml logs -f

.PHONY: docker-logs-prod
docker-logs-prod: ## Voir les logs Docker prod (tous les services)
	docker-compose -f docker-compose.prod.yml logs -f

.PHONY: docker-logs-app
docker-logs-app: ## Voir uniquement les logs de l'application
	docker-compose -f docker-compose.prod.yml logs -f app

.PHONY: docker-status
docker-status: ## Voir le statut de tous les conteneurs
	@echo "Statut des conteneurs Docker:"
	@echo ""
	docker-compose -f docker-compose.prod.yml ps
	@echo ""
	@echo "Images Docker:"
	@docker images | Select-String -Pattern "mppeep|postgres|nginx|redis|IMAGE"

.PHONY: docker-clean-dev
docker-clean-dev: ## Nettoyer Docker dev (volumes inclus)
	@echo "Nettoyage de l'environnement de developpement..."
	docker-compose -f docker-compose.yml down -v
	@echo "✅ Environnement de developpement nettoye"

.PHONY: docker-clean-prod
docker-clean-prod: ## Nettoyer Docker prod (volumes inclus)
	@echo "⚠️  ATTENTION: Les donnees PostgreSQL seront supprimees !"
	@echo "Appuyez sur Ctrl+C pour annuler..."
	@timeout /t 5
	docker-compose -f docker-compose.prod.yml down -v
	@echo "✅ Environnement de production nettoye"

.PHONY: docker-shell-app
docker-shell-app: ## Ouvrir un shell dans le conteneur app
	@echo "Ouverture d'un shell dans le conteneur..."
	docker exec -it mppeep-app bash

.PHONY: docker-shell-db
docker-shell-db: ## Ouvrir un shell PostgreSQL
	@echo "Connexion a PostgreSQL..."
	docker exec -it mppeep-db psql -U mppeep -d mppeep_prod

.PHONY: docker-prune
docker-prune: ## Nettoyer TOUT Docker (images, conteneurs, volumes inutilises)
	@echo "⚠️  ATTENTION: Ceci va supprimer toutes les ressources Docker non utilisees !"
	@echo "Appuyez sur Ctrl+C pour annuler..."
	@timeout /t 5
	docker system prune -a --volumes -f
	@echo "✅ Docker nettoye completement"

.PHONY: docker-info
docker-info: ## Informations Docker
	@echo "=========================================="
	@echo "INFORMATIONS DOCKER"
	@echo "=========================================="
	@echo ""
	@echo "Version Docker:"
	docker --version
	@echo ""
	@echo "Images MPPEEP:"
	@docker images | Select-String -Pattern "mppeep|IMAGE"
	@echo ""
	@echo "Conteneurs en cours:"
	@docker ps --filter "name=mppeep"
	@echo ""
	@echo "Utilisation disque:"
	docker system df
	@echo ""

# ==========================================
# EXPORT / IMPORT IMAGE (Deploiement sur un autre ordinateur)
# ==========================================

.PHONY: docker-save
docker-save: ## Exporter l'image Docker dans un fichier .tar (pour transfert)
	@Write-Host "==========================================" -ForegroundColor Cyan
	@Write-Host "EXPORT DE L'IMAGE DOCKER" -ForegroundColor Yellow
	@Write-Host "==========================================" -ForegroundColor Cyan
	@Write-Host ""
	@if (!(Test-Path "deploiement_docker")) { New-Item -ItemType Directory -Path "deploiement_docker" | Out-Null }
	@$$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"; $$filename = "deploiement_docker/mppeep-dashboard_$$timestamp.tar"; Write-Host "Export en cours vers : $$filename" -ForegroundColor White; Write-Host "Cela peut prendre plusieurs minutes..." -ForegroundColor Gray; Write-Host ""; docker save mppeep:latest -o $$filename; Write-Host ""; Write-Host "==========================================" -ForegroundColor Cyan; Write-Host "EXPORT TERMINE AVEC SUCCES !" -ForegroundColor Green; Write-Host "==========================================" -ForegroundColor Cyan; Write-Host ""; $$size = [math]::Round((Get-Item $$filename).Length / 1MB, 2); Write-Host "Fichier cree : $$filename" -ForegroundColor White; Write-Host "Taille : $${size} MB" -ForegroundColor White; Write-Host ""; Write-Host "Pour transferer sur un autre ordinateur :" -ForegroundColor Yellow; Write-Host "  1. Copiez le fichier .tar sur l'autre ordinateur" -ForegroundColor Gray; Write-Host "  2. Sur l'autre ordinateur, lancez : make docker-load" -ForegroundColor Gray; Write-Host ""

.PHONY: docker-load
docker-load: ## Importer l'image Docker depuis un fichier .tar
	@Write-Host "==========================================" -ForegroundColor Cyan
	@Write-Host "IMPORT DE L'IMAGE DOCKER" -ForegroundColor Yellow
	@Write-Host "==========================================" -ForegroundColor Cyan
	@Write-Host ""
	@$$files = Get-ChildItem -Path "deploiement_docker" -Filter "mppeep-dashboard_*.tar" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
	@if ($$files.Count -eq 0) { \
		Write-Host "ERREUR : Aucun fichier .tar trouve dans deploiement_docker/" -ForegroundColor Red; \
		Write-Host "" ; \
		Write-Host "Verifiez que le fichier .tar est dans le dossier deploiement_docker/" -ForegroundColor Yellow; \
		exit 1; \
	}
	@$$latestFile = $$files[0].FullName
	@Write-Host "Fichier detecte : $$latestFile" -ForegroundColor White
	@Write-Host "Import en cours... (cela peut prendre plusieurs minutes)" -ForegroundColor Gray
	@Write-Host ""
	docker load -i $$latestFile
	@Write-Host ""
	@Write-Host "==========================================" -ForegroundColor Cyan
	@Write-Host "IMPORT TERMINE AVEC SUCCES !" -ForegroundColor Green
	@Write-Host "==========================================" -ForegroundColor Cyan
	@Write-Host ""
	@Write-Host "L'image est prete a etre utilisee !" -ForegroundColor White
	@Write-Host "Lancez : make docker-prod" -ForegroundColor Yellow
	@Write-Host ""

.PHONY: docker-export
docker-export: docker-save ## Alias pour docker-save

.PHONY: docker-import
docker-import: docker-load ## Alias pour docker-load

.PHONY: docker-package
docker-package: ## Package complet pour deploiement (image + config)
	@Write-Host "==========================================" -ForegroundColor Cyan
	@Write-Host "PACKAGE COMPLET DE DEPLOIEMENT" -ForegroundColor Yellow
	@Write-Host "==========================================" -ForegroundColor Cyan
	@Write-Host ""
	@if (!(Test-Path "deploiement_docker")) { New-Item -ItemType Directory -Path "deploiement_docker" | Out-Null }
	@$$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
	@$$packageDir = "deploiement_docker/mppeep-package_$$timestamp"
	@Write-Host "[1/4] Creation du dossier de package..." -ForegroundColor White
	New-Item -ItemType Directory -Path $$packageDir | Out-Null
	@Write-Host ""
	@Write-Host "[2/4] Export de l'image Docker..." -ForegroundColor White
	docker save mppeep:latest -o "$$packageDir/mppeep-image.tar"
	@Write-Host ""
	@Write-Host "[3/4] Copie des fichiers de configuration..." -ForegroundColor White
	Copy-Item "docker-compose.prod.yml" "$$packageDir/"
	Copy-Item "env.production.template" "$$packageDir/.env.template"
	Copy-Item "deploiement_docker/nginx.conf" "$$packageDir/" -ErrorAction SilentlyContinue
	@Write-Host ""
	@Write-Host "[4/4] Creation du README de deploiement..." -ForegroundColor White
	@$$readme = @"
	# MPPEEP Dashboard - Package de Deploiement
	Date: $$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
	
	## Contenu du package
	- mppeep-image.tar : Image Docker complete
	- docker-compose.prod.yml : Configuration Docker Compose
	- .env.template : Template des variables d'environnement
	- nginx.conf : Configuration Nginx
	
	## Installation sur un nouveau serveur
	
	### 1. Prerequisites
	- Docker et Docker Compose installes
	- Ports 80, 443, 5432, 6379, 9000 disponibles
	
	### 2. Charger l'image Docker
	``````powershell
	docker load -i mppeep-image.tar
	``````
	
	### 3. Configurer les variables d'environnement
	``````powershell
	# Copier le template
	Copy-Item .env.template .env
	
	# Editer .env et renseigner :
	# - POSTGRES_PASSWORD
	# - SECRET_KEY
	# - Autres variables selon vos besoins
	``````
	
	### 4. Creer les dossiers necessaires
	``````powershell
	New-Item -ItemType Directory -Path backups, ssl -Force
	``````
	
	### 5. Demarrer les services
	``````powershell
	docker-compose -f docker-compose.prod.yml up -d
	``````
	
	### 6. Verifier le deploiement
	``````powershell
	docker-compose -f docker-compose.prod.yml ps
	docker-compose -f docker-compose.prod.yml logs -f app
	``````
	
	## URLs d'acces
	- Application : http://localhost:80 (Nginx)
	- API Direct : http://localhost:9000
	- PostgreSQL : localhost:5432
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
	``````
	
	## Support
	Contact : support@mppeep.gov
	"@
	Set-Content -Path "$$packageDir/README.md" -Value $$readme -Encoding UTF8
	@Write-Host ""
	@Write-Host "==========================================" -ForegroundColor Cyan
	@Write-Host "PACKAGE CREE AVEC SUCCES !" -ForegroundColor Green
	@Write-Host "==========================================" -ForegroundColor Cyan
	@Write-Host ""
	@$$size = [math]::Round((Get-ChildItem -Path $$packageDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
	@Write-Host "Dossier : $$packageDir" -ForegroundColor White
	@Write-Host "Taille totale : $${size} MB" -ForegroundColor White
	@Write-Host ""
	@Write-Host "Pour deployer sur un autre ordinateur :" -ForegroundColor Yellow
	@Write-Host "  1. Copiez le dossier complet sur l'autre ordinateur" -ForegroundColor Gray
	@Write-Host "  2. Suivez les instructions dans README.md" -ForegroundColor Gray
	@Write-Host ""

# ==========================================
# DEPLOIEMENT VERS UN REGISTRE DOCKER (Optionnel)
# ==========================================

.PHONY: docker-tag
docker-tag: ## Taguer l'image pour un registre (usage: make docker-tag REGISTRY=registry.example.com)
	@if (-not $$env:REGISTRY) { \
		Write-Host "ERREUR: Veuillez specifier le registre" -ForegroundColor Red; \
		Write-Host "Usage: make docker-tag REGISTRY=registry.example.com" -ForegroundColor Yellow; \
		Write-Host "Exemple: make docker-tag REGISTRY=docker.io/votrecompte" -ForegroundColor Gray; \
		exit 1; \
	}
	@Write-Host "Tagging de l'image pour : $$env:REGISTRY/mppeep-dashboard:latest" -ForegroundColor White
	docker tag mppeep:latest $$env:REGISTRY/mppeep-dashboard:latest
	@Write-Host "Image taguee avec succes !" -ForegroundColor Green

.PHONY: docker-push
docker-push: ## Pousser l'image vers un registre (usage: make docker-push REGISTRY=registry.example.com)
	@if (-not $$env:REGISTRY) { \
		Write-Host "ERREUR: Veuillez specifier le registre" -ForegroundColor Red; \
		Write-Host "Usage: make docker-push REGISTRY=registry.example.com" -ForegroundColor Yellow; \
		exit 1; \
	}
	@Write-Host "Push vers : $$env:REGISTRY/mppeep-dashboard:latest" -ForegroundColor White
	docker push $$env:REGISTRY/mppeep-dashboard:latest
	@Write-Host "Image poussee avec succes !" -ForegroundColor Green

.PHONY: docker-pull
docker-pull: ## Tirer l'image depuis un registre (usage: make docker-pull REGISTRY=registry.example.com)
	@if (-not $$env:REGISTRY) { \
		Write-Host "ERREUR: Veuillez specifier le registre" -ForegroundColor Red; \
		Write-Host "Usage: make docker-pull REGISTRY=registry.example.com" -ForegroundColor Yellow; \
		exit 1; \
	}
	@Write-Host "Pull depuis : $$env:REGISTRY/mppeep-dashboard:latest" -ForegroundColor White
	docker pull $$env:REGISTRY/mppeep-dashboard:latest
	docker tag $$env:REGISTRY/mppeep-dashboard:latest mppeep:latest
	@Write-Host "Image tiree avec succes !" -ForegroundColor Green

# Alias pour compatibilite
.PHONY: local-install
local-install: install

.PHONY: local-test
local-test: test
