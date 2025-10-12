# ============================================
# MAKEFILE - MPPEEP DASHBOARD
# ============================================
# Commandes simplifiées pour Docker et développement
# Usage : make help
# ============================================

.PHONY: help
help: ## Afficher l'aide
	@echo "🚀 MPPEEP Dashboard - Commandes Disponibles"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

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
# DÉVELOPPEMENT LOCAL (sans Docker)
# ==========================================

.PHONY: local-install
local-install: ## Installer les dépendances localement
	uv sync --extra dev

.PHONY: local-run
local-run: ## Lancer l'application localement
	uvicorn app.main:app --reload

.PHONY: local-test
local-test: ## Lancer les tests localement
	uv run pytest -v

# ==========================================
# CI/CD
# ==========================================

.PHONY: lint
lint: ## Vérifier le code (linting)
	docker-compose exec app ruff check app/ tests/

.PHONY: format
format: ## Formater le code
	docker-compose exec app black app/ tests/
	docker-compose exec app isort app/ tests/

