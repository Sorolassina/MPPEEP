# 🏗️ Structure du Projet MPPEEP Dashboard

## 📁 Organisation Complète

```
mppeep/
├── app/                        ← Application principale
│   ├── main.py                 ← Point d'entrée FastAPI
│   ├── api/                    ← Routes API
│   │   └── v1/                 ← Version 1
│   │       ├── __init__.py     ← Expose api_router
│   │       ├── router.py       ← Agrège les endpoints
│   │       └── endpoints/      ← Routes par domaine
│   │           ├── auth.py     ← Authentification
│   │           ├── users.py    ← Utilisateurs CRUD
│   │           └── health.py   ← Health check
│   ├── core/                   ← Configuration & sécurité
│   │   ├── config.py           ← Settings (multi-env)
│   │   └── security.py         ← Hashing passwords
│   ├── db/                     ← Base de données
│   │   └── session.py          ← Connexion DB
│   ├── utils/                  ← Utilitaires & helpers
│   │   ├── email.py            ← Envoi d'emails
│   │   ├── validators.py       ← Validateurs (email, password, etc.)
│   │   ├── helpers.py          ← Fonctions helpers (slugify, random, etc.)
│   │   ├── constants.py        ← Constantes de l'application
│   │   └── decorators.py       ← Décorateurs personnalisés
│   ├── models/                 ← Modèles SQLModel (ORM)
│   │   ├── user.py             ← Modèle User
│   │   └── session.py          ← Modèle UserSession (multi-device)
│   ├── schemas/                ← Schémas Pydantic (validation)
│   │   └── user.py             ← Schémas User
│   ├── services/               ← Logique métier réutilisable
│   │   ├── user_service.py     ← Service utilisateurs
│   │   └── session_service.py  ← Service sessions
│   ├── templates/              ← Templates HTML (Jinja2)
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── login.html
│   │   └── recovery_password/
│   │       ├── forgot_password.html
│   │       ├── verify_code.html
│   │       └── reset_password.html
│   └── static/                 ← Fichiers statiques
│       ├── css/
│       └── js/
│
├── tests/                      ← Tests pytest organisés par type
│   ├── conftest.py             ← Fixtures partagées
│   ├── unit/                   ← Tests unitaires (fonctions isolées)
│   │   ├── test_config.py      ← Tests configuration
│   │   ├── test_security.py    ← Tests fonctions sécurité
│   │   └── test_models.py      ← Tests modèles de données
│   ├── integration/            ← Tests d'intégration (API)
│   │   ├── test_auth_api.py    ← Tests API authentification
│   │   ├── test_users_api.py   ← Tests API utilisateurs
│   │   └── test_health.py      ← Tests health check
│   ├── functional/             ← Tests fonctionnels (workflows)
│   │   └── test_password_recovery_workflow.py
│   ├── e2e/                    ← Tests end-to-end (futur)
│   └── README.md               ← Documentation tests
│
├── scripts/                    ← Scripts utilitaires Python
│   ├── create_user.py          ← Créer un user admin
│   ├── migrate_database.py     ← Migrer entre DB
│   ├── show_config.py          ← Afficher config
│   └── README.md               ← Documentation scripts
│
├── deploy/                     ← Déploiement Windows + Cloudflare
│   ├── README.md               ← Guide complet déploiement
│   ├── QUICKSTART.md           ← Guide rapide (10 min)
│   ├── config/
│   │   ├── deploy.json         ← Configuration centralisée
│   │   ├── environments.ps1    ← Gestion environnements
│   │   └── env.production.template
│   └── scripts/                ← Scripts PowerShell
│       ├── deploy.ps1          ← Déploiement complet
│       ├── update.ps1          ← Mise à jour rapide
│       ├── rollback.ps1        ← Restauration
│       ├── setup-service.ps1   ← Config service Windows
│       ├── init-server.ps1     ← Init serveur
│       ├── setup-firewall.ps1  ← Config pare-feu
│       ├── cloudflare-dns.ps1  ← Config DNS
│       ├── health-check.ps1    ← Health check
│       ├── monitor.ps1         ← Monitoring
│       └── logs.ps1            ← Consultation logs
│
├── .github/                    ← CI/CD avec GitHub Actions
│   ├── CICD_README.md          ← Documentation CI/CD complète
│   └── workflows/              ← Workflows automatisés
│       ├── ci.yml              ← Tests automatiques (CI)
│       ├── cd-staging.yml      ← Déploiement staging (CD)
│       ├── cd-production.yml   ← Déploiement production (CD)
│       ├── schedule.yml        ← Tâches planifiées
│       └── release.yml         ← Releases automatiques
│
├── pyproject.toml              ← Dépendances & config projet
├── pytest.ini                  ← Configuration pytest
├── env.example                 ← Template configuration
├── CICD_VS_DEPLOY.md           ← Comparaison CI/CD vs Scripts
└── README.md                   ← Documentation principale
```

