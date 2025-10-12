# ⚡ Quick Start - MPPEEP Dashboard

## 🎯 Démarrage Ultra-Rapide (2 Minutes)

```bash
# 1. Cloner le projet
git clone [votre-repo] mon-projet
cd mon-projet/mppeep

# 2. Installer les dépendances
pip install uv
uv sync

# 3. Démarrer l'application
uvicorn app.main:app --reload

# ✅ C'est tout ! La base de données et l'admin sont créés automatiquement
```

**Ouvrir dans le navigateur :**
- Application : http://localhost:8000
- Documentation API : http://localhost:8000/docs
- Login : http://localhost:8000/api/v1/login

**Identifiants admin par défaut :**
- Email : `admin@mppeep.com`
- Password : `admin123`

---

## 🔄 Ce Qui Se Passe Automatiquement

Au premier démarrage, l'application :

```
1. ✅ Crée la base de données SQLite
2. ✅ Crée toutes les tables (user, etc.)
3. ✅ Crée l'utilisateur admin par défaut
4. ✅ Affiche les identifiants dans le terminal
5. ✅ Application prête à l'emploi !
```

**Console Output :**
```
🚀 Initialisation de la base de données...
📂 Base de données: sqlite:///./app.db
--------------------------------------------------
✅ Tables de la base de données créées/vérifiées

==================================================
✅ UTILISATEUR ADMIN CRÉÉ
==================================================
📧 Email    : admin@mppeep.com
🔑 Password : admin123
🆔 ID       : 1
==================================================
⚠️  IMPORTANT: Changez ce mot de passe en production!
==================================================

✅ Initialisation terminée avec succès!

INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

## 📚 Endpoints Disponibles

### Pages HTML

```
http://localhost:8000/                   ← Page d'accueil
http://localhost:8000/api/v1/login       ← Login
http://localhost:8000/api/v1/forgot-password  ← Mot de passe oublié
http://localhost:8000/accueil           ← Page d'accueil (après login)
```

### API REST

```
http://localhost:8000/docs               ← Documentation Swagger
http://localhost:8000/redoc              ← Documentation ReDoc
http://localhost:8000/api/v1/ping        ← Health check
http://localhost:8000/api/v1/users       ← CRUD utilisateurs
```

---

## 🛠️ Commandes Utiles

### Développement

```bash
# Démarrer avec hot-reload
uvicorn app.main:app --reload

# Démarrer avec logs verbeux
uvicorn app.main:app --reload --log-level debug

# Voir la configuration actuelle
python scripts/show_config.py
```

### Tests

```bash
# Tous les tests
pytest

# Tests avec couverture
pytest --cov=app

# Tests verbeux
pytest -v
```

### Gestion Utilisateurs

```bash
# Créer un utilisateur normal
python scripts/create_user.py user@example.com "John Doe" "password123"

# Créer un admin
python scripts/create_user.py admin2@example.com "Admin 2" "secure_pass" --superuser

# Réinitialiser la base (tout supprimer et recréer)
rm app.db
python scripts/init_db.py
```

---

## 🌍 Multi-Environnements

### Développement (SQLite)

```bash
# .env ou variables d'environnement
DEBUG=true
ENV=dev

# → Utilise SQLite automatiquement
```

### Production (PostgreSQL)

```bash
# .env
DEBUG=false
ENV=production
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secret
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mppeep

# → Utilise PostgreSQL automatiquement
```

---

## 🚀 Déploiement

### Option 1 : Scripts PowerShell (Windows)

```powershell
# Configuration
cd deploy/config
cp env.production.template .env.production
# Modifier .env.production

# Déploiement
.\deploy\scripts\deploy.ps1 -Environment production
```

**Voir :** `deploy/QUICKSTART.md`

---

### Option 2 : GitHub Actions (CI/CD)

```bash
# Push vers GitHub
git push origin main

# → Tests automatiques lancés

# Déploiement production
GitHub → Actions → CD Production → Run workflow → Saisir "DEPLOY"
```

**Voir :** `.github/SETUP_GITHUB_ACTIONS.md`

---

## 📖 Documentation Complète

| Fichier | Description |
|---------|-------------|
| `README.md` | Introduction générale |
| `QUICK_START.md` | Ce fichier (démarrage rapide) |
| `STARTUP_INITIALIZATION.md` | Détails initialisation auto |
| `PROJECT_STRUCTURE.md` | Architecture du projet |
| `FEATURES.md` | Liste des fonctionnalités |
| `.github/CICD_README.md` | CI/CD avec GitHub Actions |
| `deploy/README.md` | Déploiement Windows |
| `scripts/README.md` | Scripts utilitaires |
| `tests/README.md` | Guide des tests |

---

## 🎯 Prochaines Étapes

### Après le Premier Démarrage

1. **Tester l'application**
   - Ouvrir http://localhost:8000/api/v1/login
   - Se connecter avec `admin@mppeep.com / admin123`
   - Explorer l'accueil

2. **Changer le mot de passe admin**
   - Via l'interface (TODO: implémenter)
   - OU créer un nouvel admin et désactiver l'ancien

3. **Personnaliser pour votre projet**
   - Modifier `app/models/` pour vos données
   - Ajouter vos endpoints dans `app/api/v1/endpoints/`
   - Personnaliser les templates

4. **Configurer le déploiement**
   - GitHub Actions : `.github/SETUP_GITHUB_ACTIONS.md`
   - PowerShell : `deploy/README.md`

---

## 💡 Astuces

### Réinitialiser Complètement

```bash
# Supprimer la base de données
rm app.db

# Redémarrer l'application
uvicorn app.main:app --reload

# → Tout est recréé automatiquement !
```

### Désactiver l'Initialisation Auto

Si vous voulez désactiver l'initialisation automatique :

```python
# Dans app/main.py, commenter :
# @app.on_event("startup")
# async def startup_event():
#     ...
```

### Changer les Identifiants Admin par Défaut

```python
# Dans scripts/init_db.py, modifier :
admin_email = "votre@email.com"
admin_password = "votre_password"
```

---

## 🎉 C'est Parti !

Vous êtes prêt à démarrer ! L'application s'initialise automatiquement et vous pouvez commencer à développer immédiatement.

**Bon développement ! 🚀**

