# 🐳 Configuration Docker - Guide Complet

## 🎯 Pourquoi Docker ?

Docker transforme votre application en **conteneur portable** qui fonctionne identiquement sur :
- ✅ Votre machine locale (Windows, Mac, Linux)
- ✅ Serveurs de production
- ✅ Cloud (AWS, Azure, Google Cloud)
- ✅ CI/CD (GitHub Actions, GitLab CI)

**Slogan :** "It works on my machine" → "It works everywhere" 🌍

---

## 📦 Ce Qui a Été Configuré

```
mppeep/
├── Dockerfile                  ← Image production optimisée
├── Dockerfile.dev              ← Image développement (hot-reload)
├── docker-compose.yml          ← Orchestration production
├── docker-compose.dev.yml      ← Orchestration développement
├── .dockerignore               ← Fichiers exclus
├── Makefile                    ← Commandes simplifiées
│
└── docker/
    ├── README.md               ← Guide complet Docker
    ├── QUICKSTART.md           ← Démarrage rapide (5 min)
    ├── DOCKER_COMMANDS.md      ← Aide-mémoire commandes
    ├── env.docker.example      ← Variables d'environnement
    └── scripts/
        ├── docker-build.sh     ← Script de build
        ├── docker-clean.sh     ← Script de nettoyage
        └── docker-backup.sh    ← Script de backup
```

---

## 🚀 Démarrage Rapide (2 Minutes)

### Méthode 1 : Avec Make (Recommandé)

```bash
cd mppeep

# 1. Copier les variables d'environnement
cp docker/env.docker.example .env

# 2. Démarrer
make dev-up

# 3. Voir les logs
make dev-logs

# 4. Accéder
open http://localhost:8000
```

---

### Méthode 2 : Avec docker-compose

```bash
cd mppeep

# 1. Variables d'environnement
cp docker/env.docker.example .env

# 2. Démarrer
docker-compose -f docker-compose.dev.yml up -d

# 3. Logs
docker-compose -f docker-compose.dev.yml logs -f
```

---

## 🏗️ Architecture Docker

### Services Inclus

```
┌─────────────────────────────────────┐
│        DOCKER COMPOSE               │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  APP (FastAPI)               │  │
│  │  Port: 8000                  │  │
│  │  • Auto-init DB              │  │
│  │  • Health checks             │  │
│  └──────────┬───────────────────┘  │
│             │ Connexion             │
│             ↓                       │
│  ┌──────────────────────────────┐  │
│  │  DB (PostgreSQL)             │  │
│  │  Port: 5432                  │  │
│  │  • Volumes persistants       │  │
│  │  • Health checks             │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  pgAdmin (Optionnel)         │  │
│  │  Port: 5050                  │  │
│  │  • Interface web DB          │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

---

## 📊 Images Docker

### Production (Dockerfile)

**Multi-stage build :**
```
Stage 1 (Builder):
- Python 3.11
- Installation dépendances
- Taille : ~1.2 GB (temporaire, supprimée)

Stage 2 (Production):
- Python 3.11-slim
- Copie venv depuis builder
- Utilisateur non-root
- Taille finale : ~350 MB ✅
```

**Optimisations :**
- ✅ Image 3.5x plus petite
- ✅ Sécurité (non-root)
- ✅ Seulement les dépendances de prod
- ✅ Health check intégré

---

### Développement (Dockerfile.dev)

```
- Python 3.11-slim
- Toutes les dépendances (prod + dev)
- Hot-reload activé
- Volumes montés (changements en temps réel)
- Taille : ~800 MB
```

**Caractéristiques :**
- ✅ Développement rapide
- ✅ Tests disponibles
- ✅ Linting tools
- ✅ Debugging facile

---

## 🎯 Cas d'Usage

### 1. Développement Local

```bash
# Démarrer
make dev-up

# Modifier le code
code app/api/v1/endpoints/users.py

# → Hot-reload automatique ✅
# → Changements visibles immédiatement

# Tester
make test

# Arrêter
make dev-down
```

---

### 2. Tests avec DB Réelle

```bash
# Démarrer seulement la DB
docker-compose up -d db

# Lancer les tests localement
uv run pytest -v

# Les tests utilisent la vraie DB PostgreSQL
```

---

### 3. Déploiement Production

```bash
# Sur le serveur
git clone [repo]
cd mppeep

# Configurer
cp docker/env.docker.example .env
nano .env  # Modifier SECRET_KEY, passwords, etc.

# Démarrer
make up

# ✅ Application en production !
```

---

### 4. CI/CD

```yaml
# .github/workflows/docker.yml
- name: Build Docker
  run: docker build -t mppeep:${{ github.sha }} .

- name: Test in Docker
  run: |
    docker-compose up -d
    docker-compose exec -T app uv run pytest
```

---

## 🔐 Sécurité

### Mesures Implémentées

✅ **Utilisateur non-root** (UID 1000)  
✅ **Multi-stage build** (dépendances build exclues)  
✅ **Secrets via .env** (jamais en dur)  
✅ **Health checks** (détection problèmes)  
✅ **Network isolation** (bridge privé)  
✅ **Image minimale** (moins de surface d'attaque)  

---

### Checklist Sécurité

```bash
# 1. Générer des secrets forts
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. Modifier .env
SECRET_KEY=secret-genere-ici
POSTGRES_PASSWORD=password-fort-ici
PGADMIN_PASSWORD=autre-password

# 3. Protéger .env
chmod 600 .env

# 4. Vérifier que .env est dans .gitignore
cat .gitignore | grep "\.env"

# 5. Scan de sécurité (optionnel)
docker scan mppeep:latest
```

---

## 📈 Avantages Docker

### vs Installation Traditionnelle

| Aspect | Sans Docker | Avec Docker |
|--------|-------------|-------------|
| **Setup** | 30 min | 2 min |
| **Dépendances** | Manuelles | Automatiques |
| **PostgreSQL** | Installer localement | Conteneur auto |
| **Isolation** | Pollution système | Isolé |
| **Reproductibilité** | "Works on my machine" | Fonctionne partout |
| **Déploiement** | Complexe | `docker-compose up` |

---

## 🎓 Commandes Avancées

### Scaling (Plusieurs Instances)

```bash
# Lancer 3 instances de l'app
docker-compose up -d --scale app=3

# Load balancer requis (nginx, traefik)
```

---

### Monitoring

```bash
# Stats en temps réel
docker stats

# Seulement l'app
docker stats mppeep-app

# Utilisation mémoire/CPU
docker-compose top
```

---

### Debugging

```bash
# Voir les variables d'environnement
docker-compose exec app env

# Voir les processus
docker-compose exec app ps aux

# Inspecter le conteneur
docker inspect mppeep-app

# Voir le réseau
docker network inspect mppeep-network
```

---

## ✅ Résumé

**Configuration Docker Complète Créée :**

```
✅ 2 Dockerfiles (prod + dev)
✅ 2 docker-compose.yml (prod + dev)
✅ .dockerignore
✅ Makefile (commandes simplifiées)
✅ 3 scripts bash utilitaires
✅ 4 fichiers de documentation
✅ Variables d'environnement template
```

**Total : 12 fichiers Docker**

---

## 🎯 Prochaines Étapes

1. **Tester** : `make dev-up`
2. **Développer** : Modifier le code avec hot-reload
3. **Déployer** : `make up` en production
4. **Monitorer** : `make logs`

---

**🐳 Votre boilerplate est maintenant Docker-ready ! Déployez partout en 1 commande ! 🚀**

