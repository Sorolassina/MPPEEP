# 🐳 Pipeline de Build Docker - MPPEEP Dashboard

## 📋 Vue d'ensemble

Le build Docker utilise une architecture **multi-stage** en 2 étapes pour optimiser la taille de l'image finale et la sécurité.

---

## 🎯 Dockerfile vs docker-compose : Rôles et Responsabilités

### 📦 **Dockerfile.prod** - La Recette de Construction

**Rôle** : Définit **COMMENT construire une IMAGE Docker**

| Responsabilité | Description | Exemple |
|---------------|-------------|---------|
| 🏗️ **Installer dépendances système** | Packages OS (apt-get) | `RUN apt-get install gcc libpq-dev` |
| 🐍 **Installer dépendances Python** | Packages pip | `RUN pip install -r requirements.txt` |
| 📁 **Copier le code** | Code source de l'app | `COPY . /app` |
| ⚙️ **Config environnement de base** | Variables figées | `ENV PYTHONUNBUFFERED=1` |
| 🚀 **Commande de démarrage** | CMD par défaut | `CMD ["uvicorn", "app.main:app"]` |
| 🔌 **Ports exposés** | Documentation | `EXPOSE 9000` |

**Analogie** : Une **recette de cuisine** qui dit comment préparer un plat

**Commande** : `docker build -f Dockerfile.prod -t mppeep:latest .`

**Résultat** : Une **IMAGE Docker** (mppeep:latest) - comme un plat préparé et congelé ❄️

---

### 🎼 **docker-compose.prod.yml** - L'Orchestrateur

**Rôle** : Définit **COMMENT exécuter et orchestrer plusieurs CONTAINERS ensemble**

| Responsabilité | Description | Exemple |
|---------------|-------------|---------|
| 🎭 **Services multiples** | Définir app, db, nginx, redis | `services: app: db: nginx:` |
| 🌐 **Réseau** | Communication inter-containers | `networks: mppeep-network` |
| 🔑 **Variables runtime** | Env vars dynamiques | `environment: - DATABASE_URL=...` |
| 💾 **Volumes** | Données persistantes | `volumes: postgres-data:` |
| 🔗 **Dépendances** | Ordre de démarrage | `depends_on: db:` |
| 🔌 **Ports exposés** | Mapping hôte ↔ container | `ports: "80:80"` |
| 🏥 **Healthchecks** | Surveillance santé | `healthcheck: test: [...]` |
| 🔄 **Restart policies** | Redémarrage auto | `restart: always` |

**Analogie** : Un **chef d'orchestre** qui coordonne plusieurs musiciens 🎻

**Commande** : `docker-compose -f docker-compose.prod.yml up -d`

**Résultat** : Un **environnement complet** avec 4 containers qui communiquent 🎪

---

## 🔄 Workflow Build → Run

```
┌────────────────────────────────────────────────────────────┐
│  PHASE 1 : BUILD (Dockerfile.prod)                        │
│  Commande : docker-compose build                          │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Dockerfile.prod        →        IMAGE                    │
│  ┌──────────────┐              ┌──────────────┐          │
│  │ FROM python  │              │ mppeep:      │          │
│  │ RUN apt-get  │   BUILD      │   latest     │          │
│  │ COPY code    │   ──────→    │              │          │
│  │ CMD uvicorn  │              │ 300 MB       │          │
│  └──────────────┘              └──────────────┘          │
│                                                            │
│  ✅ Image créée et stockée localement                     │
│  ❌ Aucun container ne tourne encore                      │
│  ❌ Variables d'env du .env PAS encore utilisées          │
└────────────────────────────────────────────────────────────┘
                        ⬇️
                   (Image prête)
                        ⬇️
┌────────────────────────────────────────────────────────────┐
│  PHASE 2 : RUN (docker-compose.prod.yml)                 │
│  Commande : docker-compose up -d                          │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  docker-compose.yml  +  .env   →   CONTAINERS             │
│  ┌──────────────┐   ┌──────┐    ┌──────────────┐        │
│  │ services:    │   │ DB   │    │  Container   │        │
│  │   db:        │   │ USER │    │   mppeep-db  │        │
│  │   app:       │ + │ PASS │ →  │   mppeep-app │        │
│  │   nginx:     │   │ URL  │    │   mppeep-nginx│       │
│  │   redis:     │   └──────┘    │   mppeep-redis│       │
│  └──────────────┘                └──────────────┘        │
│                                                            │
│  ✅ 4 containers tournent                                 │
│  ✅ Variables d'env injectées depuis .env                 │
│  ✅ Réseau mppeep-network créé                            │
│  ✅ Volumes persistants montés                            │
└────────────────────────────────────────────────────────────┘
```

