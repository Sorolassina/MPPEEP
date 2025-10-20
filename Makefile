# ============================================
# MAKEFILE - MPPEEP DASHBOARD
# ============================================
# Commandes simplifiées pour Docker et développement
# Usage : make help
# ============================================

.PHONY: help
help: ## Afficher l'aide
	@echo "=========================================="
	@echo "🚀 MPPEEP Dashboard - Commandes"
	@echo "=========================================="
	@echo ""
	@echo "⚡ DÉVELOPPEMENT (sans Docker) - RECOMMANDÉ:"
	@echo "  make install        - Installer dépendances"
	@echo "  make run            - Lancer l'app (hot-reload)"
	@echo "  make test           - Lancer les tests"
	@echo "  make test-critical  - Tests critiques CI/CD"
	@echo "  make test-cov       - Tests avec couverture"
	@echo "  make db-init        - Initialiser la DB"
	@echo "  make db-reset       - Réinitialiser la DB"
	@echo "  make create-admin   - Créer un admin"
	@echo "  make clean          - Nettoyer fichiers temp"
	@echo ""
	@echo "📋 QUALITÉ DU CODE:"
	@echo "  make lint           - Vérifier le code"
	@echo "  make lint-fix       - Corriger automatiquement"
	@echo "  make format         - Formater le code"
	@echo "  make clean-code     - Nettoyage complet"
	@echo "  make check-all      - Vérifier sans modifier"
	@echo ""
	@echo "🔀 GIT:"
	@echo "  make git-status     - Statut Git"
	@echo "  make git-log        - Derniers commits"
	@echo "  make pre-commit     - Préparer commit (clean + test)"
	@echo "  make push           - Push vers origin"
	@echo "  make pull           - Pull depuis origin"
	@echo "  make sync           - Sync complète"
	@echo ""
	@echo "🐳 DOCKER (optionnel):"
	@echo "  make dev-up         - Docker dev"
	@echo "  make dev-down       - Arrêter Docker dev"
	@echo "  make up             - Docker prod"
	@echo "  make down           - Arrêter Docker prod"
	@echo ""
	@echo "=========================================="
	@echo "💡 Commande rapide : make run"
	@echo "=========================================="

# ==========================================
# DOCKER - DÉVELOPPEMENT
# ==========================================

.PHONY: dev-up
dev-up: ## Démarrer en mode développement (hot-reload)
	docker-compose -f docker-compose.dev.yml up -d
	@echo "✅ Application démarrée en mode développement"
	@echo "🌐 http://localhost:8000"

.PHONY: dev-down
dev-down: ## Arrêter le mode développement
	docker-compose -f docker-compose.dev.yml down

.PHONY: dev-logs
dev-logs: ## Voir les logs (développement)
	docker-compose -f docker-compose.dev.yml logs -f

.PHONY: dev-restart
dev-restart: ## Redémarrer (développement)
	docker-compose -f docker-compose.dev.yml restart

# ==========================================
# DOCKER - PRODUCTION
# ==========================================

.PHONY: up
up: ## Démarrer en mode production
	docker-compose up -d
	@echo "✅ Application démarrée en mode production"
	@echo "🌐 http://localhost:8000"

.PHONY: down
down: ## Arrêter la production
	docker-compose down

.PHONY: logs
logs: ## Voir les logs (production)
	docker-compose logs -f

.PHONY: restart
restart: ## Redémarrer (production)
	docker-compose restart

.PHONY: ps
ps: ## Voir le statut des conteneurs
	docker-compose ps

# ==========================================
# BUILD
# ==========================================

.PHONY: build
build: ## Construire les images Docker
	docker-compose build
	@echo "✅ Images construites"

.PHONY: rebuild
rebuild: ## Reconstruire sans cache
	docker-compose build --no-cache
	@echo "✅ Images reconstruites"

# ==========================================
# DATABASE
# ==========================================

.PHONY: db-shell
db-shell: ## Ouvrir psql dans PostgreSQL
	docker-compose exec db psql -U postgres -d mppeep

.PHONY: db-backup
db-backup: ## Créer un backup de la base
	@mkdir -p backups
	docker-compose exec -T db pg_dump -U postgres mppeep > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup créé dans backups/"

