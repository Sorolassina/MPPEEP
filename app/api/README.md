# 🌐 Dossier API - Routes et Endpoints

## 🤔 C'est Quoi ?

Le dossier `api/` contient **toutes les routes HTTP** de votre application - c'est par ici que passent **toutes les requêtes** des clients (navigateur, mobile, autre application).

### 🏗️ Analogie Simple

Imaginez un restaurant :

- 🏪 **L'API** = Le menu du restaurant
- 📋 **Endpoints** = Les plats du menu
- 🍽️ **Routes** = Les commandes que vous pouvez passer
- 👨‍🍳 **Backend** = La cuisine (qui prépare)

**Exemple :**
```
Client commande "GET /api/v1/users"
↓
API (menu) → "Ah, vous voulez la liste des utilisateurs"
↓
Backend (cuisine) → Prépare la liste
↓
API → Sert le résultat au client
```

---

## 📁 Structure

```
app/api/
├── __init__.py                 ← Package principal
│
└── v1/                         ← VERSION 1 de l'API
    ├── __init__.py             ← Expose api_router
    ├── router.py               ← Agrège tous les endpoints
    │
    └── endpoints/              ← Routes par domaine
        ├── __init__.py
        ├── auth.py             ← Authentification (login, recovery)
        ├── users.py            ← Gestion utilisateurs (CRUD)
        └── health.py           ← Santé de l'application
```

---

## 🎯 Rôle de Chaque Niveau

### 1️⃣ `api/` - Dossier Principal

**Rôle :** Conteneur de toutes les versions d'API

```
api/
├── v1/     ← Version 1 (actuelle)
├── v2/     ← Version 2 (future)
└── v3/     ← Version 3 (future)
```

**Pourquoi ?** Permet d'avoir plusieurs versions en parallèle

---

### 2️⃣ `v1/` - Version 1

**Rôle :** Groupe toutes les routes de la version 1

```
v1/
├── __init__.py       ← Expose api_router
├── router.py         ← Combine tous les endpoints
└── endpoints/        ← Routes organisées
```

**Avantage :** Faire évoluer l'API sans casser les anciens clients

**Exemple :**
```python
# Version 1 (actuelle)
GET /api/v1/users/1
→ {"id": 1, "email": "user@example.com"}

# Version 2 (future - changement de format)
GET /api/v2/users/1
→ {
    "id": 1,
    "profile": {
        "email": "user@example.com",
        "verified": true
    }
}

# v1 continue de fonctionner pour les anciens clients !
```

---

### 3️⃣ `router.py` - L'Agrégateur

**Rôle :** **Chef d'orchestre** qui rassemble tous les endpoints

```python
# app/api/v1/router.py

from fastapi import APIRouter
from app.api.v1.endpoints import health, users, auth

api_router = APIRouter()

# Agrégation
api_router.include_router(health.router, tags=["health"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(auth.router, tags=["auth"])
```

**Ce qui se passe :**
```
health.router    → /ping
users.router     → /users, /users/{id}, etc.
auth.router      → /login, /forgot-password, etc.

Tous combinés dans api_router !
```

---

### 4️⃣ `endpoints/` - Routes par Domaine

**Rôle :** Organise les routes par **domaine métier**

```
endpoints/
├── auth.py       ← Tout ce qui concerne l'authentification
├── users.py      ← Tout ce qui concerne les utilisateurs
└── health.py     ← Tout ce qui concerne le monitoring
```

**Principe :** Un fichier = Un domaine fonctionnel

---

## 📋 Détail des Endpoints

### `health.py` - Monitoring

**Routes :**
```python
GET /api/v1/ping
→ {"ping": "pong"}
```

**Rôle :**
- Vérifier que l'API est en ligne
- Health check pour monitoring
- Utilisé par les outils de surveillance

**Usage :**
```bash
curl http://localhost:8000/api/v1/ping
```

---

### `auth.py` - Authentification

