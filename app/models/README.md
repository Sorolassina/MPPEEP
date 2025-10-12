# 🗃️ Dossier Models - Structure des Données

## 🤔 C'est Quoi ?

Le dossier `models/` définit la **structure de vos tables** en base de données. Chaque modèle = une table.

### 🏗️ Analogie Simple

Imaginez un formulaire papier :

- 📋 **Modèle** = Le formulaire vierge (définit les champs)
- ✏️ **Instance** = Un formulaire rempli (les données)
- 🗄️ **Table DB** = Le classeur qui range tous les formulaires

**Exemple :**

```
Modèle User (formulaire vierge) :
┌─────────────────────┐
│ ID:     _________   │
│ Email:  _________   │
│ Nom:    _________   │
└─────────────────────┘

Instance User (formulaire rempli) :
┌─────────────────────┐
│ ID:     1           │
│ Email:  john@ex.com │
│ Nom:    John Doe    │
└─────────────────────┘
```

---

## 📁 Structure

```
app/models/
├── __init__.py       ← Exports de tous les modèles
├── user.py           ← Modèle User
└── session.py        ← Modèle UserSession (multi-device)
```

**Convention :** Un fichier = Un modèle

---

## 📋 Modèle User Expliqué

### Code Actuel

```python
from typing import Optional
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    full_name: str | None = None
    hashed_password: str
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
```

### Ligne par Ligne

```python
class User(SQLModel, table=True):
# ↑      ↑        ↑
# Nom    Héritage table=True → Créer une table en DB
```

**Champs :**

| Champ | Type | Description | Contrainte |
|-------|------|-------------|------------|
| `id` | `int` | Identifiant unique | Primary Key, Auto-incrémenté |
| `email` | `str` | Email de l'utilisateur | Unique, Indexé |
| `full_name` | `str \| None` | Nom complet | Optionnel |
| `hashed_password` | `str` | Mot de passe hashé | Obligatoire |
| `is_active` | `bool` | Compte actif ? | Default: True |
| `is_superuser` | `bool` | Est admin ? | Default: False |

---

## 📋 Modèle UserSession Expliqué

### Code Actuel

```python
from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime, timedelta
import secrets

class UserSession(SQLModel, table=True):
    __tablename__ = "user_sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_token: str = Field(unique=True, index=True, max_length=255)
    user_id: int = Field(foreign_key="user.id", index=True)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    device_info: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    expires_at: datetime = Field(default_factory=lambda: datetime.now() + timedelta(days=7))
    is_active: bool = Field(default=True)
```

### Ligne par Ligne

**Champs :**

| Champ | Type | Description | Contrainte |
|-------|------|-------------|------------|
| `id` | `int` | Identifiant unique | Primary Key, Auto-incrémenté |
| `session_token` | `str` | Token unique de session | Unique, Indexé, 255 caractères |
| `user_id` | `int` | ID de l'utilisateur | Foreign Key vers `user.id`, Indexé |
| `ip_address` | `str \| None` | Adresse IP du client | Optionnel, max 45 caractères (IPv6) |
| `user_agent` | `str \| None` | User-Agent du navigateur | Optionnel, max 500 caractères |
| `device_info` | `str \| None` | Info device (ex: "Chrome on Windows") | Optionnel, max 255 caractères |
| `created_at` | `datetime` | Date de création | Auto-généré |
| `last_activity` | `datetime` | Dernière activité | Mis à jour automatiquement |
| `expires_at` | `datetime` | Date d'expiration | Default: 7 jours |
| `is_active` | `bool` | Session active ? | Default: True |

### Méthodes du Modèle

```python
# Générer un token sécurisé
@staticmethod
def generate_token() -> str:
    return secrets.token_urlsafe(32)

# Vérifier si la session est expirée
def is_expired(self) -> bool:
    return datetime.now() > self.expires_at

# Rafraîchir la session
def refresh(self, days: int = 7):
    self.last_activity = datetime.now()
    self.expires_at = datetime.now() + timedelta(days=days)

# Désactiver la session (logout)
def deactivate(self):
    self.is_active = False
```

### Pourquoi un Modèle Session ?

**Avantages :**
- ✅ **Multi-device** : Un utilisateur peut avoir plusieurs sessions actives (bureau, mobile, tablette)
- ✅ **Sécurité** : Tokens sécurisés générés avec `secrets.token_urlsafe()`
- ✅ **Tracking** : Savoir d'où se connecte l'utilisateur (IP, device)
- ✅ **Expiration** : Sessions qui expirent automatiquement
- ✅ **Gestion** : L'utilisateur peut voir et déconnecter ses appareils

**Utilisation :**

