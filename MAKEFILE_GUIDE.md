# 🚀 Guide des Commandes Make - MPPEEP Dashboard

Ce guide vous explique comment utiliser le Makefile pour automatiser les tâches courantes du projet.

## 📋 Afficher l'aide

```bash
make help
```

Cette commande affiche toutes les commandes disponibles avec leurs descriptions.

---

## ⚡ Démarrage Rapide

### 🎯 Installation complète (première utilisation)

```bash
make setup
```

Cette commande effectue :
1. ✅ Vérification que `uv` est installé
2. 📦 Installation des dépendances Python
3. 🗄️ Initialisation de la base de données SQLite
4. 👤 Création de l'utilisateur admin par défaut

**Credentials admin par défaut :**
- Email : `admin@mppeep.com`
- Mot de passe : `admin123`

### 🚀 Lancer l'application (mode développement)

```bash
make start
```

L'application sera accessible sur :
- `http://localhost:9000`
- `http://127.0.0.1:9000`

**Caractéristiques :**
- ⚡ Hot-reload activé (changements automatiques)
- 🗄️ Base de données SQLite (`app.db`)
- 🐛 Debug mode activé
- 🛑 Arrêter : `Ctrl+C`

### 🏭 Lancer l'application (mode production)

```bash
make start-prod
```

**Caractéristiques :**
- 🚀 Performances optimisées
- 🗄️ Base de données PostgreSQL
- 🔒 Debug mode désactivé
- 👷 4 workers Uvicorn

### 🛑 Arrêter l'application

```bash
make stop
```

Arrête tous les processus Uvicorn en cours.

### 🔄 Redémarrer l'application

```bash
make restart
```

Équivalent à `make stop` suivi de `make start`.

---

## 🔧 Gestion de l'Environnement

### 📦 Installer les dépendances

```bash
make install
```

Installe toutes les dépendances Python avec `uv sync --extra dev`.

### 🔍 Vérifier l'environnement

```bash
make env-check
```

Vérifie :
- ✅ Installation de `uv`
- 🐍 Version de Python
- 📚 Dépendances installées
- 🗄️ État de la base de données
- 📁 Fichiers de configuration

### ℹ️ Informations sur l'environnement

```bash
make env-info
```

Affiche :
- 📂 Répertoire de travail
- 🐍 Version Python
- 📦 Version de uv
- 🗃️ Variables d'environnement

---

## 📦 Gestion UV (Dépendances)

UV est le gestionnaire de paquets rapide utilisé par ce projet. Voici toutes les commandes disponibles :

### 🔄 Synchroniser les dépendances

```bash
make uv-sync
```

Synchronise les dépendances depuis `pyproject.toml`. Équivalent à `uv sync`.

### ➕ Ajouter une dépendance

```bash
# Ajouter une dépendance de production
make uv-add PKG=requests

# Ajouter une dépendance de développement
make uv-add-dev PKG=pytest-mock
```

Exemples :
```bash
make uv-add PKG=httpx
make uv-add PKG="fastapi[all]"
make uv-add-dev PKG=black
```

### ➖ Supprimer une dépendance

```bash
make uv-remove PKG=requests
```

Supprime une dépendance de `pyproject.toml` et de l'environnement.

### 🔒 Verrouiller les dépendances

```bash
make uv-lock
```

Met à jour le fichier `uv.lock` avec les versions exactes des dépendances.

### 📋 Lister les paquets installés

```bash
make uv-list
```

Affiche tous les paquets Python installés dans l'environnement.

### 🔍 Voir les paquets obsolètes

```bash
make uv-outdated
```

Affiche les paquets qui peuvent être mis à jour vers une version plus récente.

### 🌳 Afficher l'arbre des dépendances

```bash
make uv-tree
```

Affiche l'arbre des dépendances avec leurs relations.

### ⬆️ Mettre à jour toutes les dépendances

```bash
make uv-update
```

Met à jour toutes les dépendances vers leurs dernières versions compatibles.

### 🧹 Nettoyer le cache UV

```bash
make uv-clean
```

Nettoie le cache de UV pour libérer de l'espace disque.

### ℹ️ Version de UV

```bash
make uv-version
```

Affiche les versions de UV et Python.

