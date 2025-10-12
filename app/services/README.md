# 🔧 Services - Logique Métier

## 🎯 Qu'est-ce qu'un Service ?

Un **service** est une classe qui contient la **logique métier** de l'application. Il encapsule les opérations complexes et peut être réutilisé depuis :

- ✅ Les endpoints API (`app/api/`)
- ✅ Les scripts d'administration (`scripts/`)
- ✅ Les tests (`tests/`)
- ✅ D'autres services

---

## 🏗️ Architecture : Scripts vs Services

### ❌ Avant (Sans Services)

```
scripts/create_user.py
├── Logique de création d'utilisateur
└── Interface CLI

app/api/v1/endpoints/auth.py
└── Dupliquer la logique d'authentification ❌

scripts/init_db.py
└── Dupliquer la logique de création d'admin ❌
```

**Problème :** Code dupliqué, difficile à maintenir

---

### ✅ Après (Avec Services)

```
app/services/user_service.py
└── Logique métier centralisée ✅
    ├── create_user()
    ├── authenticate()
    ├── update_password()
    └── get_by_email()

scripts/create_user.py
└── Appelle UserService.create_user() ✅

app/api/v1/endpoints/auth.py
└── Appelle UserService.authenticate() ✅

scripts/init_db.py
└── Appelle UserService.create_user() ✅
```

**Avantage :** Code unique, réutilisable, testable

---

## 📁 Services Disponibles

### `UserService`

**Fichier :** `app/services/user_service.py`

**Rôle :** Gestion des utilisateurs (CRUD, authentification, etc.)

**Méthodes :**

#### `get_by_email(session, email)` → User | None
Récupère un utilisateur par son email

```python
from app.services.user_service import UserService
from app.db.session import Session

with Session(engine) as session:
    user = UserService.get_by_email(session, "user@example.com")
    if user:
        print(f"Utilisateur trouvé: {user.full_name}")
```

---

#### `get_by_id(session, user_id)` → User | None
Récupère un utilisateur par son ID

```python
user = UserService.get_by_id(session, 1)
if user:
    print(f"User ID 1: {user.email}")
```

---

#### `create_user(session, email, full_name, password, is_active, is_superuser)` → User | None
Crée un nouvel utilisateur

```python
user = UserService.create_user(
    session=session,
    email="john@example.com",
    full_name="John Doe",
    password="secure_password",
    is_active=True,
    is_superuser=False
)

if user:
    print(f"✅ Utilisateur créé: {user.email}")
else:
    print("❌ Email déjà utilisé")
```

---

#### `authenticate(session, email, password)` → User | None
Authentifie un utilisateur

```python
user = UserService.authenticate(session, "user@example.com", "password123")

if user:
    print(f"✅ Authentification réussie: {user.email}")
else:
    print("❌ Email ou mot de passe incorrect")
```

---

#### `update_password(session, user, new_password)` → bool
Met à jour le mot de passe d'un utilisateur

```python
user = UserService.get_by_email(session, "user@example.com")
success = UserService.update_password(session, user, "new_secure_password")

if success:
    print("✅ Mot de passe mis à jour")
else:
    print("❌ Erreur lors de la mise à jour")
```

---

#### `count_users(session)` → int
Compte le nombre total d'utilisateurs

```python
total = UserService.count_users(session)
print(f"Nombre d'utilisateurs: {total}")
```

---

#### `list_all(session)` → list[User]
Liste tous les utilisateurs

```python
users = UserService.list_all(session)
for user in users:
    print(f"- {user.email} ({'Admin' if user.is_superuser else 'User'})")
```

---

## 💡 Pourquoi Utiliser des Services ?

### 1. **Réutilisabilité**

Au lieu de dupliquer le code :

```python
# ❌ Sans service (code dupliqué)

# Dans auth.py
statement = select(User).where(User.email == email)
user = session.exec(statement).first()

# Dans users.py
statement = select(User).where(User.email == email)  # Dupliqué !
user = session.exec(statement).first()

# Dans create_user.py
statement = select(User).where(User.email == email)  # Re-dupliqué !
user = session.exec(statement).first()
```

```python
# ✅ Avec service (une seule implémentation)

user = UserService.get_by_email(session, email)
# → Utilisable partout, code unique
```

---

### 2. **Testabilité**

```python
# Test du service (isolé)
def test_create_user():
    user = UserService.create_user(session, "test@test.com", "Test", "pass")
    assert user is not None
    assert user.email == "test@test.com"
```

---

### 3. **Maintenabilité**

Si vous devez changer la logique :

```python
# ✅ Une seule modification dans le service
# → Tous les endroits qui utilisent le service bénéficient du changement

# ❌ Sans service : modifier dans 5 fichiers différents
```

---

### 4. **Séparation des Responsabilités**

```
Scripts        → Interface CLI (argparse, print)
Services       → Logique métier (création, validation)
Endpoints      → HTTP (routing, responses)
Models         → Structure des données
```

Chaque couche a **une seule responsabilité**.

---

## 🎓 Bonnes Pratiques

### ✅ DO