**Routes :**
```python
# Login
GET  /api/v1/login             → Affiche formulaire
POST /api/v1/login             → Authentifie l'utilisateur

# Récupération mot de passe
GET  /api/v1/forgot-password   → Demande de code
POST /api/v1/forgot-password   → Génère et envoie code
GET  /api/v1/verify-code       → Formulaire de vérification
POST /api/v1/verify-code       → Vérifie le code
GET  /api/v1/reset-password    → Formulaire nouveau mdp
POST /api/v1/reset-password    → Change le mot de passe
```

**Workflow :**
```
1. Utilisateur oublie son mdp
2. GET /forgot-password → Formulaire
3. POST /forgot-password → Code généré
4. GET /verify-code → Saisie du code
5. POST /verify-code → Code vérifié
6. GET /reset-password → Nouveau mdp
7. POST /reset-password → Mdp changé
8. Redirect → /login
```

**Total : 7 routes** pour un workflow complet

---

### `users.py` - Gestion Utilisateurs

**Routes (CRUD) :**
```python
GET    /api/v1/users/          → Liste tous les utilisateurs
POST   /api/v1/users/          → Crée un utilisateur
GET    /api/v1/users/{id}      → Récupère un utilisateur
PUT    /api/v1/users/{id}      → Modifie un utilisateur
DELETE /api/v1/users/{id}      → Supprime un utilisateur
```

**CRUD = Create, Read, Update, Delete**

**Exemple d'utilisation :**
```bash
# Créer un utilisateur
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","full_name":"John Doe"}'

# Récupérer un utilisateur
curl http://localhost:8000/api/v1/users/1
```

---

## 🔄 Flux d'une Requête

### De A à Z

```
1. CLIENT
   ↓
   Requête : GET http://localhost:8000/api/v1/users/123
   
2. FASTAPI (main.py)
   ↓
   app.include_router(api_router, prefix="/api/v1")
   → Ajoute le préfixe /api/v1
   
3. ROUTER (v1/router.py)
   ↓
   api_router.include_router(users.router, prefix="/users")
   → Ajoute le préfixe /users
   
4. ENDPOINT (v1/endpoints/users.py)
   ↓
   @router.get("/{user_id}")
   def get_user(user_id: int):
       # Récupère l'utilisateur en DB
   
5. RÉPONSE
   ↓
   {"id": 123, "email": "user@example.com"}

URL FINALE = /api/v1 + /users + /{user_id}
           = /api/v1/users/123
```

---

## 🎨 Organisation par Domaine

### Principe de Séparation

Chaque endpoint gère **UN domaine fonctionnel** :

| Fichier | Domaine | Routes |
|---------|---------|--------|
| `health.py` | Monitoring | ping, status |
| `auth.py` | Authentification | login, register, recovery |
| `users.py` | Utilisateurs | CRUD users |

**Avantages :**
- 🔍 Facile de trouver une route
- 🧹 Code organisé et propre
- 👥 Plusieurs développeurs sans conflits
- 🧪 Tests isolés par domaine

---

## 💡 Ajouter un Nouvel Endpoint

### Étape 1 : Créer le Fichier

```bash
touch app/api/v1/endpoints/products.py
```

### Étape 2 : Définir les Routes

```python
# app/api/v1/endpoints/products.py

from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.db import get_session

router = APIRouter()

@router.get("/")
async def get_products(session: Session = Depends(get_session)):
    """Liste tous les produits"""
    products = session.exec(select(Product)).all()
    return products

@router.post("/")
async def create_product(product: ProductCreate, session: Session = Depends(get_session)):
    """Crée un produit"""
    db_product = Product.from_orm(product)
    session.add(db_product)
    session.commit()
    return db_product

@router.get("/{product_id}")
async def get_product(product_id: int, session: Session = Depends(get_session)):
    """Récupère un produit"""
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(404, detail="Produit non trouvé")
    return product
```

### Étape 3 : Ajouter au Router

```python
# app/api/v1/router.py

from app.api.v1.endpoints import health, users, auth, products  # ← Ajouter

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(products.router, prefix="/products", tags=["products"])  # ← Ajouter
```

### Étape 4 : Tester

```bash
# Lancer l'app
uvicorn app.main:app --reload

# Tester
curl http://localhost:8000/api/v1/products/

# Voir la doc auto
http://localhost:8000/docs
```

