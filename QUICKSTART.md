# 🚀 Démarrage Rapide - MPPEEP Dashboard

Ce guide vous permet de démarrer le projet en **moins de 5 minutes** !

---

## 📋 Prérequis

Avant de commencer, assurez-vous d'avoir :

- ✅ **Python 3.10+** installé
- ✅ **pip** installé (gestionnaire de paquets Python)
- ✅ **Git** installé (optionnel, pour cloner le projet)
- ✅ **Make** installé (ou utilisez PowerShell directement)

---

## ⚡ Installation en 3 étapes

### 1️⃣ Installer `uv` (gestionnaire de dépendances rapide)

```bash
pip install uv
```

### 2️⃣ Configuration complète automatique

```bash
cd mppeep
make setup
```

Cette commande va :
- ✅ Installer toutes les dépendances Python
- ✅ Créer et initialiser la base de données SQLite
- ✅ Créer l'utilisateur admin par défaut

### 3️⃣ Lancer l'application

```bash
make start
```

L'application sera accessible sur : **http://localhost:9000**

---

## 🔐 Connexion par défaut

Après l'installation, vous pouvez vous connecter avec :

- **Email** : `admin@mppeep.com`
- **Mot de passe** : `admin123`

⚠️ **IMPORTANT** : Changez ce mot de passe dès la première connexion !

---

## 🎯 Commandes Essentielles

### Lancer l'application

```bash
make start          # Mode développement (hot-reload)
make start-prod     # Mode production
```

### Arrêter l'application

```bash
make stop           # Arrêter l'application
```

### Gestion de la base de données

```bash
make db-init        # Initialiser la DB
make db-reset       # Réinitialiser la DB (supprime les données)
make db-backup      # Sauvegarder la DB
```

### Tests

```bash
make test           # Tous les tests
make test-unit      # Tests unitaires uniquement
make test-cov       # Tests avec couverture de code
```

### Qualité du code

```bash
make lint           # Vérifier le code
make format         # Formater le code
make clean-code     # Nettoyage complet (format + lint + fix)
```

---

## 📚 Documentation Complète

Pour voir toutes les commandes disponibles :

```bash
make help
```

Pour un guide détaillé :

📖 **[MAKEFILE_GUIDE.md](./MAKEFILE_GUIDE.md)** - Guide complet des commandes Make

---

## 🆘 Problèmes Fréquents

### ❌ "uv: command not found"

**Solution :**
```bash
pip install uv
```

### ❌ "Port 9000 already in use"

**Solution :**
```bash
make stop           # Arrêter l'application existante
make start          # Relancer
```

Ou modifier le port dans `Makefile` (ligne `make start`) :
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### ❌ "Database is locked"

**Solution :**
```bash
make stop           # Arrêter l'application
rm app.db           # Supprimer la base (Windows: del app.db)
make db-init        # Réinitialiser
make start          # Relancer
```

### ❌ Tests échouent

**Solution :**
```bash
make clean          # Nettoyer les fichiers temporaires
make install        # Réinstaller les dépendances
make test           # Relancer les tests
```

---

## 🔧 Sans Make (Commandes PowerShell directes)

Si vous ne pouvez pas utiliser `make`, voici les commandes PowerShell équivalentes :

### Installation

```powershell
# Installer les dépendances
uv sync --extra dev

# Initialiser la base de données
uv run python scripts/init_db.py
```

### Lancer l'application

```powershell
# Mode développement
$env:DEBUG="True"; $env:ENV="dev"; uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 9000

# Mode production
$env:DEBUG="False"; $env:ENV="prod"; uv run uvicorn app.main:app --host 0.0.0.0 --port 9000 --workers 4
```

### Tests

```powershell
# Tous les tests
uv run pytest -v

# Tests avec couverture
uv run pytest --cov=app --cov-report=html --cov-report=term-missing
```

### Qualité du code

```powershell
# Formater
uv run ruff format app/ tests/

# Linter
uv run ruff check --fix app/ tests/
```

---

## 🐳 Docker (Optionnel)

Si vous préférez utiliser Docker :

```bash
# Mode développement
make dev-up

# Mode production
make up

# Arrêter
make dev-down
# ou
make down
```

---

## 📖 Structure du Projet

```
mppeep/
├── app/                    # Code source de l'application
│   ├── api/               # Endpoints API
│   ├── core/              # Configuration et utilitaires
│   ├── models/            # Modèles de données
│   ├── schemas/           # Schémas Pydantic
│   ├── services/          # Logique métier
│   ├── templates/         # Templates HTML
│   └── static/            # Fichiers statiques (CSS, JS, images)
├── scripts/               # Scripts utilitaires
├── tests/                 # Tests
├── logs/                  # Logs de l'application
├── uploads/               # Fichiers uploadés
├── app.db                 # Base de données SQLite (créée après db-init)
├── Makefile              # Commandes automatisées
├── pyproject.toml        # Configuration Python et dépendances
└── .env                  # Variables d'environnement (à créer)
```

---

## 🎓 Prochaines Étapes

Maintenant que votre application fonctionne :

1. **🔐 Changez le mot de passe admin**
   - Connectez-vous sur http://localhost:9000
   - Allez dans Profil > Changer le mot de passe

2. **📚 Explorez la documentation**
   - Consultez `MAKEFILE_GUIDE.md` pour toutes les commandes
   - Lisez `documentation/00_START_HERE.md` pour l'architecture

3. **🧪 Lancez les tests**
   ```bash
   make test
   ```

4. **🎨 Configurez votre IDE**
   - Configurez Ruff pour le linting
   - Activez le formatage automatique

5. **🚀 Développez !**
   - Le hot-reload est activé avec `make start`
   - Les changements de code sont automatiques

---

## 🆘 Besoin d'aide ?

- 📖 **Guide complet** : [MAKEFILE_GUIDE.md](./MAKEFILE_GUIDE.md)
- 🏗️ **Architecture** : `documentation/00_START_HERE.md`
- 🐛 **Bugs** : Créez une issue sur GitHub
- 💬 **Questions** : Contactez l'équipe de développement

---

**Bon développement ! 🚀**