.PHONY: db-restore
db-restore: ## Restaurer depuis le dernier backup
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Usage: make db-restore FILE=backups/backup.sql"; \
		exit 1; \
	fi
	docker-compose exec -T db psql -U postgres mppeep < $(FILE)
	@echo "✅ Base restaurée depuis $(FILE)"

# ==========================================
# APPLICATION
# ==========================================

.PHONY: shell
shell: ## Ouvrir un shell dans le conteneur app
	docker-compose exec app bash

.PHONY: python
python: ## Ouvrir Python interactif
	docker-compose exec app python

.PHONY: create-user
create-user: ## Créer un utilisateur (EMAIL=x NOM=x PASS=x)
	@if [ -z "$(EMAIL)" ]; then \
		docker-compose exec app python scripts/create_user.py; \
	else \
		docker-compose exec app python scripts/create_user.py $(EMAIL) "$(NOM)" $(PASS); \
	fi

# ==========================================
# TESTS
# ==========================================

.PHONY: test
test: ## Lancer tous les tests
	docker-compose exec app uv run pytest -v

.PHONY: test-unit
test-unit: ## Lancer les tests unitaires
	docker-compose exec app uv run pytest tests/unit/ -v

.PHONY: test-integration
test-integration: ## Lancer les tests d'intégration
	docker-compose exec app uv run pytest tests/integration/ -v

.PHONY: test-cov
test-cov: ## Tests avec couverture de code
	docker-compose exec app uv run pytest --cov=app --cov-report=term-missing

# ==========================================
# NETTOYAGE
# ==========================================

.PHONY: clean
clean: ## Arrêter et supprimer les conteneurs
	docker-compose down
	docker-compose -f docker-compose.dev.yml down

.PHONY: clean-all
clean-all: ## Tout nettoyer (⚠️ supprime les volumes)
	docker-compose down -v
	docker-compose -f docker-compose.dev.yml down -v
	@echo "⚠️  Volumes supprimés - Données perdues!"

.PHONY: prune
prune: ## Nettoyer les images Docker inutilisées
	docker system prune -f
	@echo "✅ Images inutilisées supprimées"

# ==========================================
# OUTILS
# ==========================================

.PHONY: pgadmin
pgadmin: ## Démarrer pgAdmin (interface web DB)
	docker-compose --profile tools up -d pgadmin
	@echo "✅ pgAdmin démarré"
	@echo "🌐 http://localhost:5050"

.PHONY: config
config: ## Afficher la configuration actuelle
	docker-compose exec app python scripts/show_config.py

.PHONY: init-db
init-db: ## Réinitialiser la base de données
	docker-compose exec app python scripts/init_db.py

# ==========================================
# DÉVELOPPEMENT LOCAL (sans Docker) - COMMANDES PRINCIPALES
# ==========================================

.PHONY: install
install: ## Installer les dépendances
	@echo "📦 Installation des dépendances..."
	uv sync --extra dev
	@echo "✅ Dépendances installées !"

.PHONY: run
run: ## Lancer l'application (hot-reload)
	@echo "🚀 Démarrage de l'application..."
	@echo "🌐 http://localhost:9000"
	@echo ""
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 9000

.PHONY: test
test: ## Lancer tous les tests
	@echo "🧪 Exécution des tests..."
	uv run pytest -v

.PHONY: test-critical
test-critical: ## Tests critiques uniquement (CI/CD)
	@echo "🧪 Tests critiques..."
	uv run pytest -m critical -v

.PHONY: test-cov
test-cov: ## Tests avec couverture
	@echo "📊 Tests avec couverture..."
	uv run pytest --cov=app --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "📈 Rapport : htmlcov/index.html"

.PHONY: db-init
db-init: ## Initialiser la base de données
	@echo "🗄️ Initialisation de la base de données..."
	uv run python scripts/init_db.py

.PHONY: db-reset
db-reset: ## Réinitialiser la DB (supprime toutes les données)
	@echo "⚠️ Réinitialisation de la base de données..."
	@if exist mppeep.db del /f mppeep.db
	uv run python scripts/init_db.py
	@echo "✅ Base de données réinitialisée !"

