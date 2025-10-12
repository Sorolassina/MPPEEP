# 🐳 Docker - Guide Complet

## 🎯 Vue d'Ensemble

Ce projet inclut une **configuration Docker complète** pour déployer l'application avec :
- ✅ Image optimisée multi-stage
- ✅ PostgreSQL en conteneur
- ✅ pgAdmin pour gérer la base
- ✅ Hot-reload en développement
- ✅ Sécurité (utilisateur non-root)
- ✅ Health checks

---

## 📁 Fichiers Docker

```
mppeep/
├── Dockerfile               ← Image production (multi-stage)
├── Dockerfile.dev           ← Image développement (hot-reload)
├── docker-compose.yml       ← Orchestration production
├── docker-compose.dev.yml   ← Orchestration développement
├── .dockerignore            ← Fichiers exclus de l'image
├── .env.docker              ← Template variables d'environnement
└── docker/
    ├── README.md            ← Ce fichier
    └── scripts/             ← Scripts Docker utiles
```

---

## 🚀 Démarrage Rapide

### Développement (avec hot-reload)

```bash
# 1. Copier le fichier d'environnement
cp .env.docker .env

# 2. Démarrer les conteneurs
docker-compose -f docker-compose.dev.yml up -d

# 3. Voir les logs
docker-compose -f docker-compose.dev.yml logs -f app

# 4. Accéder à l'application
open http://localhost:8000
```

**✅ Hot-reload activé** : Les changements dans `app/` sont détectés automatiquement !

---

### Production

```bash
# 1. Configurer les variables
cp .env.docker .env
nano .env  # Modifier SECRET_KEY, POSTGRES_PASSWORD, etc.

# 2. Construire et démarrer
docker-compose up -d

# 3. Vérifier le statut
docker-compose ps

# 4. Voir les logs
docker-compose logs -f
```

---

## 📦 Services Disponibles

### Service : `app` (Application FastAPI)

```
Port : 8000
URL  : http://localhost:8000
Docs : http://localhost:8000/docs
```

**Commandes :**
```bash
# Logs
docker-compose logs -f app

# Shell interactif
docker-compose exec app bash

# Redémarrer
docker-compose restart app

# Reconstruire
docker-compose up -d --build app
```

---

### Service : `db` (PostgreSQL)

```
Port : 5432
User : postgres (ou POSTGRES_USER dans .env)
DB   : mppeep
```

**Commandes :**
```bash
# Connexion psql
docker-compose exec db psql -U postgres -d mppeep

# Voir les tables
docker-compose exec db psql -U postgres -d mppeep -c "\dt"

# Backup
docker-compose exec db pg_dump -U postgres mppeep > backup.sql

# Restore
docker-compose exec -T db psql -U postgres mppeep < backup.sql
```

---

### Service : `pgadmin` (Interface Web DB)

```
Port : 5050
URL  : http://localhost:5050
```

**⚠️ Démarrage :**
```bash
# pgAdmin est dans un "profile" optionnel
docker-compose --profile tools up -d pgadmin
```

**Connexion :**
1. Ouvrir http://localhost:5050
2. Login : `admin@mppeep.com / admin` (voir .env)
3. Ajouter serveur :
   - Host : `db`
   - Port : `5432`
   - User : `postgres`
   - Password : (votre POSTGRES_PASSWORD)

---

## 🔧 Commandes Docker

### Gestion des Conteneurs

```bash
# Démarrer tous les services
docker-compose up -d

# Démarrer en mode dev
docker-compose -f docker-compose.dev.yml up -d

# Arrêter
docker-compose down

# Arrêter et supprimer les volumes (⚠️ perte de données)
docker-compose down -v

# Redémarrer un service
docker-compose restart app

# Voir le statut
docker-compose ps

# Logs
docker-compose logs -f              # Tous les services
docker-compose logs -f app          # Seulement l'app
docker-compose logs -f db           # Seulement la DB
```

---

### Build et Images

```bash
# Construire les images
docker-compose build

# Forcer la reconstruction (sans cache)
docker-compose build --no-cache

# Reconstruire et démarrer
docker-compose up -d --build

# Voir les images
docker images | grep mppeep
```

---

### Exécution de Commandes

```bash
# Shell dans le conteneur app
docker-compose exec app bash

# Shell dans le conteneur db
docker-compose exec db bash

# Exécuter une commande Python
docker-compose exec app python scripts/create_user.py user@test.com "Test" "pass"

# Lancer les tests
docker-compose exec app uv run pytest -v

# Voir la config
docker-compose exec app python scripts/show_config.py
```

---

## 🗄️ Gestion de la Base de Données

### Backup

```bash
# Backup manuel
docker-compose exec db pg_dump -U postgres mppeep > backups/backup_$(date +%Y%m%d_%H%M%S).sql

# Backup avec docker-compose
docker-compose exec -T db pg_dump -U postgres mppeep | gzip > backups/backup.sql.gz
```

---

### Restore

```bash
# Depuis un fichier SQL
docker-compose exec -T db psql -U postgres mppeep < backups/backup.sql

# Depuis un fichier gzippé
gunzip < backups/backup.sql.gz | docker-compose exec -T db psql -U postgres mppeep
```

---

### Migration

```bash
# Accéder à psql
docker-compose exec db psql -U postgres mppeep

# Voir les tables
\dt

# Voir les données
SELECT * FROM user;

# Quitter
\q
```

---

## 🔒 Sécurité

### Bonnes Pratiques Implémentées

✅ **Utilisateur non-root** dans le conteneur  
✅ **Multi-stage build** (image finale légère)  
✅ **Secrets via .env** (pas en dur)  
✅ **Health checks** (auto-restart si erreur)  
✅ **Network isolation** (services isolés)  
✅ **Volumes séparés** (données persistantes)  