```python
from app.models.session import UserSession
from app.services.session_service import SessionService

# Créer une session
user_session = SessionService.create_session(
    db_session=session,
    user=user,
    request=request,
    remember_me=True  # 30 jours au lieu de 7
)

# Vérifier une session
user = SessionService.get_user_from_session(session, session_token)

# Lister les sessions actives
sessions = SessionService.get_active_sessions(session, user.id)
for s in sessions:
    print(f"- {s.device_info} (dernière activité: {s.last_activity})")
```

---

## 🎯 Rôle des Modèles

### 1️⃣ Définir la Structure de la Table

```python
class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True)

# → Crée cette table SQL :
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR UNIQUE NOT NULL
);
```

### 2️⃣ Créer des Instances

```python
# Créer un utilisateur
user = User(
    email="john@example.com",
    full_name="John Doe",
    hashed_password="hashed...",
    is_active=True
)

# user est une instance du modèle User
```

### 3️⃣ Interagir avec la DB

```python
from sqlmodel import Session
from app.db import engine

with Session(engine) as session:
    # Créer
    user = User(email="test@test.com")
    session.add(user)
    session.commit()
    
    # Lire
    users = session.exec(select(User)).all()
    
    # Modifier
    user.email = "new@email.com"
    session.add(user)
    session.commit()
    
    # Supprimer
    session.delete(user)
    session.commit()
```

---

## 🔧 Field() - Options Avancées

### Clés Primaires

```python
id: int | None = Field(default=None, primary_key=True)
#                      ↑              ↑
#                      Auto-généré    Clé primaire
```

### Unique (Pas de Doublons)

```python
email: str = Field(unique=True)
# → Impossible d'avoir 2 users avec le même email
```

### Index (Performance)

```python
email: str = Field(index=True)
# → Recherches par email plus rapides
```

### Valeurs par Défaut

```python
is_active: bool = Field(default=True)
# → Si non spécifié, is_active=True automatiquement
```

### Optionnel

```python
full_name: str | None = None
#                       ↑
#                       Peut être None (NULL en SQL)
```

### Contraintes Personnalisées

```python
age: int = Field(ge=0, le=150)
# ge = greater or equal (>=)
# le = less or equal (<=)

price: float = Field(gt=0)
# gt = greater than (>)

username: str = Field(min_length=3, max_length=50)
```

---

## 💡 Créer un Nouveau Modèle

### Étape 1 : Créer le Fichier

```bash
touch app/models/product.py
```

### Étape 2 : Définir le Modèle

```python
# app/models/product.py

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class Product(SQLModel, table=True):
    """Modèle pour les produits"""
    
    # Clé primaire
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Informations de base
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    price: float = Field(gt=0)  # Prix > 0
    
    # Stock
    stock: int = Field(default=0, ge=0)  # Stock >= 0
    
    # Catégorie
    category: str | None = None
    
    # Statut
    is_available: bool = Field(default=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

### Étape 3 : Exporter dans __init__.py

```python
# app/models/__init__.py

from app.models.user import User
from app.models.product import Product  # ← Ajouter

__all__ = ["User", "Product"]
```

### Étape 4 : Créer la Table

```python
# Créer toutes les tables
from app.db import init_db

init_db()
# → Table 'product' créée !
```

---

## 🔗 Relations entre Modèles

### One-to-Many (Un à Plusieurs)

```python
# Un utilisateur a plusieurs articles

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str
    
    # Relation (optionnel, pour faciliter l'accès)
    # articles: list["Article"] = Relationship(back_populates="author")