---

## 📚 Tags et Documentation Auto

### Tags dans le Router

```python
api_router.include_router(health.router, tags=["health"])
api_router.include_router(users.router, tags=["users"])
api_router.include_router(auth.router, tags=["auth"])
```

**Résultat dans `/docs` (Swagger) :**

```
📗 health
  └── GET /api/v1/ping

👥 users
  ├── GET    /api/v1/users/
  ├── POST   /api/v1/users/
  ├── GET    /api/v1/users/{id}
  ├── PUT    /api/v1/users/{id}
  └── DELETE /api/v1/users/{id}

🔐 auth
  ├── GET    /api/v1/login
  ├── POST   /api/v1/login
  ├── GET    /api/v1/forgot-password
  └── POST   /api/v1/reset-password
```

**Documentation interactive automatique !** 🎉

---

## 🎯 Préfixes et Chemins

### Comment les Préfixes S'Ajoutent

```python
# 1. Dans main.py
app.include_router(api_router, prefix="/api/v1")

# 2. Dans router.py
api_router.include_router(users.router, prefix="/users")

# 3. Dans users.py
@router.get("/{user_id}")

# RÉSULTAT FINAL :
# /api/v1 + /users + /{user_id}
# = /api/v1/users/{user_id}
```

### Tableau Récapitulatif

| Niveau | Préfixe | Où | Résultat Partiel |
|--------|---------|-----|------------------|
| App | `/api/v1` | `main.py` | `/api/v1` |
| Router | `/users` | `router.py` | `/api/v1/users` |
| Endpoint | `/{user_id}` | `users.py` | `/api/v1/users/{user_id}` |

---

## 🔀 Versioning de l'API

### Pourquoi Versionner ?

**Scénario :** Vous voulez changer le format de réponse

```python
# Version 1 (ancienne)
GET /api/v1/users/1
{
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe"
}

# Version 2 (nouvelle)
GET /api/v2/users/1
{
    "id": 1,
    "email": "user@example.com",
    "profile": {
        "firstName": "John",
        "lastName": "Doe",
        "verified": true
    }
}
```

**Avantage :** Les anciens clients continuent avec v1, les nouveaux utilisent v2 !

### Créer une v2

```bash
# 1. Copier v1
cp -r app/api/v1/ app/api/v2/

# 2. Modifier v2
# app/api/v2/endpoints/users.py
# → Nouveau format de réponse

# 3. Ajouter dans main.py
from app.api.v1 import api_router as api_v1_router
from app.api.v2 import api_router as api_v2_router

app.include_router(api_v1_router, prefix="/api/v1")
app.include_router(api_v2_router, prefix="/api/v2")

# Les deux versions fonctionnent en parallèle !
```

---

## 🛠️ Types de Routes

### Routes GET (Récupération)

```python
@router.get("/users")
async def get_users():
    """Liste tous les utilisateurs"""
    return users

@router.get("/users/{user_id}")
async def get_user(user_id: int):
    """Récupère UN utilisateur"""
    return user
```

**Usage :**
```bash
curl http://localhost:8000/api/v1/users
curl http://localhost:8000/api/v1/users/123
```

---

### Routes POST (Création)

```python
@router.post("/users")
async def create_user(user: UserCreate):
    """Crée un nouvel utilisateur"""
    new_user = User(**user.dict())
    session.add(new_user)
    session.commit()
    return new_user
```

**Usage :**
```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"email":"new@example.com","full_name":"Jane Doe"}'
```

---

### Routes PUT (Modification Complète)

```python
@router.put("/users/{user_id}")
async def update_user(user_id: int, user: UserUpdate):
    """Modifie un utilisateur (tous les champs)"""
    db_user = session.get(User, user_id)
    for key, value in user.dict().items():
        setattr(db_user, key, value)
    session.commit()
    return db_user
```

---

### Routes PATCH (Modification Partielle)

```python
@router.patch("/users/{user_id}")
async def partial_update_user(user_id: int, user: UserPartialUpdate):
    """Modifie un utilisateur (champs spécifiques)"""
    db_user = session.get(User, user_id)
    for key, value in user.dict(exclude_unset=True).items():
        setattr(db_user, key, value)
    session.commit()
    return db_user
```