---

## 🔑 Flux des Variables d'Environnement

### Problème Courant : "Pourquoi mon app ne voit pas mes variables ?"

```
┌─────────────────────────────────────────────────────────────┐
│  ÉTAPE 1 : Fichier .env sur la machine hôte               │
├─────────────────────────────────────────────────────────────┤
│  📄 .env                                                   │
│  ┌────────────────────────────────────────────┐          │
│  │ POSTGRES_USER=mppeepuser                   │          │
│  │ POSTGRES_PASSWORD=mppeep                   │          │
│  │ POSTGRES_DB=mppeep                         │          │
│  │ SECRET_KEY=mon-super-secret                │          │
│  │ DATABASE_URL=postgresql://...@db:5432/...  │ ← PAS    │
│  └────────────────────────────────────────────┘    de     │
│                                                   guillemets!│
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  ÉTAPE 2 : docker-compose.prod.yml LIT le .env            │
├─────────────────────────────────────────────────────────────┤
│  services:                                                 │
│    app:                                                    │
│      environment:                                          │
│        # Interpole les variables depuis .env ⬇️           │
│        - DATABASE_URL=postgresql://${POSTGRES_USER}:...   │
│                                   └─ "mppeepuser"          │
│        - SECRET_KEY=${SECRET_KEY}                          │
│                      └─ "mon-super-secret"                 │
│                                                            │
│  ⚠️  IMPORTANT : Les valeurs hardcodées dans              │
│      docker-compose ÉCRASENT celles du .env !             │
│                                                            │
│      - DEBUG=False        ← Toujours False (hardcodé)     │
│      - APP_NAME=MPPEEP... ← Toujours "MPPEEP..." (hardcodé)│
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  ÉTAPE 3 : Variables injectées dans le CONTAINER          │
├─────────────────────────────────────────────────────────────┤
│  Container mppeep-app :                                    │
│  ┌────────────────────────────────────────────┐          │
│  │ $ printenv                                 │          │
│  │ DATABASE_URL=postgresql://mppeepuser:...  │          │
│  │ SECRET_KEY=mon-super-secret               │          │
│  │ DEBUG=False                               │          │
│  │ APP_NAME=MPPEEP Dashboard                 │          │
│  └────────────────────────────────────────────┘          │
│                                                            │
│  ⚠️  Ces variables sont dans l'ENVIRONNEMENT du process   │
│      Docker, accessibles via os.environ ou Pydantic       │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  ÉTAPE 4 : Pydantic Settings LIT les variables d'env      │
├─────────────────────────────────────────────────────────────┤
│  app/core/config.py                                        │
│  ┌────────────────────────────────────────────┐          │
│  │ from pydantic_settings import BaseSettings │          │
│  │                                            │          │
│  │ class Settings(BaseSettings):              │          │
│  │     model_config = SettingsConfigDict(     │          │
│  │         env_file=".env",  ← Cherche aussi  │          │
│  │         case_sensitive=False               │          │
│  │     )                                      │          │
│  │                                            │          │
│  │     DATABASE_URL: str | None = None        │          │
│  │     SECRET_KEY: str = "changeme..."        │          │
│  │     DEBUG: bool = False                    │          │
│  └────────────────────────────────────────────┘          │
│                                                            │
│  🔍 Ordre de priorité Pydantic (du plus au moins) :       │
│     1. Variables d'environnement (os.environ) ← Docker    │
│     2. Fichier .env dans le container (si présent)        │
│     3. Valeurs par défaut dans la classe                  │
└───────────────────┬────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  ÉTAPE 5 : Application utilise settings                   │
├─────────────────────────────────────────────────────────────┤
│  from app.core.config import settings                     │
│                                                            │
│  # ✅ Valeurs finales :                                   │
│  settings.DATABASE_URL                                     │
│    → "postgresql://mppeepuser:mppeep@db:5432/mppeep"      │
│                                                            │
│  settings.SECRET_KEY                                       │
│    → "mon-super-secret"                                    │
│                                                            │
│  settings.DEBUG                                            │
│    → False                                                 │
└─────────────────────────────────────────────────────────────┘
```