---

### Configuration Sécurisée

```bash
# 1. Générer un SECRET_KEY fort
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. Modifier .env
SECRET_KEY=votre-secret-key-genere
POSTGRES_PASSWORD=un-mot-de-passe-fort
PGADMIN_PASSWORD=autre-mot-de-passe

# 3. Limiter les permissions
chmod 600 .env
```

---

## 🎯 Environnements

### Développement

```bash
# Utiliser docker-compose.dev.yml
docker-compose -f docker-compose.dev.yml up -d

# Caractéristiques :
✅ Hot-reload activé
✅ Volumes montés (changements en temps réel)
✅ CORS_ALLOW_ALL=true
✅ DEBUG=true
✅ SQLite OU PostgreSQL (au choix)
```

---

### Production

```bash
# Utiliser docker-compose.yml
docker-compose up -d

# Caractéristiques :
✅ Image optimisée (multi-stage)
✅ Utilisateur non-root
✅ Health checks
✅ PostgreSQL requis
✅ DEBUG=false
✅ HTTPS redirect (si activé)
```

---

## 📊 Comparaison

| Aspect | Dev | Production |
|--------|-----|------------|
| **Dockerfile** | `Dockerfile.dev` | `Dockerfile` |
| **Compose** | `docker-compose.dev.yml` | `docker-compose.yml` |
| **Hot-reload** | ✅ Oui | ❌ Non |
| **Volumes** | Code monté | Copié dans image |
| **Taille image** | ~800 MB | ~350 MB |
| **Debug** | `true` | `false` |
| **CORS** | Tous | Limité |

---

## 🐛 Troubleshooting

### Les conteneurs ne démarrent pas

```bash
# Voir les logs d'erreur
docker-compose logs

# Vérifier la santé des services
docker-compose ps
```

---

### L'app ne se connecte pas à la DB

```bash
# Vérifier que la DB est prête
docker-compose exec db pg_isready -U postgres

# Vérifier la connexion depuis l'app
docker-compose exec app python -c "from app.db.session import engine; print(engine)"
```

---

### Port déjà utilisé

```bash
# Changer le port dans .env
APP_PORT=8001

# Ou arrêter le service qui utilise le port
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows
```

---

### Reconstruire complètement

```bash
# Tout arrêter et nettoyer
docker-compose down -v

# Supprimer les images
docker rmi mppeep-app mppeep-db

# Reconstruire
docker-compose up -d --build
```

---

## 📈 Optimisation

### Taille de l'Image

```
Multi-stage build :
- Stage 1 (builder) : ~1.2 GB (temporaire, supprimé)
- Stage 2 (prod)    : ~350 MB (finale) ✅

Single-stage :
- Image unique      : ~800 MB ❌
```

**Gain : 56% de réduction ! 🎉**

---

### Performance

```bash
# Utiliser BuildKit pour builds plus rapides
DOCKER_BUILDKIT=1 docker-compose build

# Avec cache
docker-compose build --parallel
```

---

## 🎓 Cas d'Usage

### 1. Développement Local

```bash
# Développement avec DB PostgreSQL
docker-compose -f docker-compose.dev.yml up -d

# Code source : modifiez app/ normalement
# → Hot-reload automatique ✅
```

---

### 2. Tests avec DB Réelle

```bash
# Démarrer seulement la DB
docker-compose up -d db

# Lancer les tests contre la vraie DB
pytest -v
```

---

### 3. Déploiement Production

```bash
# Sur le serveur
git clone [repo]
cd mppeep
cp .env.docker .env
# Modifier .env avec vos valeurs

docker-compose up -d

# ✅ Application en production avec PostgreSQL
```

---

### 4. CI/CD avec Docker

```yaml
# .github/workflows/docker.yml
- name: Build Docker image
  run: docker build -t mppeep:latest .

- name: Run tests in Docker
  run: docker-compose -f docker-compose.test.yml run app pytest
```

---

## 🎯 Workflows Recommandés

### Développement

```bash
# Terminal 1 : Docker
docker-compose -f docker-compose.dev.yml up

# Terminal 2 : Développer
code app/api/v1/endpoints/

# → Changements détectés automatiquement
# → Application redémarre
```

---

### Production

```bash
# Build l'image
docker-compose build

# Tester localement
docker-compose up

# Si OK → Push vers registry
docker tag mppeep:latest registry.company.com/mppeep:v1.0.0
docker push registry.company.com/mppeep:v1.0.0

# Sur le serveur
docker pull registry.company.com/mppeep:v1.0.0
docker-compose up -d
```

---

## ✅ Checklist Avant Production

- [ ] Changer `SECRET_KEY` dans `.env`
- [ ] Changer `POSTGRES_PASSWORD`
- [ ] Changer `PGADMIN_PASSWORD`
- [ ] Configurer `ALLOWED_HOSTS` avec votre domaine
- [ ] Mettre `DEBUG=false`
- [ ] Mettre `ENV=production`
- [ ] Activer `ENABLE_HTTPS_REDIRECT=true`
- [ ] Sauvegarder les volumes PostgreSQL
- [ ] Tester le health check
- [ ] Configurer les backups automatiques

---

## 🎉 Résumé

Docker vous permet de :

✅ **Déployer facilement** : `docker-compose up -d`  
✅ **Environnements isolés** : Dev et Prod séparés  
✅ **Reproductibilité** : Même config partout  
✅ **Scalabilité** : Prêt pour Kubernetes  
✅ **CI/CD** : Intégration facile  

**Votre boilerplate est maintenant Docker-ready ! 🐳**

