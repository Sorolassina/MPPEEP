# 🛠️ Scripts Utilitaires

Ce dossier contient des scripts d'administration et de maintenance.

## 📋 Scripts Disponibles

### `init_db.py` ⭐ (Nouveau)
**Initialisation automatique de la base de données et de l'utilisateur admin.**

Ce script est **exécuté automatiquement** au démarrage de l'application (`app/main.py`).

```bash
# Exécution manuelle (optionnel)
python scripts/init_db.py
```

**Actions automatiques :**
1. ✅ Crée toutes les tables de la base de données (si elles n'existent pas)
2. ✅ Crée un utilisateur admin par défaut (si aucun utilisateur n'existe)

**Identifiants admin par défaut :**
- Email: `admin@mppeep.com`
- Password: `admin123`
- Rôle: Superuser

⚠️ **IMPORTANT :** Changez le mot de passe admin en production !

---

### `create_user.py`
Crée un utilisateur (admin ou normal) avec des paramètres personnalisés.

```bash
# Créer l'admin par défaut
python scripts/create_user.py

# Créer un utilisateur personnalisé
python scripts/create_user.py user@example.com "John Doe" "password123"

# Créer un superuser personnalisé
python scripts/create_user.py admin@example.com "Super Admin" "secure_pass" --superuser

# Créer un utilisateur normal
python scripts/create_user.py user@example.com "User Name" "pass123"
```

**Arguments :**
- `email` : Email de l'utilisateur (défaut: admin@mppeep.com)
- `full_name` : Nom complet (défaut: Admin MPPEEP)
- `password` : Mot de passe (défaut: admin123)
- `--superuser` : Créer un super utilisateur (optionnel)

---

### `migrate_database.py`
Migre les données d'une base de données vers une autre.

```bash
# SQLite → PostgreSQL
python scripts/migrate_database.py \
    "sqlite:///./app.db" \
    "postgresql://user:pass@localhost:5432/mppeep"

# PostgreSQL → SQLite (backup)
python scripts/migrate_database.py \
    "postgresql://user:pass@localhost:5432/mppeep" \
    "sqlite:///./backup.db"
```

---

### `show_config.py`
Affiche la configuration actuelle de l'application.

```bash
python scripts/show_config.py
```

Affiche :
- Nom de l'application
- Environnement (dev/staging/production)
- Mode debug
- Type de base de données
- URL de connexion

---

## 🔧 Note Technique

Les scripts ajoutent automatiquement le dossier parent au `PYTHONPATH` pour pouvoir importer le module `app`. Vous devez les exécuter depuis la racine du projet :

```bash
# ✅ Correct
cd mppeep
python scripts/create_test_user.py

# ❌ Incorrect
cd mppeep/scripts
python create_test_user.py  # Ne fonctionnera pas
```

---

## 📚 Différence avec les Tests

| Scripts | Tests |
|---------|-------|
| Outils d'administration | Validation du code |
| Modifient la base de données | Utilisent une DB en mémoire |
| Exécution manuelle ou auto | Exécution avec pytest |
| `scripts/*.py` | `tests/test_*.py` |
| Production | Développement |

---

## 🚀 Initialisation Automatique au Démarrage

### Comment ça fonctionne ?

Lorsque vous démarrez l'application FastAPI :

```bash
uvicorn app.main:app --reload
```

**Séquence automatique :**
```
1. FastAPI démarre
   ↓
2. Événement "startup" se déclenche (app/main.py)
   ↓
3. Appel de scripts/init_db.py
   ↓
4. Vérification des tables → Création si nécessaire
   ↓
5. Vérification des utilisateurs → Création admin si DB vide
   ↓
6. Application prête à recevoir des requêtes ✅
```

### Dans le code (`app/main.py`)

```python
@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    from scripts.init_db import initialize_database
    initialize_database()
```

### Avantages

✅ **Aucune configuration manuelle** nécessaire  
✅ **Idempotent** : peut être exécuté plusieurs fois sans problème  
✅ **Sécurisé** : vérifie avant de créer  
✅ **Automatique** : fonctionne sur tous les environnements (dev/staging/prod)  

### Cas d'usage

**Premier démarrage :**
```
Base vide → Crée tables + admin → Prêt ! ✅
```

**Démarrages suivants :**
```
Tables existent → Admin existe → Skip → Prêt ! ✅
```

**Après suppression de la DB :**
```
Pas de DB → Crée tout → Prêt ! ✅
```

---

## 🎯 Cas d'Usage des Scripts

### Développement

```bash
# Démarrer l'application (init auto)
uvicorn app.main:app --reload
# → Tables + Admin créés automatiquement

# Créer des utilisateurs supplémentaires
python scripts/create_user.py user@test.com "Test User" "test123"
```

### Production

```bash
# Premier déploiement
uvicorn app.main:app --host 0.0.0.0 --port 8000
# → Init automatique

# Changer le mot de passe admin
# 1. Se connecter avec admin@mppeep.com / admin123
# 2. Changer le mot de passe via l'interface
# OU créer un nouvel admin et supprimer l'ancien
```

### Migration

```bash
# Migrer entre bases
python scripts/migrate_database.py \
    "sqlite:///./app.db" \
    "postgresql://user:pass@host:5432/db"
```