### ⚠️ Erreurs Courantes

#### ❌ Guillemets dans le .env
```bash
# MAUVAIS (Pydantic lit littéralement les guillemets)
DATABASE_URL="postgresql://user:pass@db:5432/mppeep"

# CORRECT
DATABASE_URL=postgresql://user:pass@db:5432/mppeep
```

#### ❌ localhost au lieu de db
```bash
# MAUVAIS (localhost dans Docker = le container lui-même)
DATABASE_URL=postgresql://user:pass@localhost:5432/mppeep

# CORRECT (db = hostname DNS du service PostgreSQL)
DATABASE_URL=postgresql://user:pass@db:5432/mppeep
```

#### ❌ Oublier de rebuild après changement de code
```bash
# Si vous modifiez le code Python :
# ❌ Les changements ne seront PAS visibles sans rebuild
docker-compose up -d  

# ✅ Il faut rebuilder l'image
docker-compose build --no-cache
docker-compose up -d
```

---

## 🔀 Différences Clés : Dockerfile vs docker-compose

| Aspect | Dockerfile | docker-compose.yml |
|--------|-----------|-------------------|
| **But** | 🏗️ Construire UNE image | 🎼 Orchestrer PLUSIEURS containers |
| **Scope** | 1 seul service | 4 services (app, db, nginx, redis) |
| **Timing** | ⏰ BUILD TIME (une fois) | ⏰ RUN TIME (à chaque démarrage) |
| **Commande** | `docker build` | `docker-compose up` |
| **Variables d'env** | Figées dans l'image (ENV) | Injectées au runtime (environment:) |
| **Réseau** | ❌ Aucun | ✅ Network partagé entre services |
| **Communication** | ❌ Isolé | ✅ DNS: app ↔ db ↔ redis ↔ nginx |
| **Volumes** | Copie statique (COPY) | Montage dynamique (volumes:) |
| **Modificable** | ❌ Image immutable | ✅ Config modifiable sans rebuild |
| **Fichier créé** | Image Docker | Containers + Network + Volumes |

### 📊 Exemple Concret

**Dockerfile construit l'image** :
```dockerfile
FROM python:3.11-slim
RUN pip install fastapi uvicorn  # ← Figé dans l'image
COPY app/ /app/                  # ← Code figé dans l'image
ENV PYTHONUNBUFFERED=1           # ← Variable figée
CMD ["uvicorn", "app.main:app"]  # ← Commande figée
```
→ Résultat : Image `mppeep:latest` (300MB) stockée localement

**docker-compose lance les containers** :
```yaml
services:
  db:
    image: postgres:15-alpine      # ← Container 1
    environment:
      - POSTGRES_USER=mppeepuser   # ← Variable au runtime
    networks:
      - mppeep-network             # ← Réseau partagé
  
  app:
    image: mppeep:latest           # ← Utilise l'image buildée
    environment:
      - DATABASE_URL=postgresql://mppeepuser@db:5432/mppeep
                                   #                  ⬆️
                                   #             Hostname DNS
                                   #          (pas localhost!)
    depends_on:
      - db                         # ← Attend que db démarre
    networks:
      - mppeep-network             # ← Même réseau que db
```
→ Résultat : 4 containers tournent et communiquent

---

## 🌐 Réseau Docker : Pourquoi pas localhost ?

### ❌ Erreur : Connection à localhost refusée

```python
# Dans le container app :
DATABASE_URL = "postgresql://user:pass@localhost:5432/mppeep"
#                                       ⬆️
#                                  ERREUR !
```

**Problème** : `localhost` dans un container = **le container lui-même**, pas l'hôte !

```
┌─────────────────────┐
│  Container app      │
│  ┌─────────────┐   │
│  │ localhost   │   │ ← Pointe vers app lui-même
│  │ = 127.0.0.1 │   │
│  └─────────────┘   │
│                     │
│  PostgreSQL n'est   │
│  PAS ici ! ❌       │
└─────────────────────┘

┌─────────────────────┐
│  Container db       │  ← PostgreSQL est ICI
│  ┌─────────────┐   │
│  │ PostgreSQL  │   │
│  │ port 5432   │   │
│  └─────────────┘   │
└─────────────────────┘
```

### ✅ Solution : Utiliser le hostname DNS

```python
DATABASE_URL = "postgresql://user:pass@db:5432/mppeep"
#                                       ⬆️
#                                   Hostname DNS du service
```