---

## 🎯 Rôle de Chaque Dossier

### `app/` - Application

**Code principal de l'application.**

- `main.py` : Initialise FastAPI, monte les routes
- `api/` : Toutes les routes API organisées par version
- `core/` : Configuration, constantes, sécurité
- `db/` : Connexion et session base de données
- `models/` : Modèles de données (tables DB)
- `schemas/` : Schémas de validation (Pydantic)
- `templates/` : Templates HTML (Jinja2)
- `static/` : CSS, JS, images

---

### `tests/` - Tests

**Tests automatisés avec pytest.**

- Utilise une DB SQLite en mémoire
- Tests isolés (pas d'effet de bord)
- Fixtures réutilisables dans `conftest.py`

**Lancer les tests :**
```bash
pytest
pytest -v                    # Verbose
pytest --cov=app            # Avec couverture
pytest tests/test_auth.py   # Un fichier spécifique
```

---

### `scripts/` - Scripts Utilitaires

**Outils d'administration et maintenance.**

- Scripts à exécuter manuellement
- Modifications réelles de la DB
- Diagnostic et migration

**Exécuter depuis la racine :**
```bash
python scripts/create_test_user.py
python scripts/show_config.py
```

---

## 🔄 Flux de Données

### Requête HTTP

```
Client
  ↓
app/main.py (FastAPI app)
  ↓
app/api/v1/router.py (Agrégateur)
  ↓
app/api/v1/endpoints/*.py (Routes spécifiques)
  ↓
app/models/*.py (Modèles ORM)
  ↓
app/db/session.py (Session DB)
  ↓
Base de données (SQLite/PostgreSQL)
```

### Validation des Données

```
Client envoie JSON
  ↓
app/schemas/*.py (Validation Pydantic)
  ↓
app/api/v1/endpoints/*.py (Traitement)
  ↓
app/models/*.py (Sauvegarde en DB)
```

---

## 🗄️ Configuration Multi-Environnement

```python
# Développement (SQLite)
DEBUG=true → sqlite:///./app.db

# Production (PostgreSQL)
DEBUG=false → postgresql://...
```

**Fichiers :**
- `env.example` : Template
- `.env` : Configuration locale (gitignore)

**Voir la config actuelle :**
```bash
python scripts/show_config.py
```

---

## 📦 Dépendances

**Définies dans `pyproject.toml` :**

### Production
- `fastapi` : Framework web
- `uvicorn` : Serveur ASGI
- `sqlmodel` : ORM (SQLAlchemy + Pydantic)
- `pydantic[email]` : Validation
- `pydantic-settings` : Configuration
- `passlib[bcrypt]` : Hashing passwords
- `jinja2` : Templates HTML
- `python-multipart` : Upload fichiers

### Développement
- `pytest` : Tests
- `pytest-cov` : Couverture de code

**Installer tout :**
```bash
uv sync
```

---

## 🚀 Commandes Principales

### Développement

```bash
# Installer les dépendances
uv sync

# Créer un user admin
python scripts/create_test_user.py

# Lancer le serveur (dev)
uvicorn app.main:app --reload

# Voir la config
python scripts/show_config.py
```

### Tests

```bash
# Tous les tests
pytest

# Avec couverture
pytest --cov=app --cov-report=html

# Tests spécifiques
pytest tests/test_auth.py
pytest -k "login"
```

### Production

```bash
# Configurer l'environnement
export DEBUG=false
# ou créer .env avec DEBUG=false

# Migrer la DB (si besoin)
python scripts/migrate_database.py \
    "sqlite:///./app.db" \
    "postgresql://..."

# Lancer le serveur
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 🎨 Conventions de Code

### Nommage

- **Fichiers** : `snake_case.py`
- **Classes** : `PascalCase`
- **Fonctions/Variables** : `snake_case`
- **Constantes** : `UPPER_SNAKE_CASE`

### Organisation

- Un fichier par domaine fonctionnel
- Imports groupés : stdlib → third-party → local
- Docstrings pour fonctions publiques

### Exemple

```python
"""
Module pour gérer les utilisateurs
"""
from typing import List
from fastapi import APIRouter
from sqlmodel import Session

from app.models.user import User  # local import

router = APIRouter()

@router.get("/users/")
def get_users(session: Session) -> List[User]:
    """Récupère tous les utilisateurs"""
    return session.query(User).all()
```

---

## 📚 Documentation

- **README.md** : Vue d'ensemble du projet
- **PROJECT_STRUCTURE.md** : Ce fichier
- **tests/README.md** : Documentation tests
- **scripts/README.md** : Documentation scripts

---

## 🔐 Sécurité

- ✅ Mots de passe hashés (bcrypt)
- ✅ Validation des entrées (Pydantic)
- ✅ SECRET_KEY configurable
- ✅ Variables d'environnement
- ✅ Sessions multi-device (cookie-based)
- ✅ CORS configuration (13 middlewares)
- ✅ Security headers (CSP, HSTS, etc.)
- ⏳ TODO: JWT tokens (optionnel)
- ⏳ TODO: Rate limiting avancé

---

## 🔄 CI/CD et Déploiement

### Deux Systèmes Disponibles

#### 1. GitHub Actions (CI/CD Cloud)
```bash
# Tests automatiques à chaque push
git push
→ GitHub Actions lance les tests
→ Notification si ✅ ou ❌

# Déploiement staging (automatique)
git push origin develop
→ Tests + Déploiement staging

# Déploiement production (manuel)
GitHub Actions → Run workflow → Saisir "DEPLOY"
```

**Fichiers :** `.github/workflows/*.yml`

---

#### 2. Scripts PowerShell (Déploiement Windows)
```powershell
# Déploiement complet
.\deploy\scripts\deploy.ps1 -Environment production

# Mise à jour rapide
.\deploy\scripts\update.ps1

# Rollback
.\deploy\scripts\rollback.ps1

# Monitoring
.\deploy\scripts\monitor.ps1
```

**Fichiers :** `deploy/scripts/*.ps1`

---

### Approche Hybride (Recommandée)

```
1. Développement → git push
   ↓ (GitHub Actions - CI)
2. Tests automatiques ✅
   ↓ (Notification)
3. Déploiement manuel contrôlé
   ↓ (PowerShell - CD)
4. Service Windows + Monitoring ✅
```

**Documentation :**
- `.github/CICD_README.md` : CI/CD GitHub Actions
- `deploy/README.md` : Scripts PowerShell
- `CICD_VS_DEPLOY.md` : Comparaison des deux systèmes

---

## 🎯 Prochaines Étapes

1. ✅ **CI/CD** : GitHub Actions implémenté
2. ✅ **Déploiement** : Scripts PowerShell implémentés
3. **Sessions utilisateur** : JWT ou cookies
4. **Permissions** : Vérifier is_superuser
5. **API Keys** : Pour accès programmatique
6. **Docker** : Containerisation (optionnel)