### 🐍 Créer un environnement virtuel

```bash
make uv-venv
```

Crée un nouvel environnement virtuel (note : avec UV, c'est géré automatiquement).

### 📦 Installer un paquet avec uv pip

```bash
make uv-pip-install PKG=package-name
```

Installe un paquet directement avec `uv pip install` (alternative à `uv add`).

### 📤 Exporter les dépendances

```bash
make uv-export
```

Exporte les dépendances installées vers `requirements-exported.txt`.

---

## 🗄️ Gestion de la Base de Données

### 🆕 Initialiser la base de données

```bash
make db-init
```

Crée la base de données et les tables si elles n'existent pas.

### ♻️ Réinitialiser la base de données

```bash
make db-reset
```

**⚠️ ATTENTION : Supprime toutes les données !**

Cette commande :
1. Supprime le fichier `app.db`
2. Réinitialise la base de données
3. Recrée l'utilisateur admin par défaut

### 💾 Sauvegarder la base de données

```bash
make db-backup
```

Crée une copie de `app.db` dans le dossier `backups/` avec un timestamp :
- Format : `app_backup_YYYYMMDD_HHMMSS.db`
- Exemple : `app_backup_20251020_143025.db`

### 👤 Créer un utilisateur admin

```bash
make create-admin
```

Lance le script de création d'utilisateur en mode interactif.

---

## 🧪 Tests

### 🧪 Lancer tous les tests

```bash
make test
```

Lance tous les tests avec Pytest en mode verbose.

### 🎯 Tests unitaires uniquement

```bash
make test-unit
```

Lance uniquement les tests du dossier `tests/unit/`.

### 🔗 Tests d'intégration

```bash
make test-integration
```

Lance uniquement les tests du dossier `tests/integration/`.

### 🚨 Tests critiques (CI/CD)

```bash
make test-critical
```

Lance uniquement les tests marqués comme `@pytest.mark.critical`.

### 📊 Tests avec couverture

```bash
make test-cov
```

Lance les tests avec rapport de couverture de code :
- 📈 Rapport HTML : `htmlcov/index.html`
- 📊 Rapport console avec lignes manquantes

---

## 📋 Qualité du Code

### 🔍 Vérifier le code (Linting)

```bash
make lint
```

Vérifie le code avec Ruff sans le modifier.

### 🔧 Corriger automatiquement

```bash
make lint-fix
```

Corrige automatiquement les problèmes détectés par Ruff.

### 🎨 Formater le code

```bash
make format
```

Formate le code avec Ruff (style PEP 8).

### 👀 Vérifier le formatage

```bash
make format-check
```

Vérifie le formatage sans modifier les fichiers.

### 🧹 Nettoyage complet du code

```bash
make clean-code
```

Effectue un nettoyage complet :
1. 🎨 Formatage du code
2. 📦 Tri des imports
3. 🔧 Corrections automatiques
4. 📊 Vérification finale avec statistiques

### ✅ Vérifier tout

```bash
make check-all
```

Vérifie le formatage ET le linting sans modifier les fichiers.

---

## 🧹 Maintenance

### 🗑️ Nettoyer les fichiers temporaires

```bash
make clean
```

Supprime :
- `__pycache__/`
- `.pytest_cache/`
- `.ruff_cache/`
- `htmlcov/`
- `.coverage`

### 🧹 Nettoyage complet

```bash
make clean-all
```

Effectue `make clean` + vide les fichiers de logs :
- `logs/app.log`
- `logs/error.log`
- `logs/access.log`

### 📋 Voir les logs

```bash
make logs
```

Affiche les 50 dernières lignes de `logs/app.log` en mode suivi (comme `tail -f`).

---

## 🔀 Git & Version Control

### 📊 Statut Git

```bash
make git-status
```

Affiche le statut des fichiers Git.

### 📜 Historique des commits

```bash
make git-log
```

Affiche les 10 derniers commits en mode graphique.

### 🔍 Voir les modifications

```bash
make git-diff
```

Affiche les modifications non committées.

### 🌿 Lister les branches

```bash
make git-branches
```

Liste toutes les branches locales et distantes.

### ✅ Préparer un commit

```bash
make pre-commit
```

Prépare le code pour un commit :
1. 🧹 Nettoyage et formatage du code
2. 🧪 Exécution des tests
3. ✅ Validation complète

### 📤 Push vers origin

```bash
make push
```

Push la branche actuelle vers le remote `origin`.

### 📥 Pull depuis origin

```bash
make pull
```

Pull la branche actuelle depuis le remote `origin`.

### 🔄 Synchronisation complète

```bash
make sync
```

Effectue une synchronisation complète :
1. 📥 Pull
2. 🧹 Nettoyage du code
3. 🧪 Tests
4. 📤 Push

---

## 🐳 Docker (Optionnel)

### 🐳 Démarrer en mode développement

```bash
make dev-up
```

Lance l'application avec Docker Compose en mode dev (hot-reload).

### 🛑 Arrêter Docker dev

```bash
make dev-down
```

### 📋 Voir les logs Docker

```bash
make dev-logs
```

### 🏭 Démarrer en mode production

```bash
make up
```

Lance l'application avec Docker Compose en mode production.

### 🛑 Arrêter Docker prod

```bash
make down
```

### 📊 Statut des conteneurs

```bash
make ps
```

---

## 🎯 Workflows Recommandés

### 🆕 Premier démarrage du projet

```bash
# 1. Installation complète
make setup

# 2. Vérifier que tout fonctionne
make env-check

# 3. Lancer l'application
make start
```

### 💻 Développement quotidien

```bash
# Lancer l'application
make start

# Dans un autre terminal : lancer les tests
make test

# Nettoyer le code avant de committer
make clean-code
```

### 🚀 Avant de committer

```bash
# Préparation complète (clean + test)
make pre-commit

# Si tout est OK, commiter et pousser
git add .
git commit -m "feat: description"
make push
```

### 🔄 Mise à jour du projet

```bash
# Récupérer les dernières modifications
make pull

# Installer les nouvelles dépendances
make install

# Mettre à jour la base de données
make db-init
```

### 🐛 Debugging

```bash
# Voir les logs en temps réel
make logs

# Vérifier l'environnement
make env-check

# Réinitialiser la base si problème
make db-reset
```

---

## 📝 Notes Importantes

### ⚠️ Variables d'Environnement

Les commandes `make start` et `make start-prod` définissent automatiquement les variables d'environnement :

**Mode Dev (`make start`) :**
```powershell
$env:DEBUG="True"
$env:ENV="dev"
```

**Mode Prod (`make start-prod`) :**
```powershell
$env:DEBUG="False"
$env:ENV="prod"
```

### 🔐 Fichier .env

Vous pouvez créer un fichier `.env` pour surcharger ces valeurs :

```bash
# .env
DEBUG=False
ENV=prod
DATABASE_URL=postgresql://user:pass@localhost:5432/mppeep
SECRET_KEY=votre-cle-secrete
```

### 🐍 Environnement Virtuel

Le Makefile utilise `uv` qui gère automatiquement l'environnement virtuel. Vous n'avez **pas besoin** d'activer manuellement un venv !

Chaque commande `uv run` s'exécute dans l'environnement virtuel géré par `uv`.

### 🪟 Compatibilité Windows

Le Makefile est optimisé pour **Windows PowerShell**. Si vous êtes sur Linux/Mac, certaines commandes (comme `Test-Path`, `Remove-Item`) devront être adaptées.

---

## 🆘 Aide & Support

### ❓ Problème avec une commande ?

```bash
# Afficher l'aide
make help

# Vérifier l'environnement
make env-check

# Voir les informations détaillées
make env-info
```

### 🐛 Erreurs courantes

**Erreur : "uv: command not found"**
```bash
# Installer uv
pip install uv
```

**Erreur : "Database locked"**
```bash
# Arrêter l'application et relancer
make stop
make start
```

**Erreur : Tests échouent**
```bash
# Nettoyer et réinstaller
make clean
make install
make test
```

---

## 📚 Ressources

- 📖 Documentation FastAPI : https://fastapi.tiangolo.com
- 📦 Documentation uv : https://github.com/astral-sh/uv
- 🧪 Documentation Pytest : https://docs.pytest.org
- 🎨 Documentation Ruff : https://docs.astral.sh/ruff

---

**Bon développement ! 🚀**