---

### Routes DELETE (Suppression)

```python
@router.delete("/users/{user_id}")
async def delete_user(user_id: int):
    """Supprime un utilisateur"""
    user = session.get(User, user_id)
    session.delete(user)
    session.commit()
    return {"message": "Utilisateur supprimé"}
```

---

## 🎨 Bonnes Pratiques

### ✅ DO (À Faire)

1. **Un endpoint = Une responsabilité**
   ```python
   # ✅ Bon
   @router.get("/users")
   async def get_users():
       return users
   
   # ❌ Mauvais
   @router.get("/users-and-products-and-stats")
   async def get_everything():
       # Trop de choses différentes !
   ```

2. **Noms clairs et REST**
   ```python
   # ✅ Bon
   GET    /users
   POST   /users
   GET    /users/{id}
   DELETE /users/{id}
   
   # ❌ Mauvais
   GET /get-all-users
   POST /create-new-user
   ```

3. **Utiliser les codes HTTP corrects**
   ```python
   200 OK          → Succès
   201 Created     → Ressource créée
   204 No Content  → Suppression réussie
   400 Bad Request → Données invalides
   404 Not Found   → Ressource inexistante
   500 Server Error → Erreur serveur
   ```

4. **Docstrings explicites**
   ```python
   @router.get("/users/{user_id}")
   async def get_user(user_id: int):
       """
       Récupère un utilisateur par son ID
       
       - **user_id**: ID de l'utilisateur
       - Returns: Données de l'utilisateur
       """
       ...
   ```

---

### ❌ DON'T (À Éviter)

1. **❌ Logique métier dans les routes**
   ```python
   # ❌ Mauvais
   @router.post("/users")
   async def create_user(user: UserCreate):
       # 100 lignes de logique métier...
       # Validation complexe...
       # Calculs...
   
   # ✅ Bon
   @router.post("/users")
   async def create_user(user: UserCreate):
       # Déléguer à un service
       return UserService.create(user)
   ```

2. **❌ Routes sans versioning**
   ```python
   # ❌ Pas de version
   /users
   
   # ✅ Avec version
   /api/v1/users
   ```

3. **❌ Mélanger différents domaines**
   ```python
   # ❌ users.py contient aussi des produits
   @router.get("/products")  # Dans users.py !
   
   # ✅ Créer products.py
   ```

---

## 🌊 Requête Complète Expliquée

### Exemple : Connexion Utilisateur

```
1. NAVIGATEUR
   ↓
   POST http://localhost:8000/api/v1/login
   Body: {"username": "user@example.com", "password": "pass123"}

2. MIDDLEWARES (13 filtres)
   ↓
   ✓ CORS → Origine autorisée ?
   ✓ Request Size → Taille OK ?
   ✓ Logging → Log la requête
   ✓ Request ID → Ajoute ID unique
   
3. FASTAPI ROUTING
   ↓
   /api/v1/login
   → Cherche dans api_router (prefix /api/v1)
   → Trouve auth.router
   → Trouve @router.post("/login")
   
4. ENDPOINT FUNCTION
   ↓
   async def login_post(username, password, session):
       # Validation
       # Vérification DB
       # Création session
       return RedirectResponse("/dashboard")
   
5. MIDDLEWARES (retour)
   ↓
   ✓ Request ID → Ajoute X-Request-ID
   ✓ Logging → Log la réponse
   ✓ GZip → Compresse
   ✓ Security Headers → Ajoute headers
   
6. NAVIGATEUR
   ↓
   Reçoit : 303 Redirect to /dashboard
```

---

## 📊 Convention de Nommage

### Fichiers Endpoints

```
Format : <domaine>.py

Exemples :
✅ auth.py          → Authentification
✅ users.py         → Utilisateurs
✅ products.py      → Produits
✅ orders.py        → Commandes
✅ payments.py      → Paiements
```

### Fonctions

```
Format : <action>_<ressource>

Exemples :
✅ get_users()
✅ create_user()
✅ delete_product()
✅ update_order()
```

### Routes URL

