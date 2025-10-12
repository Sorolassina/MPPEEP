# 🗄️ Dossier DB - Gestion de la Base de Données

## 🤔 C'est Quoi ?

Le dossier `db/` gère la **connexion à la base de données** et fournit les **sessions** pour interagir avec les données.

### 🏗️ Analogie Simple

Imaginez une bibliothèque :

- 📚 **Base de données** = La bibliothèque (stocke tous les livres)
- 🔌 **Engine** = La carte de membre (permet d'entrer)
- 📖 **Session** = Le chariot (pour prendre/déposer des livres)
- 🏢 **db/session.py** = Le guichet d'accueil (donne les chariots)

**Sans session, pas d'accès aux données !**

---

## 📁 Structure

```
app/db/
├── __init__.py       ← Exports (engine, get_session, init_db)
└── session.py        ← Configuration de la connexion DB
```

**Simple mais essentiel !**

---

## 🔧 Composants Principaux

### 1️⃣ `engine` - Le Moteur de Base de Données

**C'est quoi ?**
Le **moteur** est la **connexion principale** à la base de données.

```python
# Création du moteur
engine = create_engine(settings.database_url, echo=settings.DEBUG)
```

**Paramètres :**
- `settings.database_url` → Bascule SQLite/PostgreSQL automatiquement
- `echo=settings.DEBUG` → Affiche les requêtes SQL en mode debug

**Ce qu'il fait :**
```python
DEBUG=True → Affiche toutes les requêtes SQL dans la console
DEBUG=False → Silencieux (production)
```

**Utilisation directe (rare) :**
```python
from app.db import engine
from sqlmodel import Session

# Créer une session manuelle
with Session(engine) as session:
    user = session.get(User, 1)
```

---

### 2️⃣ `init_db()` - Initialiser la Base de Données

**C'est quoi ?**
Fonction qui **crée toutes les tables** définies dans vos modèles.

```python
def init_db() -> None:
    SQLModel.metadata.create_all(engine)
```

**Ce qu'elle fait :**
```
1. Lit tous vos modèles (User, Product, etc.)
2. Génère les requêtes SQL CREATE TABLE
3. Crée les tables dans la base de données
```

**Quand l'utiliser ?**
```python
# Première fois que vous lancez l'application
from app.db import init_db

init_db()
# → Crée les tables user, product, order, etc.
```

**Exemple dans un script :**
```python
# scripts/init_database.py

from app.db import init_db

if __name__ == "__main__":
    print("📋 Création des tables...")
    init_db()
    print("✅ Base de données initialisée !")
```

---

### 3️⃣ `get_session()` - Obtenir une Session

**C'est quoi ?**
Une **session** est comme un **panier** pour interagir avec la base de données.

```python
def get_session():
    with Session(engine) as session:
        yield session
```

**Ce qu'elle fait :**
```
1. Ouvre une connexion à la DB
2. Vous donne accès (yield)
3. Ferme automatiquement la connexion (même si erreur)
```

**Utilisation avec FastAPI (le plus courant) :**
```python
from fastapi import Depends
from sqlmodel import Session
from app.db import get_session

@router.get("/users")
async def get_users(session: Session = Depends(get_session)):
    # session est automatiquement créée et fermée !
    users = session.exec(select(User)).all()
    return users
```

**Utilisation manuelle (scripts) :**
```python
from app.db import engine
from sqlmodel import Session

with Session(engine) as session:
    user = User(email="test@test.com")
    session.add(user)
    session.commit()
    # session fermée automatiquement
```

---

## 🔄 Cycle de Vie d'une Session

### Étape par Étape

```python
# 1. CLIENT fait une requête
GET /api/v1/users

# 2. FASTAPI appelle l'endpoint
@router.get("/users")
async def get_users(session: Session = Depends(get_session)):
    
    # 3. get_session() s'exécute
    # → Ouvre une connexion DB
    # → Crée une Session
    # → Yield (donne la session à l'endpoint)
    
    # 4. ENDPOINT utilise la session
    users = session.exec(select(User)).all()
    
    # 5. ENDPOINT retourne le résultat
    return users
    
    # 6. get_session() ferme la session
    # → Ferme la connexion DB
    # → Libère les ressources

# 7. RÉPONSE envoyée au client
```

**Automatique grâce à `Depends()` !**

---

## 🎯 Opérations de Base

### Créer (Create)

```python
from app.db import get_session
from app.models.user import User

@router.post("/users")
async def create_user(
    email: str,
    full_name: str,
    session: Session = Depends(get_session)
):
    # 1. Créer l'objet
    new_user = User(
        email=email,
        full_name=full_name,
        hashed_password=get_password_hash("default")
    )
    
    # 2. Ajouter à la session
    session.add(new_user)
    
    # 3. Commit (sauvegarder)
    session.commit()
    
    # 4. Refresh (récupérer l'ID auto-généré)
    session.refresh(new_user)
    
    return new_user
```

---

### Lire (Read)

```python
from sqlmodel import select

@router.get("/users")
async def get_users(session: Session = Depends(get_session)):
    # Tous les utilisateurs
    statement = select(User)
    users = session.exec(statement).all()
    return users

@router.get("/users/{user_id}")
async def get_user(user_id: int, session: Session = Depends(get_session)):
    # Un utilisateur par ID
    user = session.get(User, user_id)
    
    if not user:
        raise HTTPException(404, detail="Utilisateur non trouvé")
    
    return user
```

**Avec filtre :**
```python
@router.get("/users/active")
async def get_active_users(session: Session = Depends(get_session)):
    # Filtrer
    statement = select(User).where(User.is_active == True)
    users = session.exec(statement).all()
    return users
```

---

### Modifier (Update)

```python
@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    email: str,
    full_name: str,
    session: Session = Depends(get_session)
):
    # 1. Récupérer
    user = session.get(User, user_id)
    
    if not user:
        raise HTTPException(404, detail="Utilisateur non trouvé")
    
    # 2. Modifier
    user.email = email
    user.full_name = full_name
    
    # 3. Sauvegarder
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return user
```

---

### Supprimer (Delete)

```python
@router.delete("/users/{user_id}")
async def delete_user(user_id: int, session: Session = Depends(get_session)):
    # 1. Récupérer
    user = session.get(User, user_id)
    
    if not user:
        raise HTTPException(404, detail="Utilisateur non trouvé")
    
    # 2. Supprimer
    session.delete(user)
    session.commit()
    
    return {"message": "Utilisateur supprimé"}
```

---

## 🔍 Requêtes Avancées

### Filtrage Multiple

```python
from sqlmodel import select, and_, or_

# AND (tous les critères)
statement = select(User).where(
    and_(
        User.is_active == True,
        User.is_superuser == False
    )
)

# OR (au moins un critère)
statement = select(User).where(
    or_(
        User.email.contains("@gmail.com"),
        User.email.contains("@yahoo.com")
    )
)
```

### Tri

```python
# Croissant
statement = select(User).order_by(User.email)

# Décroissant
statement = select(User).order_by(User.created_at.desc())
```

### Pagination

```python
@router.get("/users")
async def get_users(
    page: int = 1,
    page_size: int = 20,
    session: Session = Depends(get_session)
):
    # Calculer l'offset
    offset = (page - 1) * page_size
    
    # Requête paginée
    statement = select(User).offset(offset).limit(page_size)
    users = session.exec(statement).all()
    
    # Compter le total
    count_statement = select(func.count()).select_from(User)
    total = session.exec(count_statement).one()
    
    return {
        "users": users,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size
    }
```

### Jointures (Relations)

```python
# Si vous avez des relations entre modèles

# Exemple : User a plusieurs Posts
statement = select(User).where(User.id == 1)
user = session.exec(statement).first()

# Accéder aux posts
posts = user.posts  # Si relation définie
```

---

## 🎨 Bonnes Pratiques

### ✅ DO (À Faire)

1. **Toujours utiliser `Depends(get_session)`**
   ```python
   # ✅ Bon
   @router.get("/users")
   async def get_users(session: Session = Depends(get_session)):
       ...
   
   # ❌ Mauvais (session jamais fermée)
   @router.get("/users")
   async def get_users():
       session = Session(engine)
       ...
       # Oups, jamais fermée !
   ```

2. **Commit après modifications**
   ```python
   # ✅ Bon
   user.email = "new@email.com"
   session.add(user)
   session.commit()  # ← Sauvegarde !
   
   # ❌ Mauvais (pas sauvegardé)
   user.email = "new@email.com"
   # Oups, pas de commit !
   ```

3. **Gérer les erreurs**
   ```python
   # ✅ Bon
   user = session.get(User, user_id)
   if not user:
       raise HTTPException(404, detail="Non trouvé")
   
   # ❌ Mauvais (peut crasher)
   user = session.get(User, user_id)
   return user.email  # Si user est None → Crash !
   ```

4. **Refresh après commit pour obtenir l'ID**
   ```python
   # ✅ Bon
   session.add(new_user)
   session.commit()
   session.refresh(new_user)  # ← Récupère l'ID
   print(new_user.id)  # → 1, 2, 3...
   
   # ❌ Mauvais
   session.add(new_user)
   session.commit()
   print(new_user.id)  # → None (pas rafraîchi)
   ```

---

### ❌ DON'T (À Éviter)

1. **❌ Plusieurs commits sans raison**
   ```python
   # ❌ Inefficace
   session.add(user1)
   session.commit()  # Commit 1
   session.add(user2)
   session.commit()  # Commit 2
   
   # ✅ Bon
   session.add(user1)
   session.add(user2)
   session.commit()  # Un seul commit
   ```

2. **❌ Oublier de gérer les erreurs DB**
   ```python
   # ❌ Peut crasher
   from sqlalchemy.exc import IntegrityError
   
   try:
       session.add(user)
       session.commit()
   except IntegrityError:
       # Email dupliqué
       raise HTTPException(409, detail="Email déjà utilisé")
   ```

3. **❌ Requêtes N+1**
   ```python
   # ❌ Mauvais (N requêtes)
   users = session.exec(select(User)).all()
   for user in users:
       posts = session.exec(select(Post).where(Post.user_id == user.id)).all()
       # → 1 requête pour users + N requêtes pour posts
   
   # ✅ Bon (1 requête avec jointure)
   statement = select(User).join(Post)
   results = session.exec(statement).all()
   ```

---

## 🔄 Multi-Environnement

### Bascule Automatique SQLite/PostgreSQL

```python
# Dans session.py
engine = create_engine(settings.database_url, echo=settings.DEBUG)

# settings.database_url retourne :
DEBUG=True  → "sqlite:///./app.db"
DEBUG=False → "postgresql://user:pass@host:5432/db"
```

**Avantage :** Même code, différentes bases !

### Mode Debug

```python
echo=settings.DEBUG

DEBUG=True  → Affiche toutes les requêtes SQL
DEBUG=False → Silencieux
```

**Exemple en mode DEBUG :**
```sql
INFO:sqlalchemy.engine.Engine:
SELECT user.id, user.email, user.full_name
FROM user
WHERE user.id = ?
```

---

## 💡 Exemples Pratiques

### Exemple 1 : Créer un Utilisateur

```python
from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.db import get_session
from app.models.user import User
from app.core.security import get_password_hash

router = APIRouter()

@router.post("/users")
async def create_user(
    email: str,
    password: str,
    full_name: str,
    session: Session = Depends(get_session)
):
    # 1. Créer l'utilisateur
    user = User(
        email=email,
        full_name=full_name,
        hashed_password=get_password_hash(password),
        is_active=True,
        is_superuser=False
    )
    
    # 2. Sauvegarder
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # 3. Retourner
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name
    }
```

---

### Exemple 2 : Recherche avec Filtre

```python
@router.get("/users/search")
async def search_users(
    query: str,
    session: Session = Depends(get_session)
):
    # Recherche dans email ou nom
    statement = select(User).where(
        or_(
            User.email.contains(query),
            User.full_name.contains(query)
        )
    )
    
    users = session.exec(statement).all()
    return users
```

**Usage :**
```bash
# Chercher "john"
curl "http://localhost:8000/api/v1/users/search?query=john"
```

---

### Exemple 3 : Modification avec Validation

```python
@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    email: str,
    full_name: str,
    session: Session = Depends(get_session)
):
    # 1. Vérifier que l'utilisateur existe
    user = session.get(User, user_id)
    
    if not user:
        raise HTTPException(404, detail="Utilisateur non trouvé")
    
    # 2. Vérifier que l'email n'est pas déjà utilisé
    if email != user.email:
        existing = session.exec(
            select(User).where(User.email == email)
        ).first()
        
        if existing:
            raise HTTPException(409, detail="Email déjà utilisé")
    
    # 3. Modifier
    user.email = email
    user.full_name = full_name
    
    # 4. Sauvegarder
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return user
```

---

### Exemple 4 : Transaction avec Rollback

```python
@router.post("/transfer")
async def transfer_money(
    from_user_id: int,
    to_user_id: int,
    amount: float,
    session: Session = Depends(get_session)
):
    try:
        # 1. Débiter le compte source
        from_user = session.get(User, from_user_id)
        from_user.balance -= amount
        
        # 2. Créditer le compte destination
        to_user = session.get(User, to_user_id)
        to_user.balance += amount
        
        # 3. Sauvegarder
        session.add(from_user)
        session.add(to_user)
        session.commit()
        
        return {"message": "Transfert réussi"}
        
    except Exception as e:
        # Rollback automatique (annule tout)
        session.rollback()
        raise HTTPException(500, detail="Transfert échoué")
```

**Avantage :** Si une étape échoue, tout est annulé (atomicité)

---

## 🔌 Connexion à la Base de Données

### SQLite (Développement)

```python
# Automatique quand DEBUG=True
DATABASE_URL = "sqlite:///./app.db"

# Crée un fichier : app.db
# Avantages :
# ✅ Aucune installation
# ✅ Un seul fichier
# ✅ Facile à réinitialiser (supprimer le fichier)

# Limites :
# ⚠️ Une seule écriture à la fois
# ⚠️ Pas adapté pour > 100 users simultanés
```

---

### PostgreSQL (Production)

```python
# Automatique quand DEBUG=False
DATABASE_URL = "postgresql://user:pass@host:5432/dbname"

# Avantages :
# ✅ Écritures multiples simultanées
# ✅ Performances élevées
# ✅ Fonctionnalités avancées

# Nécessite :
# ⚠️ Serveur PostgreSQL installé
# ⚠️ Configuration (user, password, host)
```

---

## 🎯 init_db() - Quand et Comment

### Première Utilisation

```bash
# Option 1 : Via script
python scripts/create_user.py
# → Appelle init_db() automatiquement

# Option 2 : Via code
python -c "from app.db import init_db; init_db()"

# Option 3 : Manuellement
python
>>> from app.db import init_db
>>> init_db()
```

### Réinitialiser la Base

```bash
# SQLite : Supprimer le fichier
rm app.db

# Recréer
python -c "from app.db import init_db; init_db()"
```

### Ajouter un Nouveau Modèle

```python
# 1. Créer le modèle
# app/models/product.py
class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    price: float

# 2. Importer dans __init__.py
# app/models/__init__.py
from app.models.product import Product

# 3. Recréer les tables
from app.db import init_db
init_db()
# → Table 'product' créée !
```

---

## 📊 SQLModel vs SQLAlchemy

### Qu'est-ce que SQLModel ?

**SQLModel = SQLAlchemy + Pydantic**

```python
# SQLModel
class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str

# Avantages :
# ✅ Définition simple
# ✅ Type hints
# ✅ Validation automatique (Pydantic)
# ✅ Compatible FastAPI
```

**Vs SQLAlchemy pur :**
```python
# SQLAlchemy (plus verbeux)
class User(Base):
    __tablename__ = "user"
    
    id = Column(Integer, primary_key=True)
    email = Column(String)
```

**→ SQLModel est plus moderne et simple !**

---

## 🔒 Transactions et Atomicité

### Transaction Automatique

```python
# Avec get_session(), tout est automatique !

@router.post("/create-order")
async def create_order(session: Session = Depends(get_session)):
    # Tout se passe dans une transaction
    order = Order(...)
    session.add(order)
    
    item1 = OrderItem(...)
    session.add(item1)
    
    item2 = OrderItem(...)
    session.add(item2)
    
    session.commit()
    # → Soit TOUT réussit, soit RIEN n'est sauvegardé
```

### Rollback Manuel

```python
try:
    # Opérations
    session.add(user)
    session.commit()
    
except Exception as e:
    session.rollback()  # Annule tout
    raise
```

---

## 🆘 Problèmes Courants

### Erreur : "No such table"

```
sqlalchemy.exc.OperationalError: no such table: user
```

**Cause :** Tables pas créées

**Solution :**
```python
from app.db import init_db
init_db()
```

---

### Erreur : "Database is locked"

```
sqlite3.OperationalError: database is locked
```

**Cause :** Deux écritures simultanées (SQLite)

**Solutions :**
1. Passer à PostgreSQL
2. Réduire les écritures simultanées
3. Augmenter le timeout

```python
engine = create_engine(
    "sqlite:///./app.db",
    connect_args={"timeout": 30}  # 30 secondes
)
```

---

### Erreur : "Session is closed"

```python
# ❌ Erreur
user = session.get(User, 1)
session.close()
print(user.email)  # → Session fermée !

# ✅ Solution : Utiliser avant de fermer
user = session.get(User, 1)
email = user.email  # Récupérer avant
session.close()
print(email)  # OK
```

---

### Erreur : "Unique constraint failed"

```python
sqlalchemy.exc.IntegrityError: UNIQUE constraint failed: user.email
```

**Cause :** Tentative de créer un user avec email existant

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

## 🧪 Tests avec la Base de Données

### Session de Test en Mémoire

```python
# tests/conftest.py

@pytest.fixture(name="session")
def session_fixture():
    # Base SQLite en mémoire pour les tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        yield session
```

**Avantages :**
- ✅ Rapide (en mémoire)
- ✅ Isolé (chaque test repart de zéro)
- ✅ Pas de pollution de la vraie DB

---

## 🔍 Debug des Requêtes SQL

### Activer les Logs SQL

```bash
# Dans .env
DEBUG=true

# Dans la console, vous verrez :
INFO:sqlalchemy.engine.Engine:
BEGIN (implicit)

INFO:sqlalchemy.engine.Engine:
SELECT user.id, user.email
FROM user
WHERE user.id = ?

INFO:sqlalchemy.engine.Engine:
[cached since 0.001s ago] (1,)
```

### Logger Personnalisé

```python
import logging

# Activer les logs SQL
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

---

## 📊 Comparaison Session vs Engine

| Aspect | Engine | Session |
|--------|--------|---------|
| **Rôle** | Connexion à la DB | Panier de transactions |
| **Création** | Une fois au démarrage | À chaque requête |
| **Durée de vie** | Toute l'application | Une requête |
| **Usage** | Créer des sessions | Interagir avec la DB |
| **Fermeture** | Jamais (sauf arrêt app) | Après chaque requête |

---

## 🎯 Architecture Complète

```
Configuration
    ↓
settings.database_url
    ↓
engine = create_engine(url)
    ↓
get_session() → Session(engine)
    ↓
Endpoints utilisent Depends(get_session)
    ↓
Session automatiquement fermée
```

---

## 📚 Fichiers Liés

### Dépendances

```
db/session.py
    ↓ utilise
core/config.py (settings.database_url)
    ↓ bascule selon
DEBUG (True/False)
    ↓ crée
SQLite ou PostgreSQL
```

### Utilisé Par

```
db/session.py
    ↓ fournit
get_session()
    ↓ utilisé dans
api/v1/endpoints/*.py (tous les endpoints)
    ↓ et dans
scripts/*.py (scripts d'admin)
```

---

## 🔄 Workflow Complet : CRUD User

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db import get_session
from app.models.user import User

router = APIRouter()

# CREATE
@router.post("/users")
async def create(email: str, session: Session = Depends(get_session)):
    user = User(email=email)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

# READ ALL
@router.get("/users")
async def read_all(session: Session = Depends(get_session)):
    users = session.exec(select(User)).all()
    return users

# READ ONE
@router.get("/users/{user_id}")
async def read_one(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(404)
    return user

# UPDATE
@router.put("/users/{user_id}")
async def update(
    user_id: int,
    email: str,
    session: Session = Depends(get_session)
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(404)
    
    user.email = email
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

# DELETE
@router.delete("/users/{user_id}")
async def delete(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(404)
    
    session.delete(user)
    session.commit()
    return {"message": "Supprimé"}
```

---

## 📖 Ressources

- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [FastAPI Database](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/)

---

## ✨ Résumé

| Aspect | Valeur |
|--------|--------|
| **Rôle** | 🗄️ Gestion connexion et sessions DB |
| **Fichiers** | `session.py`, `__init__.py` |
| **Composants** | `engine`, `init_db()`, `get_session()` |
| **Multi-env** | SQLite (dev) ↔️ PostgreSQL (prod) |
| **Usage** | `session: Session = Depends(get_session)` |
| **Operations** | Create, Read, Update, Delete (CRUD) |
| **Automatique** | Ouverture/fermeture sessions |

---

**🗄️ Le dossier db = Le pont entre votre code et votre base de données !**