class Article(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    
    # Clé étrangère
    user_id: int = Field(foreign_key="user.id")
    
    # Relation (optionnel)
    # author: User = Relationship(back_populates="articles")
```

**Usage :**
```python
# Accéder aux articles d'un user
user = session.get(User, 1)
articles = session.exec(
    select(Article).where(Article.user_id == user.id)
).all()
```

---

## 🎨 Bonnes Pratiques

### ✅ DO (À Faire)

1. **Noms au singulier**
   ```python
   # ✅ Bon
   class User(SQLModel, table=True):
       ...
   
   # ❌ Mauvais
   class Users(SQLModel, table=True):
       ...
   ```

2. **Type hints clairs**
   ```python
   # ✅ Bon
   email: str
   age: int | None
   created_at: datetime
   
   # ❌ Mauvais
   email: str = None  # Confus, optionnel ou pas ?
   ```

3. **Valeurs par défaut sensées**
   ```python
   # ✅ Bon
   is_active: bool = Field(default=True)
   created_at: datetime = Field(default_factory=datetime.now)
   
   # ❌ Mauvais
   is_active: bool  # Pas de défaut, obligatoire à spécifier
   ```

4. **Index sur les champs recherchés**
   ```python
   # ✅ Bon
   email: str = Field(index=True)
   # → Recherches par email rapides
   ```

5. **Contraintes de validation**
   ```python
   # ✅ Bon
   price: float = Field(gt=0)  # Prix > 0
   age: int = Field(ge=0, le=150)  # 0 <= age <= 150
   ```

---

### ❌ DON'T (À Éviter)

1. **❌ Mots de passe en clair**
   ```python
   # ❌ DANGEREUX
   password: str
   
   # ✅ SÉCURISÉ
   hashed_password: str
   ```

2. **❌ Pas de primary key**
   ```python
   # ❌ Mauvais
   class User(SQLModel, table=True):
       email: str
       # Pas d'ID !
   
   # ✅ Bon
   class User(SQLModel, table=True):
       id: int | None = Field(default=None, primary_key=True)
       email: str
   ```

3. **❌ Logique métier dans le modèle**
   ```python
   # ❌ Éviter
   class User(SQLModel, table=True):
       email: str
       
       def send_welcome_email(self):
           # Logique métier → mettre dans services/
   
   # ✅ Modèle = Structure de données uniquement
   ```

---

## 📊 SQLModel vs Pydantic

### Différence Clé

```python
# SQLModel (table=True) → Table en DB
class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str

# SQLModel (table=False) → Pas de table (juste validation)
class UserUpdate(SQLModel):
    email: str | None = None
    full_name: str | None = None

# Pydantic → Validation seulement
class UserCreate(BaseModel):
    email: EmailStr
    password: str
```

**Usage :**
- `table=True` → Modèle DB (stockage)
- `table=False` ou Pydantic → Schéma (validation)

---

## 🔄 Workflow Complet

### De la Définition à l'Utilisation

```
1. DÉFINIR LE MODÈLE
   ↓
   class User(SQLModel, table=True):
       id: int | None = ...
       email: str = ...

2. CRÉER LA TABLE
   ↓
   init_db()
   → CREATE TABLE user (...)

3. UTILISER DANS L'API
   ↓
   @router.post("/users")
   async def create_user(...):
       user = User(email=...)
       session.add(user)
       session.commit()

4. STOCKÉ EN BASE
   ↓
   SQLite: app.db
   PostgreSQL: base distante
```

---

## 🎯 Exemple Complet : Modèle Article

```python
# app/models/article.py

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class Article(SQLModel, table=True):
    """
    Modèle pour les articles de blog
    """
    
    # Identifiant
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Contenu
    title: str = Field(min_length=1, max_length=200, index=True)
    slug: str = Field(unique=True, index=True)
    content: str
    excerpt: str | None = Field(default=None, max_length=500)
    
    # Métadonnées
    author_id: int = Field(foreign_key="user.id")
    category: str | None = None
    tags: str | None = None  # "python,fastapi,tutorial"
    
    # Visibilité
    is_published: bool = Field(default=False)
    is_featured: bool = Field(default=False)
    
    # SEO
    meta_title: str | None = None
    meta_description: str | None = None
    
    # Statistiques
    views_count: int = Field(default=0, ge=0)
    likes_count: int = Field(default=0, ge=0)
    
    # Dates
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    published_at: datetime | None = None
```

**Table générée :**
```sql
CREATE TABLE article (
    id INTEGER PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    slug VARCHAR UNIQUE NOT NULL,
    content TEXT NOT NULL,
    author_id INTEGER NOT NULL,
    is_published BOOLEAN DEFAULT FALSE,
    views_count INTEGER DEFAULT 0,
    created_at DATETIME NOT NULL,
    ...
    FOREIGN KEY (author_id) REFERENCES user(id)
);
```

---

## 🆘 Problèmes Courants

### Table déjà existe

```python
sqlalchemy.exc.OperationalError: table user already exists
```

**Cause :** `init_db()` appelé plusieurs fois

**Solution :**
```python
# Vérifier avant de créer
from sqlmodel import SQLModel

# Supprimer toutes les tables (ATTENTION : perte de données !)
SQLModel.metadata.drop_all(engine)

# Recréer
SQLModel.metadata.create_all(engine)
```

---

### Contrainte unique violée

```python
sqlalchemy.exc.IntegrityError: UNIQUE constraint failed: user.email
```

**Cause :** Tentative de créer 2 users avec le même email

**Solution :**
```python
from sqlalchemy.exc import IntegrityError

try:
    session.add(user)
    session.commit()
except IntegrityError:
    session.rollback()
    raise HTTPException(409, detail="Email déjà utilisé")
```

---

### Modifier le Modèle après Création

```python
# Si vous modifiez un modèle après que la table existe :

# Option 1 : Migrations (recommandé en production)
# → Utiliser Alembic

# Option 2 : Recréer la table (dev seulement)
# 1. Supprimer le fichier app.db
# 2. Relancer init_db()
```

---

## 📚 Types de Champs Courants

### Texte

```python
# Texte court
name: str = Field(max_length=100)

# Texte long
description: str  # Pas de limite

# Email (validation)
from pydantic import EmailStr
email: EmailStr
```

### Nombres

```python
# Entier
age: int = Field(ge=0, le=150)

# Décimal
price: float = Field(gt=0)

# Grand nombre
population: int
```

### Booléens

```python
is_active: bool = Field(default=True)
is_admin: bool = Field(default=False)
```

### Dates

```python
from datetime import datetime, date

# Date et heure
created_at: datetime = Field(default_factory=datetime.now)

# Date seulement
birth_date: date | None = None
```

### Optionnel

```python
# Peut être None
full_name: str | None = None
description: str | None = None

# Obligatoire
email: str  # Doit être fourni
```

---

## 🔗 Relations (Avancé)

### One-to-Many avec Relationship

```python
from sqlmodel import Relationship

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str
    
    # Relation : Un user a plusieurs articles
    articles: list["Article"] = Relationship(back_populates="author")

class Article(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    user_id: int = Field(foreign_key="user.id")
    
    # Relation : Un article a un auteur
    author: User = Relationship(back_populates="articles")
```

**Usage :**
```python
user = session.get(User, 1)
print(user.articles)  # Liste des articles
# → Pas besoin de requête séparée !
```

---

## 🎯 Ajouter un Nouveau Modèle

### Exemple : Product

```python
# 1. Créer app/models/product.py
from typing import Optional
from sqlmodel import SQLModel, Field

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(min_length=1, max_length=200)
    price: float = Field(gt=0)
    stock: int = Field(default=0, ge=0)
    is_available: bool = Field(default=True)

# 2. Exporter dans app/models/__init__.py
from app.models.product import Product

__all__ = ["User", "Product"]

# 3. Créer la table
from app.db import init_db
init_db()

# 4. Utiliser dans l'API
from app.models.product import Product

@router.post("/products")
async def create_product(name: str, price: float, session: Session = Depends(get_session)):
    product = Product(name=name, price=price)
    session.add(product)
    session.commit()
    return product
```

---

## 🧪 Tester les Modèles

```python
# tests/unit/test_models.py

from app.models.user import User
from app.core.security import get_password_hash

def test_create_user(session):
    """Test la création d'un utilisateur"""
    user = User(
        email="test@example.com",
        full_name="Test User",
        hashed_password=get_password_hash("password123")
    )
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Vérifications
    assert user.id is not None  # ID généré
    assert user.email == "test@example.com"
    assert user.is_active is True  # Valeur par défaut
    assert user.is_superuser is False  # Valeur par défaut
```

---

## 📊 Models vs Schemas

### Différence Fondamentale

| Aspect | Models | Schemas |
|--------|--------|---------|
| **Rôle** | Structure de la **table DB** | Validation des **données entrantes** |
| **Héritage** | `SQLModel, table=True` | `BaseModel` ou `SQLModel` |
| **Dossier** | `app/models/` | `app/schemas/` |
| **Contient** | Tous les champs de la table | Seulement les champs nécessaires |
| **Exemple** | `User` (avec id, created_at, etc.) | `UserCreate` (email, password) |

**Exemple :**

```python
# MODEL (table DB complète)
class User(SQLModel, table=True):
    id: int | None
    email: str
    hashed_password: str
    is_active: bool
    created_at: datetime

# SCHEMA (validation création)
class UserCreate(BaseModel):
    email: EmailStr        # ← Seulement ce que l'utilisateur fournit
    password: str          # ← Pas hashé encore
    # Pas d'id, pas de created_at
```

---

## ✨ Résumé

| Aspect | Valeur |
|--------|--------|
| **Rôle** | 🗃️ Définir la structure des tables DB |
| **Fichiers** | Un fichier = Un modèle = Une table |
| **Héritage** | `SQLModel, table=True` |
| **Champs** | Type hints + Field() |
| **Contraintes** | unique, index, default, ge, le, etc. |
| **Création** | `init_db()` |
| **Usage** | CRUD via Session |

---

## 🎯 Pour Votre Boilerplate

### ✅ Modèle User Inclus

- ✅ Structure complète
- ✅ Champs de sécurité (hashed_password, is_active)
- ✅ Contraintes (email unique, indexé)
- ✅ Valeurs par défaut

### 🚀 Réutilisation

```bash
# Nouveau projet ?
cp app/models/user.py nouveau_projet/app/models/

# Base solide pour commencer !
# Ajoutez vos propres modèles (Product, Order, etc.)
```

---

**🗃️ Les models = Le plan architectural de votre base de données !**