Docker Compose crée automatiquement un **DNS interne** :
- Le service `db` est accessible via le hostname `db`
- Le service `app` est accessible via le hostname `app`
- Le service `redis` est accessible via le hostname `redis`

```
┌──────────────────────────────────────────────────┐
│  Réseau Docker: mppeep-network                  │
│  ┌─────────────┐     ┌─────────────┐           │
│  │ Container   │     │ Container   │           │
│  │    app      │────▶│     db      │           │
│  │             │     │             │           │
│  │ Peut joindre:    │ PostgreSQL  │           │
│  │ - db:5432   │     │ port 5432   │           │
│  │ - redis:6379│     └─────────────┘           │
│  │ - nginx:80  │                                │
│  └─────────────┘     ┌─────────────┐           │
│                      │ Container   │           │
│                      │   redis     │           │
│                      │             │           │
│                      │ Redis       │           │
│                      │ port 6379   │           │
│                      └─────────────┘           │
│                                                 │
│  DNS automatique :                              │
│  - db      → 172.18.0.2 (IP interne)           │
│  - app     → 172.18.0.3 (IP interne)           │
│  - redis   → 172.18.0.4 (IP interne)           │
└──────────────────────────────────────────────────┘
```

---

## 🏗️ Architecture du Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOCKERFILE.PROD                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  STAGE 1 : BUILDER                                              │
│  Image de base : python:3.11-slim                               │
├─────────────────────────────────────────────────────────────────┤
│  1. Installation des outils de compilation                      │
│     ├─ gcc                                                      │
│     ├─ libpq-dev (PostgreSQL headers)                          │
│     └─ build-essential                                          │
│                                                                 │
│  2. Création de l'environnement virtuel                         │
│     └─ /opt/venv                                                │
│                                                                 │
│  3. Installation des dépendances Python                         │
│     ├─ requirements.txt                                         │
│     └─ pip install --no-cache-dir                              │
│                                                                 │
│  📦 Résultat : /opt/venv avec toutes les dépendances           │
└─────────────────────────────────────────────────────────────────┘
                              ⬇️
                    (Copie de /opt/venv)
                              ⬇️
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 2 : RUNTIME (Image finale)                              │
│  Image de base : python:3.11-slim                               │
├─────────────────────────────────────────────────────────────────┤
│  1. Installation des dépendances runtime uniquement             │
│     ├─ libpq5 (PostgreSQL client)                              │
│     ├─ postgresql-client                                        │
│     └─ curl (pour healthcheck)                                 │
│                                                                 │
│  2. Création de l'utilisateur non-root                          │
│     └─ mppeep:mppeep (UID 1000)                                │
│                                                                 │
│  3. Copie depuis BUILDER                                        │
│     └─ /opt/venv → /opt/venv                                   │
│                                                                 │
│  4. Copie du code applicatif                                    │
│     └─ . → /app                                                │
│                                                                 │
│  5. Configuration finale                                        │
│     ├─ Création des dossiers (logs, data, uploads)            │
│     ├─ Permissions pour utilisateur mppeep                     │
│     └─ USER mppeep (switch to non-root)                       │
│                                                                 │
│  🚀 Résultat : Image production optimisée                      │
└─────────────────────────────────────────────────────────────────┘
                              ⬇️
                     EXPOSE PORT 9000
                              ⬇️
                     CMD: uvicorn avec 4 workers
