# 🏷️ Énumérations (Enums) - Guide Complet

## 🎯 Qu'est-ce qu'un Enum ?

Un **enum** (énumération) est une liste de **constantes nommées** qui représentent des valeurs fixes.

**Pourquoi utiliser des enums ?**
- ✅ **Sécurité** : Impossible de mettre une valeur invalide
- ✅ **Lisibilité** : `UserType.ADMIN` au lieu de `"admin"`
- ✅ **Autocomplétion** : L'IDE suggère les valeurs possibles
- ✅ **Refactoring** : Changer une valeur partout en 1 fois
- ✅ **Documentation** : Les valeurs possibles sont dans le code

---

## 📁 Fichier : `app/core/enums.py`

---

## 📋 Enums Disponibles

### 1️⃣ UserType (Type d'Utilisateur)

```python
from app.core.enums import UserType

class UserType(str, Enum):
    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"
    GUEST = "guest"
```

**Utilisation :**

```python
from app.core.enums import UserType

# Créer un admin
user = User(
    email="admin@app.com",
    type_user=UserType.ADMIN  # ← Utiliser l'enum
)

# Vérifier le type
if user.type_user == UserType.ADMIN:
    print("C'est un administrateur")

# Dans une requête SQL
statement = select(User).where(User.type_user == UserType.ADMIN)
admins = session.exec(statement).all()
```

**Stockage en base :**
```sql
-- Stocké comme VARCHAR (texte)
type_user VARCHAR  →  "admin", "user", "moderator", ou "guest"
```

**PAS de table séparée** ! Juste du texte.

---

### 2️⃣ UserStatus (Statut d'Utilisateur)

```python
class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
```

**Utilisation future :**

```python
# Au lieu de is_active (booléen simple)
user.status = UserStatus.SUSPENDED

# Permet plus de nuances
if user.status == UserStatus.PENDING:
    send_activation_email(user)
```

---

### 3️⃣ Environment (Environnement)

```python
class Environment(str, Enum):
    DEVELOPMENT = "dev"
    STAGING = "staging"
    PRODUCTION = "production"
```

**Utilisation dans config :**

```python
from app.core.enums import Environment

# Dans app/core/config.py
ENV: Environment = Environment.DEVELOPMENT

# Vérification
if settings.ENV == Environment.PRODUCTION:
    enable_https_redirect()
```

---

## 🎯 Pourquoi `str, Enum` ?

```python
class UserType(str, Enum):
    #            ↑ Hérite de str
    ADMIN = "admin"
```

**Avantages :**
1. **Sérialisation JSON** : Fonctionne directement avec FastAPI
2. **Stockage DB** : Stocké comme VARCHAR
3. **Comparaison** : Peut être comparé à une string

```python
# Sans str
user.type_user == "admin"  # ❌ Ne fonctionne pas

# Avec str
user.type_user == "admin"  # ✅ Fonctionne !
user.type_user == UserType.ADMIN  # ✅ Fonctionne aussi !
```

---

## 📊 Comparaison : Avant vs Après

### ❌ Avant (Sans Enums)

```python
# Création d'utilisateur
user = User(
    email="admin@app.com",
    type_user="admin"  # ← String en dur, risque de typo
)

# Vérification
if user.type_user == "admin":  # ← Typo possible : "admn", "Admin", "ADMIN"
    print("Admin")

# Problèmes :
# - Pas d'autocomplétion
# - Typos possibles
# - Valeurs non documentées
# - Difficile à refactorer
```

---

### ✅ Après (Avec Enums)

```python
from app.core.enums import UserType

# Création d'utilisateur
user = User(
    email="admin@app.com",
    type_user=UserType.ADMIN  # ← Enum, autocomplétion, pas de typo
)

# Vérification
if user.type_user == UserType.ADMIN:  # ← Sûr, autocomplété
    print("Admin")

# Avantages :
# ✅ Autocomplétion IDE
# ✅ Pas de typo possible
# ✅ Valeurs documentées
# ✅ Refactoring facile
```

---

## 🔧 Utilisation dans le Code

### Dans les Modèles

```python
from app.core.enums import UserType

class User(SQLModel, table=True):
    type_user: str = Field(default=UserType.USER)
    
    @property
    def is_admin(self) -> bool:
        return self.type_user == UserType.ADMIN
```

---

### Dans les Services

```python
from app.core.enums import UserType

class UserService:
    @staticmethod
    def create_admin(session, email, name, password):
        return UserService.create_user(
            session,
            email,
            name,
            password,
            type_user=UserType.ADMIN  # ← Enum
        )
```

---

### Dans les Endpoints

```python
from app.core.enums import UserType

@router.post("/users")
def create_user(user_data: UserCreate):
    user = UserService.create_user(
        session,
        user_data.email,
        user_data.name,
        user_data.password,
        type_user=UserType.USER  # ← Par défaut USER
    )
```

---

### Dans les Scripts

```python
from app.core.enums import UserType

# Créer un admin
admin = UserService.create_user(
    session,
    "admin@app.com",
    "Admin",
    "pass",
    type_user=UserType.ADMIN
)

# Créer un modérateur
mod = UserService.create_user(
    session,
    "mod@app.com",
    "Moderator",
    "pass",
    type_user=UserType.MODERATOR
)
```

---

## 🎯 Nouvelle Logique d'Initialisation

### ❌ Ancienne Logique

```python
# Si AUCUN utilisateur existe → Créer admin
if UserService.count_users(session) == 0:
    create_admin()
```

**Problème :** Si vous créez des users normaux en premier, l'admin n'est jamais créé !

---

### ✅ Nouvelle Logique

```python
# Si AUCUN ADMIN existe → Créer admin
if not UserService.has_admin(session):
    create_admin()
```

