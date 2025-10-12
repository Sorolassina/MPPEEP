# ✅ Dossier Schemas - Validation des Données

## 🤔 C'est Quoi ?

Le dossier `schemas/` contient les **schémas de validation** pour les données qui **entrent et sortent** de votre API.

### 🏗️ Analogie Simple

Imaginez un contrôle de sécurité à l'aéroport :

- ✈️ **API** = L'aéroport
- 🛂 **Schema** = Le contrôle de sécurité (vérifie que tout est en règle)
- 👤 **Données** = Les passagers
- ❌ **Validation** = "Vous ne pouvez pas passer avec ça !"

**Exemple :**
```
Client envoie : {"email": "invalid-email"}
↓
Schema : "❌ Format d'email invalide !"
↓
Réponse : 422 Unprocessable Entity
```

---

## 📁 Structure

```
app/schemas/
├── __init__.py       ← Exports de tous les schémas
└── user.py           ← Schémas User
```

---

## 📋 Schémas User Expliqués

### Code Actuel

```python
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str | None = None

class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
```

### Rôle de Chaque Schema

#### `UserCreate` - Création d'Utilisateur

**Quand :** Client **envoie** des données pour créer un user

```python
POST /api/v1/users
Body: {
    "email": "john@example.com",
    "full_name": "John Doe"
}
```

**Validation automatique :**
```python
email: EmailStr  # ← Vérifie que c'est un email valide
# "john@example.com" → ✅ OK
# "invalid" → ❌ Erreur 422
```

---

#### `UserRead` - Lecture d'Utilisateur

**Quand :** API **retourne** des données au client

```python
GET /api/v1/users/1
Response: {
    "id": 1,
    "email": "john@example.com",
    "full_name": "John Doe"
}
```

**Masque les champs sensibles :**
```python
# ❌ PAS dans UserRead
hashed_password  # ← Secret, jamais exposé !

# ✅ Dans UserRead
id, email, full_name  # ← Seulement les infos publiques
```

---

## 🎯 Différence Models vs Schemas

### Tableau Comparatif

| Aspect | Models | Schemas |
|--------|--------|---------|
| **Dossier** | `app/models/` | `app/schemas/` |
| **Rôle** | Structure de la **table DB** | Validation des **données API** |
| **Héritage** | `SQLModel, table=True` | `BaseModel` (Pydantic) |
| **Contient** | Tous les champs de la table | Seulement champs nécessaires |
| **Usage** | Stockage en DB | Entrée/Sortie API |
| **Exemple** | `User` (complet) | `UserCreate`, `UserRead` |

### Exemple Visuel

```python
# ===== MODEL (Table DB complète) =====
class User(SQLModel, table=True):
    id: int | None                    # Généré auto
    email: str
    full_name: str | None
    hashed_password: str              # ← Hashé, secret
    is_active: bool = True            # ← Géré par l'app
    is_superuser: bool = False        # ← Géré par l'app
    created_at: datetime              # ← Timestamp auto
    updated_at: datetime              # ← Timestamp auto

# ===== SCHEMA Création (Ce que le client envoie) =====
class UserCreate(BaseModel):
    email: EmailStr                   # ← Email validé
    password: str                     # ← En clair (sera hashé)
    full_name: str | None = None      # ← Optionnel
    # Pas d'id, pas de timestamps !

# ===== SCHEMA Lecture (Ce que l'API retourne) =====
class UserRead(BaseModel):
    id: int                           # ← Maintenant présent
    email: EmailStr
    full_name: str | None
    # Pas de hashed_password ! (sécurité)
    # Pas de is_superuser ! (info interne)
```

---

## 💡 Types de Schemas Courants

### 1️⃣ Create (Création)

```python
class UserCreate(BaseModel):
    """Données pour créer un utilisateur"""
    email: EmailStr
    password: str
    full_name: str | None = None
```

**Usage :**
```python
@router.post("/users", response_model=UserRead)
async def create_user(user: UserCreate, session: Session = Depends(get_session)):
    # user est validé automatiquement !
    db_user = User(
        email=user.email,
        hashed_password=get_password_hash(user.password),
        full_name=user.full_name
    )
    session.add(db_user)
    session.commit()
    return db_user
```

---

### 2️⃣ Read (Lecture)

```python
class UserRead(BaseModel):
    """Données retournées par l'API"""
    id: int
    email: EmailStr
    full_name: str | None
    is_active: bool
    
    # Config pour lire depuis le modèle
    class Config:
        from_attributes = True
```

**Usage :**
```python
@router.get("/users/{user_id}", response_model=UserRead)
async def get_user(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    return user
    # → Automatiquement converti en UserRead
```

---

### 3️⃣ Update (Modification)

```python
class UserUpdate(BaseModel):
    """Données pour modifier un utilisateur"""
    email: EmailStr | None = None
    full_name: str | None = None
    # Tous les champs optionnels (modification partielle)
```

**Usage :**
```python
@router.patch("/users/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    session: Session = Depends(get_session)
):
    user = session.get(User, user_id)
    
    # Modifier seulement les champs fournis
    for key, value in user_update.dict(exclude_unset=True).items():
        setattr(user, key, value)
    
    session.add(user)
    session.commit()
    return user
```