```python
# Dans un endpoint
@router.post("/users")
def create_user_endpoint(user_data: UserCreate, session: Session):
    user = UserService.create_user(session, **user_data.dict())
    return {"user": user}

# Dans un script
def main():
    with Session(engine) as session:
        UserService.create_user(session, "admin@app.com", "Admin", "pass")

# Dans un test
def test_user_creation():
    user = UserService.create_user(test_session, "test@test.com", ...)
    assert user is not None
```

---

### ❌ DON'T

```python
# Ne pas dupliquer la logique
@router.post("/users")
def create_user_endpoint(...):
    user = User(email=..., hashed_password=get_password_hash(...))  # ❌
    session.add(user)  # Logique en dur
    session.commit()
```

---

## 📊 Comparaison

| Aspect | Sans Service | Avec Service |
|--------|--------------|--------------|
| **Réutilisabilité** | ❌ Code dupliqué | ✅ Code unique |
| **Maintenance** | ❌ Modifier partout | ✅ Modifier 1 fois |
| **Tests** | ❌ Difficile | ✅ Facile |
| **Lisibilité** | ❌ Code verbeux | ✅ Code concis |
| **Bugs** | ❌ Risque élevé | ✅ Risque faible |

---

## 🚀 Utilisation

### Dans un Endpoint API

```python
from fastapi import Depends
from app.services.user_service import UserService
from app.db.session import get_session

@router.post("/login")
def login(email: str, password: str, session: Session = Depends(get_session)):
    user = UserService.authenticate(session, email, password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {"user_id": user.id, "email": user.email}
```

---

### Dans un Script

```python
from app.services.user_service import UserService
from app.db.session import Session, engine

with Session(engine) as session:
    user = UserService.create_user(
        session, "admin@app.com", "Admin", "password", is_superuser=True
    )
    print(f"Admin créé: {user.email}")
```

---

### Dans un Test

```python
def test_authenticate_valid_user(test_session):
    # Créer un user de test
    UserService.create_user(
        test_session, "test@test.com", "Test", "password123"
    )
    
    # Tester l'authentification
    user = UserService.authenticate(test_session, "test@test.com", "password123")
    assert user is not None
    assert user.email == "test@test.com"
```

---

### `SessionService`

**Fichier :** `app/services/session_service.py`

**Rôle :** Gestion des sessions utilisateur (multi-device, tracking, expiration)

**Méthodes principales :**

#### `create_session(db_session, user, request, remember_me)` → UserSession
Crée une nouvelle session pour l'utilisateur

```python
from app.services.session_service import SessionService

user_session = SessionService.create_session(
    db_session=session,
    user=user,
    request=request,
    remember_me=True  # 30 jours au lieu de 7
)
```

---

#### `get_user_from_session(db_session, session_token)` → User | None
Récupère l'utilisateur associé à une session

```python
session_token = request.cookies.get("mppeep_session")
user = SessionService.get_user_from_session(session, session_token)

if user:
    print(f"✅ Utilisateur authentifié: {user.email}")
```

---

#### `delete_session(db_session, session_token)` → bool
Déconnecte une session spécifique

```python
success = SessionService.delete_session(session, session_token)
```

---

#### `get_active_sessions(db_session, user_id)` → list[UserSession]
Liste toutes les sessions actives d'un utilisateur

```python
sessions = SessionService.get_active_sessions(session, user.id)
for s in sessions:
    print(f"- {s.device_info} (IP: {s.ip_address})")
```

---

#### `delete_all_user_sessions(db_session, user_id)` → int
Déconnecte toutes les sessions d'un utilisateur

```python
count = SessionService.delete_all_user_sessions(session, user.id)
print(f"✅ {count} session(s) déconnectée(s)")
```

---

#### `set_session_cookie(response, session_token, max_age)` 
Définit le cookie de session dans la réponse

```python
from fastapi import Response

response = Response()
SessionService.set_session_cookie(
    response=response,
    session_token=user_session.session_token,
    max_age=30 * 24 * 60 * 60  # 30 jours
)
```

---

**Fonctionnalités :**
- ✅ Sessions multi-device (plusieurs connexions simultanées)
- ✅ Tracking device info (navigateur, OS)
- ✅ Expiration configurable (7 ou 30 jours avec "remember me")
- ✅ Déconnexion sélective ou globale
- ✅ Nettoyage automatique des sessions expirées
- ✅ Sécurité : cookies HttpOnly, SameSite

---

## 🎯 Prochains Services

Vous pouvez créer d'autres services selon vos besoins :

```
app/services/
├── __init__.py
├── user_service.py        ← ✅ Créé
├── session_service.py     ← ✅ Créé
├── email_service.py       ← Envoi d'emails
├── notification_service.py ← Notifications
└── storage_service.py     ← Upload de fichiers
```

---

## ✨ Résumé

**Services = Logique Métier Réutilisable**

- ✅ Une seule source de vérité
- ✅ Code testable et maintenable
- ✅ Utilisable depuis API, scripts, tests
- ✅ Séparation claire des responsabilités

**Maintenant votre code suit les bonnes pratiques d'architecture ! 🎉**

