# 🐳 Aide-Mémoire Docker - Commandes Rapides

## 🎯 Commandes Make (Recommandé)

```bash
# Voir toutes les commandes disponibles
make help

# Développement
make dev-up          # Démarrer (hot-reload)
make dev-logs        # Voir les logs
make dev-down        # Arrêter

# Production
make up              # Démarrer
make logs            # Voir les logs
make down            # Arrêter
make ps              # Statut

# Build
make build           # Construire les images
make rebuild         # Reconstruire (sans cache)

# Database
make db-shell        # Ouvrir psql
make db-backup       # Créer un backup
make db-restore FILE=backup.sql  # Restaurer

# Application
make shell           # Shell dans le conteneur
make create-user EMAIL=user@test.com NOM="User" PASS=pass123

# Tests
make test            # Tous les tests
make test-unit       # Tests unitaires
make test-cov        # Avec couverture

# Nettoyage
make clean           # Arrêter les conteneurs
make clean-all       # Tout supprimer (⚠️ données)
make prune           # Nettoyer Docker

# Outils
make pgadmin         # Interface web DB
make config          # Voir la config
```

---

## 🐳 Commandes Docker Compose (Manuelles)

### Démarrage

```bash
# Production
docker-compose up -d

# Développement
docker-compose -f docker-compose.dev.yml up -d

# Avec rebuild
docker-compose up -d --build

# Mode interactif (voir les logs)
docker-compose up
```

---

### Arrêt

```bash
# Arrêter
docker-compose down

# Arrêter et supprimer les volumes (⚠️ perte de données)
docker-compose down -v

# Arrêter un service spécifique
docker-compose stop app
docker-compose stop db
```

---

### Logs

```bash
# Tous les services
docker-compose logs -f

# Un service spécifique
docker-compose logs -f app
docker-compose logs -f db

# Dernières 100 lignes
docker-compose logs --tail=100 app

# Depuis un moment
docker-compose logs --since 30m app
```

---

### Status

```bash
# Voir les conteneurs
docker-compose ps

# Détails complets
docker-compose ps -a

# Voir les ports
docker-compose port app 8000
```

---

### Rebuild

```bash
# Rebuild un service
docker-compose build app

# Rebuild sans cache
docker-compose build --no-cache

# Rebuild et redémarrer
docker-compose up -d --build
```

---

## 🔧 Commandes dans les Conteneurs

### Application

```bash
# Shell interactif
docker-compose exec app bash

# Commande Python
docker-compose exec app python scripts/create_user.py

# Tests
docker-compose exec app uv run pytest -v

# Config
docker-compose exec app python scripts/show_config.py

# Créer un user
docker-compose exec app python scripts/create_user.py user@test.com "User" "pass"
```

---

### Base de Données

```bash
# psql interactif
docker-compose exec db psql -U postgres -d mppeep

# Commande SQL directe
docker-compose exec db psql -U postgres -d mppeep -c "SELECT * FROM user;"

# Voir les tables
docker-compose exec db psql -U postgres -d mppeep -c "\dt"

# Backup
docker-compose exec db pg_dump -U postgres mppeep > backup.sql

# Restore
docker-compose exec -T db psql -U postgres mppeep < backup.sql
```

---

## 🗑️ Nettoyage

### Conteneurs

```bash
# Arrêter et supprimer les conteneurs
docker-compose down

# Supprimer aussi les volumes
docker-compose down -v

# Supprimer les images
docker rmi mppeep-app mppeep-db
```

---

### Système Docker

```bash
# Nettoyer tout Docker
docker system prune -f

# Nettoyer tout + volumes
docker system prune -a --volumes

# Voir l'espace utilisé
docker system df
```

---

## 🎯 Workflows Courants

### Développement

```bash
# 1. Démarrer
make dev-up

# 2. Développer (modifier le code)
code app/

# 3. Voir les logs
make dev-logs

# 4. Arrêter
make dev-down
```

---

### Tests

```bash
# Lancer les tests dans Docker
make test

# Ou manuellement
docker-compose exec app uv run pytest -v
```

---

### Déploiement

```bash
# 1. Build
make build

# 2. Tester localement
make up
make logs

# 3. Si OK, push vers registry
docker tag mppeep:latest registry.company.com/mppeep:v1.0.0
docker push registry.company.com/mppeep:v1.0.0
```

---

## 📊 Résumé des Commandes

| Action | Commande Courte | Commande Complète |
|--------|-----------------|-------------------|
| **Démarrer dev** | `make dev-up` | `docker-compose -f docker-compose.dev.yml up -d` |
| **Démarrer prod** | `make up` | `docker-compose up -d` |
| **Logs** | `make logs` | `docker-compose logs -f` |
| **Arrêter** | `make down` | `docker-compose down` |
| **Rebuild** | `make rebuild` | `docker-compose build --no-cache` |
| **Shell** | `make shell` | `docker-compose exec app bash` |
| **Tests** | `make test` | `docker-compose exec app uv run pytest` |
| **Backup** | `make db-backup` | `docker-compose exec db pg_dump ...` |

---

**💡 Utilisez `make help` pour voir toutes les commandes ! 🚀**