.PHONY: create-admin
create-admin: ## Créer un utilisateur admin
	@echo "👤 Création d'un administrateur..."
	uv run python scripts/create_admin.py

.PHONY: shell
shell: ## Ouvrir un shell Python
	@echo "🐍 Shell Python interactif..."
	uv run python

.PHONY: clean
clean: ## Nettoyer les fichiers temporaires
	@echo "🧹 Nettoyage..."
	@if exist __pycache__ rmdir /s /q __pycache__
	@if exist .pytest_cache rmdir /s /q .pytest_cache
	@if exist .ruff_cache rmdir /s /q .ruff_cache
	@if exist htmlcov rmdir /s /q htmlcov
	@if exist .coverage del /f .coverage
	@echo "✅ Nettoyage terminé !"

# Alias pour compatibilité
.PHONY: local-install
local-install: install

.PHONY: local-run
local-run: run

.PHONY: local-test
local-test: test

# ==========================================
# CI/CD & CODE QUALITY
# ==========================================

.PHONY: lint
lint: ## Vérifier le code avec Ruff
	@echo "🔍 Vérification du code avec Ruff..."
	uv run ruff check app/ tests/

.PHONY: lint-fix
lint-fix: ## Corriger automatiquement les problèmes
	@echo "🔧 Correction automatique avec Ruff..."
	uv run ruff check --fix app/ tests/

.PHONY: format
format: ## Formater le code avec Ruff
	@echo "🎨 Formatage du code avec Ruff..."
	uv run ruff format app/ tests/

.PHONY: format-check
format-check: ## Vérifier le formatage sans modifier
	@echo "👀 Vérification du formatage..."
	uv run ruff format --check app/ tests/

.PHONY: clean-code
clean-code: ## Nettoyer et formater le code (format + lint-fix)
	@echo "🧹 Nettoyage complet du code..."
	@echo ""
	@echo "1️⃣ Formatage du code..."
	uv run ruff format app/ tests/
	@echo ""
	@echo "2️⃣ Tri des imports..."
	uv run ruff check --select I --fix app/ tests/
	@echo ""
	@echo "3️⃣ Corrections automatiques..."
	uv run ruff check --fix app/ tests/
	@echo ""
	@echo "4️⃣ Vérification finale..."
	uv run ruff check app/ tests/ --statistics
	@echo ""
	@echo "✅ Code nettoyé avec succès !"

.PHONY: check-all
check-all: format-check lint ## Vérifier tout (format + lint) sans modifier

# ==========================================
# GIT & VERSION CONTROL
# ==========================================

.PHONY: git-status
git-status: ## Voir le statut Git
	@echo "📊 Statut Git..."
	git status

.PHONY: git-log
git-log: ## Voir les derniers commits
	@echo "📜 Historique des commits..."
	git log --oneline --graph --decorate -10

.PHONY: git-diff
git-diff: ## Voir les modifications
	@echo "🔍 Modifications non committées..."
	git diff

.PHONY: git-branches
git-branches: ## Lister les branches
	@echo "🌿 Branches Git..."
	git branch -a

.PHONY: pre-commit
pre-commit: clean-code local-test ## Préparation avant commit (clean + test)
	@echo ""
	@echo "✅ Code prêt à être commité !"
	@echo ""
	@echo "Prochaines étapes :"
	@echo "  git add ."
	@echo "  git commit -m 'feat: description'"
	@echo "  git push"

.PHONY: commit
commit: pre-commit ## Commit interactif après nettoyage
	@echo ""
	@echo "📝 Ajout des fichiers..."
	git add .
	@echo ""
	@echo "📊 Fichiers modifiés :"
	git status --short
	@echo ""
	@echo "💬 Message du commit :"
	@read -p "  → " msg; git commit -m "$$msg"

.PHONY: push
push: ## Push vers origin
	@echo "📤 Push vers origin..."
	git push origin $$(git branch --show-current)

.PHONY: pull
pull: ## Pull depuis origin
	@echo "📥 Pull depuis origin..."
	git pull origin $$(git branch --show-current)

.PHONY: sync
sync: pull pre-commit push ## Synchroniser (pull + clean + test + push)
	@echo "✅ Branche synchronisée !"

