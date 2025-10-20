# 🐳 Déploiement Docker - MPPEEP Dashboard

## 🎯 Vue d'ensemble

Ce document détaille le **déploiement de MPPEEP Dashboard avec Docker**, depuis la création des images jusqu'au déploiement en production avec Docker Compose.

---

## 📋 Table des matières

- [Prérequis](#-prérequis)
- [Dockerfile](#-dockerfile)
- [Docker Compose](#-docker-compose)
- [Variables d'environnement](#-variables-denvironnement)
- [Build et démarrage](#-build-et-démarrage)
- [Production](#-production)
- [Volumes et persistence](#-volumes-et-persistence)
- [Réseaux](#-réseaux)
- [Monitoring](#-monitoring)
- [Dépannage](#-dépannage)

---

## ✅ Prérequis

### Installation de Docker

#### Windows
```bash
# Télécharger Docker Desktop
https://www.docker.com/products/docker-desktop/

# Vérifier l'installation
docker --version
docker-compose --version
```

#### Linux (Ubuntu/Debian)
```bash
# Installation
sudo apt update
sudo apt install docker.io docker-compose

# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER
newgrp docker

# Vérifier
docker --version
docker-compose --version
```

#### macOS
```bash
# Télécharger Docker Desktop
https://www.docker.com/products/docker-desktop/

# Ou avec Homebrew
brew install --cask docker

# Vérifier
docker --version
docker-compose --version
```

---

## 🐳 Dockerfile

### Version Développement

Créer `Dockerfile` à la racine de `mppeep/` :

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Métadonnées
LABEL maintainer="MPPEEP <support@mppeep.gov>"
LABEL version="1.0.0"
LABEL description="MPPEEP Dashboard - Système de Gestion Intégré"

# Variables d'environnement Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Répertoire de travail
WORKDIR /app

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copier les dépendances
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY . .

# Créer les dossiers nécessaires
RUN mkdir -p logs static/uploads

# Exposer le port
EXPOSE 9000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9000/api/v1/health').read()"

# Commande de démarrage
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
```

### Version Production (Multi-stage)

```dockerfile
# Dockerfile.prod
# ============================================
# STAGE 1 : BUILDER
# ============================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Installation des dépendances de build
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier requirements
COPY requirements.txt .

# Créer un environnement virtuel
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Installer les dépendances
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================
# STAGE 2 : RUNTIME
# ============================================
FROM python:3.11-slim

# Métadonnées
LABEL maintainer="MPPEEP <support@mppeep.gov>"
LABEL version="1.0.0"
LABEL environment="production"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Installation des dépendances runtime uniquement
RUN apt-get update && apt-get install -y \
    libpq5 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root
RUN useradd -m -u 1000 mppeep && \
    chown -R mppeep:mppeep /app

# Copier l'environnement virtuel depuis le builder
COPY --from=builder /opt/venv /opt/venv

# Copier le code
COPY --chown=mppeep:mppeep . .

# Créer les dossiers
RUN mkdir -p logs static/uploads && \
    chown -R mppeep:mppeep logs static/uploads

# Passer à l'utilisateur non-root
USER mppeep

# Exposer le port
EXPOSE 9000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9000/api/v1/health').read()"

# Commande de démarrage (production avec plusieurs workers)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000", "--workers", "4"]
```

---

## 🐳 Docker Compose

### Version Développement

Créer `docker-compose.yml` :

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Application MPPEEP
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mppeep-app
    ports:
      - "9000:9000"
    environment:
      - DATABASE_URL=sqlite:///./data/mppeep.db
      - SECRET_KEY=${SECRET_KEY:-dev-secret-key-change-in-production}
      - DEBUG=True
      - APP_NAME=MPPEEP Dashboard
    volumes:
      # Code source (hot reload)
      - ./app:/app/app
      - ./static:/app/static
      - ./templates:/app/templates
      # Données persistantes
      - mppeep-data:/app/data
      - mppeep-logs:/app/logs
      - mppeep-uploads:/app/static/uploads
    command: uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
    restart: unless-stopped
    networks:
      - mppeep-network

volumes:
  mppeep-data:
  mppeep-logs:
  mppeep-uploads:

networks:
  mppeep-network:
    driver: bridge
```

### Version Production (avec PostgreSQL)

Créer `docker-compose.prod.yml` :

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  # PostgreSQL Database
  db:
    image: postgres:15-alpine
    container_name: mppeep-db
    environment:
      - POSTGRES_USER=${POSTGRES_USER:-mppeep}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB:-mppeep_prod}
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./backups:/backups
    ports:
      - "5432:5432"
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mppeep"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - mppeep-network

  # Application MPPEEP
  app:
    build:
      context: .
      dockerfile: Dockerfile.prod
    container_name: mppeep-app
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "9000:9000"
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER:-mppeep}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB:-mppeep_prod}
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=False
      - APP_NAME=MPPEEP Dashboard
      - CORS_ORIGINS=["https://mppeep.gov"]
    volumes:
      - mppeep-logs:/app/logs
      - mppeep-uploads:/app/static/uploads
    restart: always
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:9000/api/v1/health').read()"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - mppeep-network

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: mppeep-nginx
    depends_on:
      - app
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - mppeep-uploads:/usr/share/nginx/html/uploads:ro
    restart: always
    networks:
      - mppeep-network

  # Redis Cache (optionnel)
  redis:
    image: redis:7-alpine
    container_name: mppeep-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: always
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
    networks:
      - mppeep-network

volumes:
  postgres-data:
  mppeep-logs:
  mppeep-uploads:
  redis-data:

networks:
  mppeep-network:
    driver: bridge
```

---

## 🔐 Variables d'environnement

### Fichier `.env` pour Docker

Créer `.env` à la racine de `mppeep/` :

```bash
# .env pour Docker

# ============================================
# BASE DE DONNÉES
# ============================================
POSTGRES_USER=mppeep
POSTGRES_PASSWORD=VotreMotDePasseSuperSecurise123!
POSTGRES_DB=mppeep_prod

# ============================================
# APPLICATION
# ============================================
SECRET_KEY=votre-clé-secrète-super-longue-et-aléatoire-minimum-32-caractères
DEBUG=False
APP_NAME=MPPEEP Dashboard
APP_VERSION=1.0.0

# ============================================
# SÉCURITÉ
# ============================================
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=["https://mppeep.gov"]

# ============================================
# RÉSEAU (si nécessaire)
# ============================================
# HOST_PORT=9000
# NGINX_HTTP_PORT=80
# NGINX_HTTPS_PORT=443
```

### Générer les secrets

```bash
# SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# POSTGRES_PASSWORD
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

---

## 🚀 Build et Démarrage

### Développement (SQLite)

```bash
# 1. Builder l'image
docker-compose build

# 2. Démarrer
docker-compose up

# Ou en une commande
docker-compose up --build

# En arrière-plan (detached)
docker-compose up -d

# Voir les logs
docker-compose logs -f app

# Arrêter
docker-compose down
```

### Production (PostgreSQL)

```bash
# 1. Configurer les variables d'environnement
cp .env.example .env
nano .env  # Éditer les valeurs

# 2. Builder l'image de production
docker-compose -f docker-compose.prod.yml build

# 3. Démarrer tous les services
docker-compose -f docker-compose.prod.yml up -d

# 4. Vérifier le statut
docker-compose -f docker-compose.prod.yml ps

# 5. Voir les logs
docker-compose -f docker-compose.prod.yml logs -f

# 6. Arrêter
docker-compose -f docker-compose.prod.yml down
```

---

## 📦 Commandes Docker Utiles

### Gestion des conteneurs

```bash
# Lister les conteneurs actifs
docker ps

# Lister tous les conteneurs
docker ps -a

# Logs d'un conteneur
docker logs mppeep-app
docker logs -f mppeep-app  # Suivi en temps réel

# Entrer dans un conteneur
docker exec -it mppeep-app bash
docker exec -it mppeep-app sh  # Si bash n'est pas disponible

# Arrêter un conteneur
docker stop mppeep-app

# Redémarrer
docker restart mppeep-app

# Supprimer un conteneur
docker rm mppeep-app

# Supprimer tous les conteneurs arrêtés
docker container prune
```

### Gestion des images

```bash
# Lister les images
docker images

# Supprimer une image
docker rmi mppeep-app:latest

# Supprimer les images non utilisées
docker image prune

# Builder une image manuellement
docker build -t mppeep-app:latest .
docker build -f Dockerfile.prod -t mppeep-app:prod .

# Tag d'une image
docker tag mppeep-app:latest mppeep-app:v1.0.0
```

### Gestion des volumes

```bash
# Lister les volumes
docker volume ls

# Inspecter un volume
docker volume inspect mppeep_mppeep-data

# Supprimer un volume
docker volume rm mppeep_mppeep-data

# Supprimer tous les volumes non utilisés
docker volume prune
```

---

## 💾 Volumes et Persistence

### Volumes définis

```yaml
volumes:
  mppeep-data:        # Base de données SQLite
  mppeep-logs:        # Logs de l'application
  mppeep-uploads:     # Fichiers uploadés
  postgres-data:      # Données PostgreSQL (prod)
  redis-data:         # Cache Redis (prod)
```

### Localisation des volumes

```bash
# Trouver le chemin physique d'un volume
docker volume inspect mppeep_mppeep-data

# Résultat typique (Linux)
/var/lib/docker/volumes/mppeep_mppeep-data/_data

# Résultat typique (Windows)
\\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\mppeep_mppeep-data\_data
```

### Sauvegarder les volumes

```bash
# Sauvegarder la base de données
docker run --rm \
  -v mppeep_mppeep-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/mppeep-db-$(date +%Y%m%d).tar.gz -C /data .

# Restaurer
docker run --rm \
  -v mppeep_mppeep-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/mppeep-db-20250119.tar.gz -C /data
```

### Bind Mounts (développement)

Pour le hot-reload en développement :

```yaml
volumes:
  - ./app:/app/app              # Code source
  - ./static:/app/static        # CSS/JS
  - ./templates:/app/templates  # Templates HTML
```

**Résultat** : Modifications du code prises en compte immédiatement.

---

## 🌐 Réseaux Docker

### Réseau par défaut

```yaml
networks:
  mppeep-network:
    driver: bridge
```

**Communication inter-conteneurs** :
- `app` peut accéder à `db` via `http://db:5432`
- `nginx` peut accéder à `app` via `http://app:9000`

### DNS interne

Docker crée automatiquement des entrées DNS :
- `db` → IP du conteneur PostgreSQL
- `app` → IP du conteneur MPPEEP
- `redis` → IP du conteneur Redis

---

## 🔒 Configuration Nginx (Reverse Proxy)

### Fichier `nginx.conf`

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream mppeep_app {
        server app:9000;
    }

    # Redirection HTTP → HTTPS
    server {
        listen 80;
        server_name mppeep.gov www.mppeep.gov;
        
        location / {
            return 301 https://$server_name$request_uri;
        }
    }

    # HTTPS
    server {
        listen 443 ssl http2;
        server_name mppeep.gov www.mppeep.gov;

        # Certificats SSL
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        
        # Configuration SSL moderne
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Sécurité
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # Taille max des uploads
        client_max_body_size 50M;

        # Proxy vers l'application FastAPI
        location / {
            proxy_pass http://mppeep_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Fichiers statiques (performance)
        location /static/ {
            alias /usr/share/nginx/html/static/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        # Uploads
        location /uploads/ {
            alias /usr/share/nginx/html/uploads/;
            expires 7d;
        }

        # Health check
        location /health {
            access_log off;
            return 200 "OK\n";
            add_header Content-Type text/plain;
        }
    }
}
```

---

## 📊 Monitoring et Logs

### Voir les logs

```bash
# Logs de tous les services
docker-compose logs -f

# Logs d'un service spécifique
docker-compose logs -f app
docker-compose logs -f db
docker-compose logs -f nginx

# Dernières 100 lignes
docker-compose logs --tail=100 app

# Logs depuis une heure
docker-compose logs --since 1h app
```

### Monitoring des ressources

```bash
# Utilisation CPU/RAM/Réseau
docker stats

# Stats d'un conteneur spécifique
docker stats mppeep-app

# Informations détaillées
docker inspect mppeep-app
```

### Health Checks

```bash
# Vérifier le statut de santé
docker ps

# Colonnes affichées :
# STATUS : Up (healthy) / Up (unhealthy) / Up

# Logs du health check
docker inspect --format='{{json .State.Health}}' mppeep-app | python -m json.tool
```

---

## 🔄 Migrations et Mises à jour

### Mettre à jour l'application

```bash
# 1. Pull les dernières modifications
git pull origin main

# 2. Rebuild l'image
docker-compose -f docker-compose.prod.yml build

# 3. Redémarrer avec la nouvelle image
docker-compose -f docker-compose.prod.yml up -d

# 4. Vérifier
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f app
```

### Migrations de base de données

```bash
# Entrer dans le conteneur
docker exec -it mppeep-app bash

# Lancer le script de migration
python scripts/migrate_db.py

# Ou directement
docker exec -it mppeep-app python scripts/migrate_db.py
```

### Sauvegarde avant mise à jour

```bash
# Sauvegarder PostgreSQL
docker exec mppeep-db pg_dump -U mppeep mppeep_prod > backups/mppeep_$(date +%Y%m%d_%H%M%S).sql

# Sauvegarder SQLite
docker cp mppeep-app:/app/data/mppeep.db backups/mppeep_$(date +%Y%m%d_%H%M%S).db

# Sauvegarder les uploads
docker run --rm \
  -v mppeep_mppeep-uploads:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/uploads_$(date +%Y%m%d).tar.gz -C /data .
```

---

## 🚀 Déploiement en Production

### Checklist pré-déploiement

- [ ] ✅ Fichier `.env` configuré avec secrets sécurisés
- [ ] ✅ `DEBUG=False` dans `.env`
- [ ] ✅ `DATABASE_URL` pointe vers PostgreSQL
- [ ] ✅ Certificats SSL présents dans `./ssl/`
- [ ] ✅ `nginx.conf` configuré avec le bon domaine
- [ ] ✅ Tests passent : `docker-compose -f docker-compose.prod.yml run --rm app pytest -m critical`
- [ ] ✅ Sauvegarde configurée (cron job)

### Déploiement initial

```bash
# 1. Cloner sur le serveur
git clone https://github.com/votre-org/mppeep-dashboard.git
cd mppeep-dashboard/mppeep

# 2. Configuration
cp .env.example .env
nano .env  # Éditer les secrets

# 3. Obtenir les certificats SSL (Let's Encrypt)
sudo certbot certonly --standalone -d mppeep.gov -d www.mppeep.gov
sudo cp /etc/letsencrypt/live/mppeep.gov/fullchain.pem ./ssl/
sudo cp /etc/letsencrypt/live/mppeep.gov/privkey.pem ./ssl/

# 4. Build et démarrage
docker-compose -f docker-compose.prod.yml up -d --build

# 5. Créer l'admin initial
docker exec -it mppeep-app python scripts/create_admin.py

# 6. Vérifier
curl https://mppeep.gov/api/v1/health
```

### Renouvellement SSL automatique

```bash
# Cron job pour renouveler les certificats
0 0 1 * * certbot renew --quiet && \
  cp /etc/letsencrypt/live/mppeep.gov/fullchain.pem /path/to/mppeep/ssl/ && \
  cp /etc/letsencrypt/live/mppeep.gov/privkey.pem /path/to/mppeep/ssl/ && \
  docker-compose -f /path/to/mppeep/docker-compose.prod.yml restart nginx
```

---

## 🛠️ Tâches de Maintenance

### Sauvegardes automatiques

```bash
# Script backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/path/to/backups"

# Sauvegarder PostgreSQL
docker exec mppeep-db pg_dump -U mppeep mppeep_prod | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Sauvegarder les uploads
docker run --rm \
  -v mppeep_mppeep-uploads:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/uploads_$DATE.tar.gz -C /data .

# Nettoyer les anciennes sauvegardes (>30 jours)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "✅ Sauvegarde terminée : $DATE"
```

**Cron job** :
```bash
# Sauvegarder tous les jours à 2h du matin
0 2 * * * /path/to/backup.sh >> /var/log/mppeep-backup.log 2>&1
```

### Nettoyage

```bash
# Supprimer les conteneurs arrêtés
docker container prune -f

# Supprimer les images non utilisées
docker image prune -a -f

# Supprimer les volumes non utilisés
docker volume prune -f

# Nettoyage complet (ATTENTION : perte de données possibles)
docker system prune -a --volumes -f
```

### Redémarrage des services

```bash
# Redémarrer tous les services
docker-compose -f docker-compose.prod.yml restart

# Redémarrer un service spécifique
docker-compose -f docker-compose.prod.yml restart app
docker-compose -f docker-compose.prod.yml restart db
docker-compose -f docker-compose.prod.yml restart nginx
```

---

## 🔍 Dépannage

### Problème 1 : Conteneur ne démarre pas

```bash
# Voir les logs
docker-compose logs app

# Vérifier la configuration
docker-compose config

# Inspecter le conteneur
docker inspect mppeep-app

# Vérifier les ports
netstat -an | grep 9000  # Windows/Linux
lsof -i :9000  # Mac/Linux
```

### Problème 2 : Erreur de connexion à la DB

```bash
# Vérifier que PostgreSQL est démarré
docker-compose ps db

# Tester la connexion depuis l'app
docker exec -it mppeep-app psql -h db -U mppeep -d mppeep_prod

# Vérifier les variables d'environnement
docker exec mppeep-app env | grep DATABASE
```

### Problème 3 : Permissions

```bash
# Vérifier les permissions des volumes
docker exec -it mppeep-app ls -la /app/logs
docker exec -it mppeep-app ls -la /app/data

# Corriger les permissions
docker exec -it mppeep-app chown -R mppeep:mppeep /app/logs
```

### Problème 4 : Mémoire insuffisante

```bash
# Augmenter la limite mémoire du conteneur
# Dans docker-compose.yml :
services:
  app:
    mem_limit: 2g
    mem_reservation: 1g
```

---

## 📈 Optimisations

### Image plus légère

```dockerfile
# Utiliser alpine (image plus petite)
FROM python:3.11-alpine

# Multi-stage build
FROM python:3.11-slim AS builder
# ... build ...

FROM python:3.11-slim
COPY --from=builder /opt/venv /opt/venv
```

**Résultat** : Image de ~200 MB au lieu de ~1 GB

### Cache des layers

```dockerfile
# Copier requirements AVANT le code
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copier le code (change fréquemment)
COPY . .
```

**Résultat** : Build plus rapide (cache des dépendances)

### Workers multiples

```yaml
# Production : plusieurs workers
command: uvicorn app.main:app --host 0.0.0.0 --port 9000 --workers 4
```

**Calcul** : `workers = (2 * CPU cores) + 1`

---

## 🔐 Sécurité

### Bonnes pratiques

1. **Ne pas exécuter en root**
```dockerfile
RUN useradd -m -u 1000 mppeep
USER mppeep
```

2. **Secrets hors du code**
```yaml
environment:
  - SECRET_KEY=${SECRET_KEY}  # Depuis .env
```

3. **Scanner les vulnérabilités**
```bash
docker scan mppeep-app:latest
```

4. **Limiter les ressources**
```yaml
services:
  app:
    mem_limit: 2g
    cpus: 2
```

5. **Réseau isolé**
```yaml
networks:
  mppeep-network:
    driver: bridge
    internal: false  # Accès internet
```

---

## 📊 Exemple Complet de Déploiement

### Structure de fichiers

```
mppeep/
├── .env                        # Variables d'environnement
├── .env.example                # Template
├── Dockerfile                  # Image développement
├── Dockerfile.prod             # Image production
├── docker-compose.yml          # Dev (SQLite)
├── docker-compose.prod.yml     # Prod (PostgreSQL + Nginx)
├── nginx.conf                  # Configuration Nginx
├── ssl/                        # Certificats SSL
│   ├── fullchain.pem
│   └── privkey.pem
├── backups/                    # Sauvegardes
└── scripts/
    ├── create_admin.py
    ├── migrate_db.py
    └── backup.sh
```

### Commandes de déploiement

```bash
# 1. Configuration
cp .env.example .env
nano .env

# 2. Build
docker-compose -f docker-compose.prod.yml build

# 3. Démarrage
docker-compose -f docker-compose.prod.yml up -d

# 4. Vérification
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f

# 5. Initialisation
docker exec -it mppeep-app python scripts/create_admin.py

# 6. Test
curl https://mppeep.gov/api/v1/health
```

---

## 🎯 Docker Compose Commandes Essentielles

```bash
# Démarrer
docker-compose up -d

# Arrêter
docker-compose down

# Redémarrer
docker-compose restart

# Rebuild et redémarrer
docker-compose up -d --build

# Voir les services
docker-compose ps

# Logs
docker-compose logs -f

# Exécuter une commande
docker-compose exec app python scripts/create_admin.py

# Entrer dans un conteneur
docker-compose exec app bash

# Supprimer tout (conteneurs + volumes)
docker-compose down -v
```

---

## 📝 Fichier .dockerignore

Créer `.dockerignore` pour exclure les fichiers inutiles :

```
# .dockerignore
.git
.github
.venv
__pycache__
*.pyc
*.pyo
*.pyd
.pytest_cache
.coverage
htmlcov
*.log
*.db
.env
.env.local
node_modules
documentation
tests
backups
*.md
```

**Résultat** : Image Docker plus légère et build plus rapide.

---

## 🌟 Avantages de Docker

### Pour le développement
- ✅ **Environnement identique** : "Works on my machine" résolu
- ✅ **Installation rapide** : Un seul `docker-compose up`
- ✅ **Isolation** : Pas de conflit avec d'autres projets
- ✅ **Reproductibilité** : Même environnement pour tous

### Pour la production
- ✅ **Déploiement simple** : `docker-compose up -d`
- ✅ **Scalabilité** : Ajouter des workers facilement
- ✅ **Rollback rapide** : Revenir à une version antérieure
- ✅ **Portabilité** : Fonctionne partout (AWS, Azure, on-premise)

---

## 🎓 Ressources

### Documentation Docker
- [Docker Docs](https://docs.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [Best Practices](https://docs.docker.com/develop/dev-best-practices/)

### Tutoriels
- [FastAPI with Docker](https://fastapi.tiangolo.com/deployment/docker/)
- [PostgreSQL in Docker](https://hub.docker.com/_/postgres)

---

## ✅ Checklist de Production

- [ ] `.env` configuré avec secrets sécurisés
- [ ] `DEBUG=False`
- [ ] PostgreSQL configuré (pas SQLite)
- [ ] Nginx configuré avec SSL
- [ ] Certificats SSL valides
- [ ] Sauvegardes automatiques configurées
- [ ] Monitoring en place
- [ ] Health checks fonctionnels
- [ ] Logs rotatifs configurés
- [ ] Firewall configuré
- [ ] Tests critiques passent
- [ ] Documentation à jour

---

**Votre application est prête pour Docker ! 🐳**

Prochaine étape : Voir [README.md](README.md) pour la documentation complète.