---

### 4️⃣ List (Liste avec Pagination)

```python
class UserList(BaseModel):
    """Liste paginée d'utilisateurs"""
    users: list[UserRead]
    total: int
    page: int
    page_size: int
    pages: int
```

**Usage :**
```python
@router.get("/users", response_model=UserList)
async def get_users(page: int = 1, page_size: int = 20):
    # ...
    return UserList(
        users=users,
        total=100,
        page=page,
        page_size=page_size,
        pages=5
    )
```

---

## 🎨 Validation Avancée

### Validateurs Pydantic

```python
from pydantic import BaseModel, EmailStr, validator, field_validator

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    age: int | None = None
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        """Valider la force du mot de passe"""
        if len(v) < 8:
            raise ValueError('Minimum 8 caractères')
        if not any(c.isupper() for c in v):
            raise ValueError('Au moins une majuscule')
        if not any(c.isdigit() for c in v):
            raise ValueError('Au moins un chiffre')
        return v
    
    @field_validator('age')
    @classmethod
    def age_valid(cls, v):
        """Valider l'âge"""
        if v is not None and (v < 0 or v > 150):
            raise ValueError('Âge invalide')
        return v
```

**Résultat :**
```python
# Données invalides
UserCreate(email="test@test.com", password="weak")
# → ValidationError: Minimum 8 caractères

# Données valides
UserCreate(email="test@test.com", password="Strong123")
# → ✅ OK
```

---

## 🔧 Config et Options

### from_attributes (Important !)

```python
class UserRead(BaseModel):
    id: int
    email: str
    
    class Config:
        from_attributes = True  # ← Permet de lire depuis un modèle SQLModel
```

**Sans cette config :**
```python
user = session.get(User, 1)  # Modèle SQLModel
return user
# → ❌ Erreur : Can't convert User to UserRead
```

**Avec cette config :**
```python
user = session.get(User, 1)
return user
# → ✅ Automatiquement converti en UserRead
```

---

## 💡 Exemples Complets

### Exemple 1 : CRUD Complet avec Schemas

```python
# app/schemas/product.py

from pydantic import BaseModel, field_validator

class ProductCreate(BaseModel):
    """Créer un produit"""
    name: str
    price: float
    stock: int = 0
    
    @field_validator('price')
    @classmethod
    def price_positive(cls, v):
        if v <= 0:
            raise ValueError('Le prix doit être positif')
        return v

class ProductUpdate(BaseModel):
    """Modifier un produit"""
    name: str | None = None
    price: float | None = None
    stock: int | None = None

class ProductRead(BaseModel):
    """Lire un produit"""
    id: int
    name: str
    price: float
    stock: int
    is_available: bool
    
    class Config:
        from_attributes = True

# Dans l'API
@router.post("/products", response_model=ProductRead)
async def create_product(product: ProductCreate, session: Session = Depends(get_session)):
    db_product = Product(**product.dict())
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product  # ← Converti en ProductRead
```

---

### Exemple 2 : Schéma avec Relations

```python
class ArticleRead(BaseModel):
    id: int
    title: str
    content: str
    author: UserRead  # ← Schema imbriqué
    
    class Config:
        from_attributes = True

# Réponse :
{
    "id": 1,
    "title": "Mon Article",
    "content": "...",
    "author": {
        "id": 5,
        "email": "author@example.com",
        "full_name": "Author Name"
    }
}
```

---

## 🆘 Problèmes Courants

### Validation échoue

```python
# Erreur
{
    "detail": [
        {
            "loc": ["body", "email"],
            "msg": "value is not a valid email address",
            "type": "value_error.email"
        }
    ]
}
```

**Cause :** Email invalide

**Solution :** Envoyer un email valide ou modifier la validation

---

### from_attributes manquant

```python
# ❌ Erreur
return user  # User (SQLModel) → UserRead (BaseModel)
# TypeError: 'User' object is not subscriptable

# ✅ Solution : Ajouter Config
class UserRead(BaseModel):
    ...
    class Config:
        from_attributes = True
```

---

## 📚 Validation Types Pydantic

```python
from pydantic import (
    EmailStr,      # Email validé
    HttpUrl,       # URL validé
    constr,        # String avec contraintes
    conint,        # Int avec contraintes
    condecimal,    # Decimal avec contraintes
)

class UserCreate(BaseModel):
    email: EmailStr                          # Email valide
    website: HttpUrl | None = None           # URL valide
    username: constr(min_length=3, max_length=50)  # 3-50 caractères
    age: conint(ge=0, le=150)               # 0 <= age <= 150
```

---

## ✨ Résumé

| Aspect | Valeur |
|--------|--------|
| **Rôle** | ✅ Valider les données entrantes/sortantes |
| **Héritage** | `BaseModel` (Pydantic) |
| **Types courants** | Create, Read, Update, List |
| **Validation** | Automatique + Validators personnalisés |
| **Sécurité** | Masque les champs sensibles |
| **Usage** | `response_model=UserRead` |

---

**✅ Les schemas = Les contrôleurs de qualité de vos données !**