```
Format : /<ressource> ou /<ressource>/{id}

Exemples :
✅ /users
✅ /users/{user_id}
✅ /products/{product_id}/reviews
✅ /orders/{order_id}/items
```

---

## 🔧 Dépendances FastAPI

### Injection de Dépendances

```python
from fastapi import Depends
from sqlmodel import Session
from app.db import get_session

@router.get("/users")
async def get_users(session: Session = Depends(get_session)):
    # session est automatiquement injectée !
    users = session.exec(select(User)).all()
    return users
```

**Avantage :** Pas besoin de créer/fermer la session manuellement

### Dépendances Personnalisées

```python
# Vérifier si l'utilisateur est admin
def require_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_superuser:
        raise HTTPException(403, detail="Accès réservé aux admins")
    return current_user

# Utiliser
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(require_admin)  # ← Vérifie automatiquement
):
    # Seulement les admins arrivent ici
    ...
```

---

## 📈 Évolution de l'API

### Aujourd'hui (MVP)

```
api/v1/
└── endpoints/
    ├── health.py    (1 route)
    ├── auth.py      (7 routes)
    └── users.py     (5 routes)

Total : 13 routes
```

### Dans 3 Mois (Projet Mature)

```
api/v1/
└── endpoints/
    ├── health.py
    ├── auth.py
    ├── users.py
    ├── products.py      (5 routes)
    ├── orders.py        (6 routes)
    ├── payments.py      (4 routes)
    ├── analytics.py     (8 routes)
    └── notifications.py (3 routes)

Total : 47 routes
```

**Grâce à l'organisation, facile d'ajouter !**

---

## 🧪 Tests des Endpoints

### Test Simple

```python
# tests/integration/test_products_api.py

def test_get_products(client: TestClient):
    response = client.get("/api/v1/products/")
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_product(client: TestClient):
    response = client.post(
        "/api/v1/products/",
        json={"name": "Produit Test", "price": 19.99}
    )
    
    assert response.status_code == 201
    assert response.json()["name"] == "Produit Test"
```

---

## 🆘 Problèmes Courants

### Route 404 Not Found

```python
# ❌ Erreur : Route non trouvée
curl http://localhost:8000/api/v1/product
# → 404

# Causes possibles :
# 1. Typo dans l'URL (product au lieu de products)
# 2. Router pas inclus dans main.py
# 3. Préfixe oublié
```

**Solution :**
```bash
# Lister toutes les routes
http://localhost:8000/docs
# ou
http://localhost:8000/openapi.json
```

### Import Circulaire

```python
# ❌ Erreur
# auth.py importe users.py
# users.py importe auth.py
# → ImportError: circular import

# ✅ Solution : Utiliser un service intermédiaire
# ou déplacer le code commun dans utils/
```

---

## ✨ Résumé

| Aspect | Valeur |
|--------|--------|
| **Rôle** | 🌐 Toutes les routes HTTP de l'application |
| **Organisation** | Par version (v1, v2) → Par domaine (auth, users) |
| **Versioning** | Permet plusieurs versions en parallèle |
| **Documentation** | Auto-générée dans `/docs` |
| **Convention** | REST (GET, POST, PUT, DELETE) |
| **Routes actuelles** | 13 routes (health, auth, users) |
| **Extensibilité** | Facile d'ajouter de nouveaux endpoints |

---

## 🎯 Pour Votre Boilerplate

### ✅ Ce qui est Standardisé

- ✅ Structure v1/ (prête pour v2)
- ✅ Organisation par domaine (endpoints/)
- ✅ Router centralisé (router.py)
- ✅ Tags pour documentation auto
- ✅ 3 endpoints de base (health, auth, users)

### 🚀 Réutilisation

```bash
# Nouveau projet ?
cp -r mppeep/app/api/ nouveau_projet/app/api/

# Vous avez :
# - Structure complète
# - Auth prêt à l'emploi
# - CRUD users fonctionnel
# - Health check
# - Versioning

# Il suffit d'ajouter vos propres endpoints !
```

---

**🌐 Le dossier API = Le cœur de communication de votre application avec le monde extérieur !**