```

---

## 📊 Détails des Stages

### Stage 1 : BUILDER (Construction)

**Objectif** : Compiler et installer toutes les dépendances Python

**Image de base** : `python:3.11-slim` (~150MB)

**Étapes** :
1. **Installation des outils de build**
   ```dockerfile
   RUN apt-get install -y gcc libpq-dev
   ```
   - `gcc` : Compilateur C pour les packages Python natifs
   - `libpq-dev` : Headers PostgreSQL pour `psycopg2`

2. **Création de l'environnement virtuel**
   ```dockerfile
   RUN python -m venv /opt/venv
   ENV PATH="/opt/venv/bin:$PATH"
   ```

3. **Installation des dépendances**
   ```dockerfile
   RUN pip install --no-cache-dir -r requirements.txt
   ```
   - `--no-cache-dir` : Ne pas stocker le cache pip (économie d'espace)

**Taille approximative** : ~500MB (avec outils de build)

---

### Stage 2 : RUNTIME (Production)

**Objectif** : Image légère et sécurisée pour l'exécution

**Image de base** : `python:3.11-slim` (~150MB)

**Étapes** :
1. **Dépendances runtime uniquement**
   ```dockerfile
   RUN apt-get install -y libpq5 postgresql-client curl
   ```
   - `libpq5` : Librairie PostgreSQL runtime (pas les headers)
   - `curl` : Pour le healthcheck

2. **Sécurité : Utilisateur non-root**
   ```dockerfile
   RUN groupadd -r mppeep && useradd -r -g mppeep -u 1000 mppeep
   ```

3. **Copie depuis le BUILDER**
   ```dockerfile
   COPY --from=builder /opt/venv /opt/venv
   ```
   ✅ On récupère uniquement les dépendances compilées, pas les outils de build

4. **Copie du code**
   ```dockerfile
   COPY --chown=mppeep:mppeep . .
   ```

5. **Configuration finale**
   - Création des dossiers nécessaires
   - Permissions correctes
   - Switch vers utilisateur `mppeep`

**Taille approximative** : ~300MB (image finale optimisée)

---

## 🔄 Flux de Données

```
┌─────────────────┐
│  requirements.  │
│      txt        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│   STAGE 1       │──────│   /opt/venv     │
│   (Builder)     │      │   + deps        │
└─────────────────┘      └────────┬────────┘
                                  │
                                  │ COPY --from=builder
                                  ▼
                         ┌─────────────────┐      ┌─────────────────┐
                         │   STAGE 2       │──────│  Image finale   │
                         │   (Runtime)     │      │  mppeep:latest  │
                         └────────┬────────┘      └─────────────────┘
                                  │
                                  │ + Code app
                                  ▼
                         ┌─────────────────┐
                         │  app/           │
                         │  ├─ main.py     │
                         │  ├─ core/       │
                         │  ├─ api/        │
                         │  └─ models/     │
                         └─────────────────┘
```

---

## ⚙️ Configuration de Démarrage

### Commande CMD

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000", "--workers", "4"]
```

**Paramètres** :
- `app.main:app` : Point d'entrée FastAPI
- `--host 0.0.0.0` : Écoute sur toutes les interfaces
- `--port 9000` : Port exposé
- `--workers 4` : 4 processus worker pour gérer les requêtes en parallèle

### Healthcheck

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:9000/api/v1/health || exit 1
```

**Paramètres** :
- `interval=30s` : Vérification toutes les 30 secondes
- `timeout=10s` : Timeout après 10 secondes
- `start-period=40s` : Délai avant le premier check (temps de démarrage)
- `retries=3` : 3 échecs consécutifs = container unhealthy

---

## 🚀 Commandes de Build

### Build manuel

```bash
# Build de l'image
docker build -f Dockerfile.prod -t mppeep:latest .

# Build sans cache (rebuild complet)
docker build --no-cache -f Dockerfile.prod -t mppeep:latest .
```

### Build via Docker Compose

```bash
# Build standard
docker-compose -f docker-compose.prod.yml build

# Build sans cache
docker-compose -f docker-compose.prod.yml build --no-cache

# Build et démarrage
docker-compose -f docker-compose.prod.yml up --build -d
```

### Build via Makefile

```bash
# Rebuild complet (production)
make docker-rebuild-prod