**Avantage :** 
- Même s'il y a 100 users normaux, l'admin sera créé au démarrage
- L'admin n'est créé qu'une seule fois (pas de doublon)

---

## 📝 Scénarios

### Scénario 1 : Premier Démarrage (Base Vide)

```
uvicorn app.main:app

Console :
✅ Tables créées
ℹ️  0 utilisateur(s) trouvé(s)
📦 Création de l'admin par défaut...
✅ ADMINISTRATEUR CRÉÉ
   Type: admin
```

**Résultat :** Base avec 1 admin

---

### Scénario 2 : Base avec Users Normaux Seulement

```
Base avant :
- user1@test.com (type: user)
- user2@test.com (type: user)
- user3@test.com (type: user)

uvicorn app.main:app

Console :
✅ Tables créées
ℹ️  3 utilisateur(s) trouvé(s) mais aucun admin
📦 Création de l'admin par défaut...
✅ ADMINISTRATEUR CRÉÉ
   Type: admin
```

**Résultat :** Base avec 3 users + 1 admin

---

### Scénario 3 : Base avec Déjà un Admin

```
Base avant :
- admin@company.com (type: admin)
- user1@test.com (type: user)

uvicorn app.main:app

Console :
✅ Tables créées
ℹ️  1 administrateur(s) trouvé(s) - Pas de création nécessaire
✅ Initialisation terminée
```

**Résultat :** Rien n'est créé (admin existe déjà)

---

## 🚀 Utilisation du Script CLI

### Créer un Admin

```bash
# Méthode 1 : Avec --type
python scripts/create_user.py admin@company.com "Super Admin" "P@ss" --type admin

# Méthode 2 : Avec --superuser (rétrocompatibilité)
python scripts/create_user.py admin@company.com "Super Admin" "P@ss" --superuser

# Output :
✅ UTILISATEUR CRÉÉ
📧 Email      : admin@company.com
👔 Type       : admin  ← Type affiché
```

---

### Créer un User Normal

```bash
python scripts/create_user.py user@test.com "John Doe" "pass123"

# Output :
✅ UTILISATEUR CRÉÉ
📧 Email      : user@test.com
👔 Type       : user
```

---

### Créer un Modérateur

```bash
python scripts/create_user.py mod@app.com "Moderator" "pass" --type moderator

# Output :
✅ UTILISATEUR CRÉÉ
📧 Email      : mod@app.com
👔 Type       : moderator
```

---

### Créer un Invité

```bash
python scripts/create_user.py guest@app.com "Guest User" "pass" --type guest

# Output :
✅ UTILISATEUR CRÉÉ
📧 Email      : guest@app.com
👔 Type       : guest
```

---

## 📊 Structure en Base de Données

### Table `user`

```sql
CREATE TABLE user (
    id INTEGER PRIMARY KEY,
    email VARCHAR UNIQUE,
    full_name VARCHAR,
    hashed_password VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    type_user VARCHAR DEFAULT 'user',  ← Stocké comme texte
    created_at DATETIME,
    updated_at DATETIME
);
```

**Exemples de données :**

| id | email | type_user | is_superuser |
|----|-------|-----------|--------------|
| 1 | admin@mppeep.com | `"admin"` | `true` |
| 2 | user@test.com | `"user"` | `false` |
| 3 | mod@app.com | `"moderator"` | `false` |
| 4 | guest@app.com | `"guest"` | `false` |

**Note :** Stocké comme **VARCHAR**, pas comme une table séparée.

---

## ✅ Avantages de Cette Approche

### vs Table Séparée (user_types)

| Aspect | Enum (VARCHAR) | Table Séparée |
|--------|----------------|---------------|
| **Simplicité** | ✅ Simple | ❌ Complexe |
| **Performance** | ✅ Rapide | ⚠️ JOIN nécessaire |
| **Migration** | ✅ Facile | ❌ Difficile |
| **Code** | ✅ Minimal | ❌ Beaucoup de code |
| **Flexibilité** | ⚠️ Moins flexible | ✅ Très flexible |

**Pour votre cas (4 types fixes) → Enum est PARFAIT ! ✅**

---

## 🎓 Bonnes Pratiques

### ✅ DO

```python
# Utiliser l'enum
user.type_user = UserType.ADMIN

# Comparaison avec enum
if user.type_user == UserType.ADMIN:
    ...

# Dans les queries
statement = select(User).where(User.type_user == UserType.MODERATOR)
```

---

### ❌ DON'T

```python
# Ne pas utiliser de strings en dur
user.type_user = "admin"  # ❌ Risque de typo

# Ne pas comparer avec des strings si possible
if user.type_user == "admin":  # ⚠️ Fonctionne mais moins sûr
    ...
```

---

## 📚 Ajouter de Nouveaux Enums

### Exemple : Rôles Plus Détaillés

```python
# app/core/enums.py

class UserRole(str, Enum):
    """Rôles détaillés pour permissions"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    EDITOR = "editor"
    VIEWER = "viewer"
    GUEST = "guest"
```

```python
# app/models/user.py

class User(SQLModel, table=True):
    role: str = Field(default=UserRole.VIEWER)
```

---

## ✨ Résumé

**Enums = Constantes Typées pour Valeurs Fixes**

- ✅ 3 enums créés : `UserType`, `UserStatus`, `Environment`
- ✅ Stockés comme VARCHAR (texte) en base
- ✅ Pas de table séparée
- ✅ Autocomplétion et sécurité
- ✅ Nouvelle logique : Créer admin SI aucun admin existe (au lieu de "si base vide")

**Votre code est maintenant plus sûr et plus maintenable ! 🎉**

