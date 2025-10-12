# 🚀 MPPEEP Dashboard - FastAPI Boilerplate

[![CI Tests](https://img.shields.io/badge/tests-passing-green)](https://github.com/votre-user/mppeep/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.118+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> **Boilerplate FastAPI Production-Ready** avec authentification complète, tests automatisés, CI/CD, et scripts de déploiement Windows.

---

## 🎯 Pourquoi ce Boilerplate ?

Ce projet est un **template standardisé** pour démarrer rapidement vos projets FastAPI avec :

- ✅ **Gain de temps** : 5 minutes pour démarrer au lieu de plusieurs jours
- ✅ **Bonnes pratiques** : Architecture éprouvée et scalable
- ✅ **Production-ready** : Sécurité, tests, déploiement inclus
- ✅ **Documentation** : Guides pour dev ET non-tech
- ✅ **Deux systèmes CI/CD** : GitHub Actions ET scripts PowerShell

---

## ⚡ Quick Start (5 Minutes)

```bash
# 1. Cloner le projet
git clone [votre-repo] mon-projet
cd mon-projet/mppeep

# 2. Installer les dépendances
pip install uv
uv sync

# 3. Créer un utilisateur admin
python scripts/create_test_user.py

# 4. Lancer le serveur
uvicorn app.main:app --reload

# 5. Ouvrir dans le navigateur
open http://localhost:8000
```

**✨ Voilà ! Votre API est prête !**

---

## 🔥 Fonctionnalités Principales

### 🚀 API REST Complète

```
✅ Versioning (v1, v2, ...)
✅ Documentation auto (Swagger + ReDoc)
✅ Validation automatique (Pydantic)
✅ Gestion d'erreurs centralisée
✅ Health check endpoint
```

**Endpoints disponibles :**
- `GET /api/v1/ping` - Vérification santé
- `POST /api/v1/login` - Authentification
- `POST /api/v1/forgot-password` - Récupération mot de passe
- `GET /api/v1/users` - Liste utilisateurs
- `POST /api/v1/users` - Créer utilisateur

**Documentation interactive :**
- Swagger UI : http://localhost:8000/docs
- ReDoc : http://localhost:8000/redoc

---

### 📝 Système de Logging Professionnel

```
✅ Logs fichiers séparés (app.log, error.log, access.log)
✅ Rotation automatique (10 MB max)
✅ Console colorée (stdout/stderr)
✅ Format Apache-like pour HTTP
✅ Stack traces complètes
✅ Request ID tracking
```

**Fichiers de logs :**
- `logs/app.log` - Tous les logs de l'application
- `logs/error.log` - Seulement les erreurs (avec stack traces)
- `logs/access.log` - Requêtes HTTP (format Apache)

**Voir la documentation :** [`LOGGING_QUICKSTART.md`](./LOGGING_QUICKSTART.md)

---

### 🔐 Authentification Complète

```
✅ Login email/password
✅ Hashing sécurisé (bcrypt)
✅ Sessions multi-device
✅ Gestion des sessions actives
✅ Récupération mot de passe (3 étapes)
✅ Comptes actifs/désactivés
✅ Rôles (user / superuser)
```

**Système de sessions :**
- Plusieurs connexions simultanées (bureau, mobile, etc.)
- Tracking device info (navigateur, OS)
- Expiration configurable (7 ou 30 jours)
- Déconnexion sélective ou globale

**Workflow de récupération :**
1. Demande de code (`/forgot-password`)
2. Vérification du code (`/verify-code`)
3. Réinitialisation (`/reset-password`)

---

### 🗄️ Base de Données Flexible

```
✅ SQLite (développement)
✅ PostgreSQL (production)
✅ Migration automatique
✅ Multi-environnements
```

**Changement automatique :**
```bash
# Développement
DEBUG=true → SQLite automatique

# Production
DEBUG=false → PostgreSQL automatique
```

**Migration entre bases :**
```bash
python scripts/migrate_database.py \
    "sqlite:///./app.db" \
    "postgresql://user:pass@host:5432/db"
```

---

### 🧪 Tests Automatisés

```
✅ Tests unitaires
✅ Tests d'intégration
✅ Tests fonctionnels
✅ Couverture de code
✅ DB en mémoire
```

**Commandes :**
```bash
pytest                     # Tous les tests
pytest -v                  # Mode verbose
pytest --cov=app          # Avec couverture
pytest tests/unit/        # Seulement unitaires
pytest -m auth            # Marker "auth"
```

**Organisation :**
```
tests/
├── unit/           ← Fonctions isolées
├── integration/    ← API endpoints
├── functional/     ← Workflows complets
└── e2e/            ← Interface utilisateur
```

---

### 🔄 CI/CD Complet

#### Option 1 : GitHub Actions (Automatique)

```
✅ Tests auto à chaque push
✅ Linting automatique
✅ Scan sécurité
✅ Déploiement staging auto
✅ Déploiement production manuel
✅ Releases automatiques
```

**Workflows :**
- `ci.yml` - Tests automatiques
- `cd-staging.yml` - Déploiement staging
- `cd-production.yml` - Déploiement production
- `schedule.yml` - Tâches quotidiennes
- `release.yml` - Releases auto

**Setup :** Voir [`.github/SETUP_GITHUB_ACTIONS.md`](.github/SETUP_GITHUB_ACTIONS.md)

---

#### Option 2 : Scripts PowerShell (Windows)

```
✅ Déploiement complet (1 commande)
✅ Service Windows (NSSM)
✅ Cloudflare DNS
✅ Backup/Rollback automatiques
✅ Monitoring temps réel
```

**Scripts disponibles :**
```powershell
.\deploy\scripts\deploy.ps1          # Déploiement complet
.\deploy\scripts\update.ps1          # Mise à jour
.\deploy\scripts\rollback.ps1        # Restauration
.\deploy\scripts\monitor.ps1         # Monitoring
.\deploy\scripts\health-check.ps1    # Santé app
```

**Setup :** Voir [`deploy/README.md`](deploy/README.md)

---

#### Option 3 : Hybride (Recommandé ⭐)

```
GitHub Actions (CI) → Tests automatiques ✅
        ↓
    Notification
        ↓
PowerShell (CD) → Déploiement contrôlé ✅
```

**Workflow :**
1. `git push` → Tests auto (GitHub)
2. Si ✅ → Notification
3. `.\deploy.ps1` → Déploiement (PowerShell)

---

## 📁 Structure du Projet

```
mppeep/
├── app/                      ← Application principale
│   ├── main.py              ← Point d'entrée FastAPI
│   ├── api/v1/              ← Routes API (versioning)
│   ├── core/                ← Configuration & middlewares
│   │   ├── logging_config.py ← Configuration logs
│   │   └── middleware.py    ← 13 middlewares
│   ├── db/                  ← Base de données
│   ├── models/              ← Modèles SQLModel
│   │   ├── user.py          ← Modèle User
│   │   └── session.py       ← Modèle UserSession (multi-device)
│   ├── schemas/             ← Schémas Pydantic
│   ├── services/            ← Logique métier
│   │   ├── user_service.py  ← Service utilisateurs
│   │   └── session_service.py ← Service sessions
│   ├── utils/               ← Utilitaires
│   ├── templates/           ← Templates HTML (Jinja2)
│   └── static/              ← CSS, JS, images
│
├── logs/                    ← Fichiers de logs
│   ├── app.log              ← Tous les logs
│   ├── error.log            ← Erreurs seulement
│   └── access.log           ← Requêtes HTTP
│
├── tests/                   ← Tests pytest
│   ├── unit/                ← Tests unitaires
│   ├── integration/         ← Tests API
│   └── functional/          ← Tests workflows
│
├── scripts/                 ← Scripts utilitaires
│   ├── create_user.py       ← Créer des utilisateurs
│   └── init_db.py           ← Initialiser la DB
│
├── deploy/                  ← Déploiement Windows
│   ├── config/              ← Configuration
│   └── scripts/             ← Scripts PowerShell
│
├── docker/                  ← Configuration Docker
│   ├── scripts/             ← Scripts Docker
│   └── README.md            ← Guide Docker
│
├── .github/                 ← CI/CD GitHub Actions
│   └── workflows/           ← Workflows
│
├── pyproject.toml           ← Dépendances
├── pytest.ini               ← Config pytest
├── env.example              ← Template configuration
└── README.md                ← Ce fichier
```

**Documentation complète :** [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md)

---

## 🛠️ Stack Technologique

### Backend
- **FastAPI** - Framework web moderne
- **SQLModel** - ORM (SQLAlchemy + Pydantic)
- **Uvicorn** - Serveur ASGI
- **Passlib** - Hashing passwords
- **Pydantic** - Validation données

### Frontend
- **Jinja2** - Templates HTML
- **HTML5 + CSS3** - Interface
- **JavaScript** - Interactions

### Base de Données
- **SQLite** - Développement
- **PostgreSQL** - Production

### Tests
- **Pytest** - Framework de tests
- **pytest-cov** - Couverture de code

### CI/CD
- **GitHub Actions** - Automatisation cloud
- **PowerShell** - Déploiement Windows

---

## 📚 Documentation

| Fichier | Description |
|---------|-------------|
| [`README.md`](README.md) | Ce fichier |
| [`QUICK_START.md`](QUICK_START.md) | Démarrage rapide (2 min) |
| [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) | Architecture complète |
| [`SESSIONS_SYSTEM.md`](SESSIONS_SYSTEM.md) | Système de sessions multi-device |
| [`LOGGING_QUICKSTART.md`](LOGGING_QUICKSTART.md) | Guide du système de logging |
| [`FEATURES.md`](FEATURES.md) | Liste des fonctionnalités |
| [`CICD_VS_DEPLOY.md`](CICD_VS_DEPLOY.md) | Comparaison CI/CD |
| [`.github/CICD_README.md`](.github/CICD_README.md) | Guide GitHub Actions |
| [`.github/SETUP_GITHUB_ACTIONS.md`](.github/SETUP_GITHUB_ACTIONS.md) | Setup GitHub Actions |
| [`deploy/README.md`](deploy/README.md) | Guide déploiement |
| [`deploy/QUICKSTART.md`](deploy/QUICKSTART.md) | Quick start (10 min) |
| [`tests/README.md`](tests/README.md) | Guide des tests |

**+ 15 fichiers README** dans chaque dossier pour documentation contextuelle.

---

## 🔧 Configuration

### Variables d'Environnement

```bash
# 1. Copier le template
cp env.example .env

# 2. Modifier les valeurs
nano .env

# 3. Variables principales
APP_NAME=MPPEEP Dashboard
ENV=dev
DEBUG=true
SECRET_KEY=changeme-in-production

# Database auto selon DEBUG
SQLITE_DB_PATH=./app.db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
# ...
```

**Fichiers de config :**
- `env.example` - Template
- `.env` - Local (gitignore)
- `deploy/config/deploy.json` - Déploiement

---

### Middlewares Configurables

```bash
# 13 middlewares activables/désactivables
ENABLE_CORS=true
ENABLE_GZIP=true
ENABLE_SECURITY_HEADERS=true
ENABLE_LOGGING=true
ENABLE_REQUEST_ID=true
ENABLE_CACHE_CONTROL=true
ENABLE_CSP=true
ENABLE_ERROR_HANDLING=true
ENABLE_HTTPS_REDIRECT=false
ENABLE_IP_FILTER=false
ENABLE_USER_AGENT_FILTER=false
ENABLE_REQUEST_SIZE_LIMIT=true
```

---

## 🚀 Déploiement

### Développement

```bash
# Lancer en mode dev (hot-reload)
uvicorn app.main:app --reload

# Avec logs verbeux
uvicorn app.main:app --reload --log-level debug
```

---

### Production (Linux/Cloud)

```bash
# 1. Configurer environnement
export DEBUG=false
export DATABASE_URL=postgresql://...

# 2. Lancer le serveur
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Ou avec Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

---

### Production (Windows Server)

```powershell
# Méthode 1 : GitHub Actions
# Voir .github/SETUP_GITHUB_ACTIONS.md

# Méthode 2 : Scripts PowerShell
.\deploy\scripts\deploy.ps1 -Environment production

# Méthode 3 : Hybride
# Tests sur GitHub + Déploiement PowerShell
```

**Guide complet :** [`deploy/README.md`](deploy/README.md)

---

## 🧪 Tests

```bash
# Tous les tests
pytest

# Tests spécifiques
pytest tests/unit/                # Unitaires
pytest tests/integration/         # Intégration
pytest tests/functional/          # Fonctionnels

# Avec couverture
pytest --cov=app --cov-report=html

# Avec markers
pytest -m auth                    # Tests auth
pytest -m database                # Tests DB
pytest -m slow                    # Tests lents

# Mode verbose
pytest -v

# S'arrêter au premier échec
pytest -x
```

**Documentation :** [`tests/README.md`](tests/README.md)

---

## 📦 Scripts Utilitaires

```bash
# Créer un utilisateur admin
python scripts/create_test_user.py

# Afficher la configuration actuelle
python scripts/show_config.py

# Migrer entre bases de données
python scripts/migrate_database.py \
    "sqlite:///./app.db" \
    "postgresql://user:pass@host:5432/db"
```

---

## 🔒 Sécurité

### Mesures Implémentées

```
✅ Password hashing (bcrypt)
✅ HTTPS redirect (production)
✅ CORS configuré
✅ Security headers
✅ CSP (Content Security Policy)
✅ Request size limit
✅ IP filtering (optionnel)
✅ User agent filtering (optionnel)
✅ Error handling sécurisé
✅ Trusted hosts
✅ Secrets en variables d'environnement
```

### Bonnes Pratiques

- ⚠️ **Changer** `SECRET_KEY` en production
- ⚠️ **Ne jamais** commiter `.env`
- ⚠️ **Utiliser** HTTPS en production
- ⚠️ **Limiter** les allowed hosts
- ⚠️ **Activer** tous les middlewares en prod

---

## 🎓 Pour Qui ?

### ✅ Développeurs Python/FastAPI
Démarrer rapidement avec une structure standardisée

### ✅ Startups et PME
Solution production-ready avec documentation complète

### ✅ Équipes
CI/CD automatisé pour collaboration efficace

### ✅ Solo Developers
Gain de temps avec scripts de déploiement

---

## 🎯 Cas d'Usage

### Nouveau Projet

```bash
# 1. Cloner
git clone [repo] mon-projet

# 2. Renommer
# Remplacer "MPPEEP" par votre nom de projet

# 3. Personnaliser
# Modifier app/models/, app/schemas/, etc.

# 4. Déployer
# Utiliser GitHub Actions ou PowerShell
```

---

### Projet Existant

```bash
# Copier les parties utiles :
# - Structure de dossiers
# - Configuration multi-env
# - Tests
# - CI/CD
# - Scripts de déploiement
```

---

## 📊 Statistiques

```
✅ 80+ fichiers
✅ 5000+ lignes de code
✅ 2000+ lignes de documentation
✅ 15+ fichiers README
✅ 25+ tests
✅ 13 middlewares
✅ 5 workflows CI/CD
✅ 10 scripts PowerShell
```

---

## 🤝 Contribution

1. Fork le projet
2. Créer une branche (`git checkout -b feat/nouvelle`)
3. Commit (`git commit -m 'feat: nouvelle fonctionnalité'`)
4. Push (`git push origin feat/nouvelle`)
5. Créer une Pull Request

---

## 📄 License

MIT License - Voir [LICENSE](LICENSE)

---

## 🙏 Remerciements

- [FastAPI](https://fastapi.tiangolo.com/) - Framework web
- [SQLModel](https://sqlmodel.tiangolo.com/) - ORM
- [Pytest](https://pytest.org/) - Tests
- [GitHub Actions](https://github.com/features/actions) - CI/CD

---

## 📞 Support

- 📧 Email : support@mppeep.com
- 📚 Documentation : Voir les README dans chaque dossier
- 🐛 Issues : [GitHub Issues](https://github.com/votre-user/mppeep/issues)

---

## 🎯 Roadmap

- [x] API REST complète
- [x] Authentification
- [x] Tests automatisés
- [x] CI/CD GitHub Actions
- [x] Scripts PowerShell
- [x] Documentation complète
- [x] Sessions utilisateur (multi-device)
- [x] Système de logging complet
- [ ] API Keys
- [ ] Docker (en cours)
- [ ] Webhooks
- [ ] Rate limiting avancé

---

**🚀 Prêt pour la Production !**

Utilisez ce boilerplate pour tous vos projets FastAPI et gagnez des heures de développement à chaque fois !

**Bon développement ! 🎉**