# Build seulement
make docker-build-prod
```

---

## 📦 Optimisations Appliquées

### 1. Multi-stage Build
✅ **Avantage** : Réduit la taille de l'image finale de ~500MB à ~300MB
- Les outils de build (gcc, headers) ne sont pas dans l'image finale
- Seules les dépendances runtime sont copiées

### 2. Layers Caching
✅ **Avantage** : Builds plus rapides lors des modifications
- `requirements.txt` copié avant le code
- Si `requirements.txt` ne change pas, la layer est réutilisée

### 3. No Cache Pip
```dockerfile
pip install --no-cache-dir
```
✅ **Avantage** : Économie de ~100MB d'espace disque

### 4. Nettoyage APT
```dockerfile
rm -rf /var/lib/apt/lists/*
```
✅ **Avantage** : Économie de ~50MB d'espace disque

### 5. Utilisateur Non-Root
```dockerfile
USER mppeep
```
✅ **Avantage** : Sécurité renforcée
- Le container ne s'exécute pas en root
- Limite les dégâts en cas de compromission

---

## 🔍 Analyse de l'Image

### Inspecter l'image

```bash
# Voir les layers
docker history mppeep:latest

# Taille de l'image
docker images mppeep:latest

# Inspection détaillée
docker inspect mppeep:latest
```

### Taille approximative des composants

```
Base image (python:3.11-slim)  : ~150 MB
Dépendances Python             : ~100 MB
Code applicatif                : ~10 MB
Librairies système (libpq5)    : ~40 MB
─────────────────────────────────────────
Total                          : ~300 MB
```

---

## 🛡️ Sécurité

### Bonnes pratiques appliquées

✅ **Multi-stage build** : Pas d'outils de build dans l'image finale  
✅ **Utilisateur non-root** : Exécution avec UID 1000  
✅ **Versions fixes** : `python:3.11-slim` (pas de `latest`)  
✅ **Healthcheck** : Surveillance de l'état du container  
✅ **Minimal dependencies** : Seulement ce qui est nécessaire  
✅ **No secrets** : Pas de credentials hardcodés (via env vars)  

---

## 🔧 Variables d'Environnement

### Définies dans le Dockerfile

```dockerfile
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/opt/venv/bin:$PATH"
```

### Passées via docker-compose.prod.yml

```yaml
environment:
  - DATABASE_URL=postgresql://...
  - SECRET_KEY=${SECRET_KEY:?SECRET_KEY requis}
  - DEBUG=False
  - APP_NAME=MPPEEP Dashboard
  - APP_VERSION=1.0.0
  - ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

---

## 📝 Logs et Monitoring

### Structure des logs

```
/app/logs/
  ├── app.log          # Logs applicatifs
  ├── access.log       # Logs d'accès HTTP
  └── error.log        # Logs d'erreurs
```

### Voir les logs

```bash
# Logs du container
docker logs mppeep-app

# Logs en temps réel
docker logs -f mppeep-app

# Via docker-compose
docker-compose -f docker-compose.prod.yml logs -f app

# Via Makefile
make docker-logs-prod
```

---

## 🆘 Troubleshooting

### ❌ Connection refused: localhost:5432

**Symptôme** :
```
ERROR | ❌ Impossible de se connecter au serveur PostgreSQL
connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused
```

**Diagnostic** :
```bash
# 1. Vérifier que DATABASE_URL est bien injectée dans le container
docker exec mppeep-app printenv | grep DATABASE

# ✅ DOIT afficher : DATABASE_URL=postgresql://...@db:5432/...
#                                                    ⬆️ PAS localhost !
```

**Causes possibles** :

#### 🔴 Cause 1 : L'image contient l'ancien code
L'image Docker a été buildée AVANT la correction du code. Le container tourne avec l'ancienne version.

**Solution** :
```bash
# Rebuilder l'image avec le nouveau code
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# OU via Makefile
make docker-rebuild-prod
```

#### 🔴 Cause 2 : SyntaxError dans config.py
Le code Python crashe AVANT de pouvoir lire `DATABASE_URL`, donc il utilise les valeurs par défaut.

**Vérification** :
```bash
# Voir les logs de l'app
docker logs mppeep-app 2>&1 | grep -i "syntax\|error"

# Si vous voyez "SyntaxError: invalid syntax"
# → Corrigez le code et rebuilder !
```

**Code incorrect** :
```python
# ❌ MAUVAIS (SyntaxError en Python)
POSTGRES_HOST: str = if self.DEBUG: "localhost" else "db"
```

**Code correct** :
```python
# ✅ CORRECT (opérateur ternaire Python)
POSTGRES_HOST: str = "localhost" if self.DEBUG else "db"

# OU mieux : utiliser DATABASE_URL (prioritaire)
DATABASE_URL: str | None = None  # Lu depuis docker-compose
```

#### 🔴 Cause 3 : Guillemets dans .env
Le fichier `.env` contient des guillemets qui corrompent la valeur.

**Vérification** :
```bash
cat .env | grep DATABASE_URL
```

**Incorrect** :
```bash
# ❌ MAUVAIS
DATABASE_URL="postgresql://user:pass@db:5432/mppeep"
              ⬆️ guillemets                                ⬆️
```

**Correct** :
```bash
# ✅ CORRECT (pas de guillemets)
DATABASE_URL=postgresql://user:pass@db:5432/mppeep
```

#### 🔴 Cause 4 : Mauvais hostname dans DATABASE_URL
L'URL pointe vers `localhost` au lieu du service Docker `db`.

**Vérification** :
```bash
# Dans docker-compose.prod.yml, ligne 44 :
- DATABASE_URL=postgresql://...@db:5432/...
                              ⬆️
                         DOIT être "db" !
```

**Rappel** : Dans Docker, les containers communiquent via **DNS** :
- ✅ `db` = hostname du service PostgreSQL
- ❌ `localhost` = le container app lui-même

---

### Build échoue

**Problème** : Erreur lors de l'installation des dépendances
```bash
# Solution : Build sans cache
docker-compose -f docker-compose.prod.yml build --no-cache
```

### Container ne démarre pas

**Problème** : Healthcheck fail
```bash
# Vérifier les logs
docker logs mppeep-app

# Vérifier la BDD
docker exec mppeep-db pg_isready
```

### Permission denied

**Problème** : Erreur d'écriture dans /app/logs
```bash
# Vérifier les permissions
docker exec mppeep-app ls -la /app/logs

# Recréer avec bonnes permissions
docker-compose down
docker-compose up --build -d
```

---

## 📋 Résumé Rapide - Aide-Mémoire

### 🎯 Les 3 Concepts Clés

| Concept | Rôle | Fichier | Timing |
|---------|------|---------|--------|
| **🏗️ Image** | Template figé de l'app | Dockerfile.prod | BUILD TIME |
| **📦 Container** | Instance en cours d'exécution | docker-compose.prod.yml | RUN TIME |
| **🌐 Réseau** | Communication entre containers | docker-compose.prod.yml | RUN TIME |

### ⚡ Commandes Essentielles

```bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BUILD : Créer/Recréer l'image
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
docker-compose -f docker-compose.prod.yml build           # Build standard
docker-compose -f docker-compose.prod.yml build --no-cache # Build from scratch
make docker-build-prod                                     # Via Makefile

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RUN : Démarrer/Arrêter les containers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
docker-compose -f docker-compose.prod.yml up -d           # Démarrer (détaché)
docker-compose -f docker-compose.prod.yml down            # Arrêter
docker-compose -f docker-compose.prod.yml restart         # Redémarrer
make docker-start-prod                                     # Via Makefile
make docker-stop-prod                                      # Via Makefile

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REBUILD COMPLET : Tout refaire
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
make docker-rebuild-prod                                   # Stop + Build + Start

# Équivalent manuel :
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DEBUG : Voir ce qui se passe
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
docker logs mppeep-app                                     # Logs de l'app
docker logs -f mppeep-app                                  # Logs en temps réel
docker exec mppeep-app printenv                            # Variables d'env
docker exec -it mppeep-app /bin/bash                       # Shell dans le container
docker-compose -f docker-compose.prod.yml ps               # Statut des containers
make docker-logs-prod                                      # Via Makefile
```

### 🔑 Points Clés à Retenir

✅ **Dockerfile = Recette** → Construit une image  
✅ **docker-compose = Chef** → Lance plusieurs containers  
✅ **Variables d'env** : docker-compose > Pydantic > défauts  
✅ **Réseau Docker** : Utiliser `db`, pas `localhost`  
✅ **Modification code** : Toujours rebuilder l'image  
✅ **Modification .env** : Juste restart (pas de rebuild)  

### 🚫 Pièges à Éviter

❌ **Ne PAS** mettre de guillemets dans le `.env`  
❌ **Ne PAS** utiliser `localhost` dans `DATABASE_URL` (utiliser `db`)  
❌ **Ne PAS** oublier de rebuild après changement de code Python  
❌ **Ne PAS** commiter le fichier `.env` (contient des secrets)  
❌ **Ne PAS** utiliser `docker run` directement (utiliser `docker-compose`)  

---

## 📚 Fichiers Liés

- `Dockerfile.prod` : Définition de l'image production
- `docker-compose.prod.yml` : Orchestration des services
- `requirements.txt` : Dépendances Python
- `Makefile` : Commandes simplifiées
- `.dockerignore` : Fichiers exclus du build

---

## 🎯 Prochaines Améliorations

- [ ] Mise en place de scan de vulnérabilités (`docker scan`)
- [ ] Optimisation des layers avec `dive` tool
- [ ] CI/CD pour build automatique
- [ ] Registry privé pour les images
- [ ] Signatures d'images pour la sécurité

---

**Documentation créée le** : 2025-10-20  
**Version** : 1.0.0  
**Maintenu par** : MPPEEP Team

