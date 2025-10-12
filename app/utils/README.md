# 🔧 Dossier Utils (Utilitaires)

## 🤔 C'est Quoi ?

Le dossier `utils/` contient des **fonctions helpers** et **outils réutilisables** qui ne rentrent dans aucune autre catégorie (models, schemas, api, etc.).

### 🏗️ Analogie Simple

Imaginez votre application comme une cuisine :

- 🍳 **App** = La cuisine complète
- 🥘 **Models** = Les recettes
- 🔪 **Utils** = Les **ustensiles de cuisine** (couteau, fouet, balance)
  - Utilisés partout
  - Réutilisables
  - Facilitent le travail

---

## 📁 Structure

```
app/utils/
├── __init__.py           ← Exports de tous les utilitaires
├── README.md             ← Ce fichier
├── email.py              ← Envoi d'emails
├── validators.py         ← Validateurs de données
├── helpers.py            ← Fonctions helpers générales
├── constants.py          ← Constantes de l'application
└── decorators.py         ← Décorateurs personnalisés
```

---

## 📚 Fichiers Détaillés

### 📧 `email.py` - Gestion des Emails

**Fonctions disponibles :**

#### `send_email()`
Envoie un email générique

```python
from app.utils import send_email

await send_email(
    to_email="user@example.com",
    subject="Bienvenue !",
    body="Contenu de l'email",
    html_body="<h1>Contenu HTML</h1>"
)
```

#### `send_verification_email()`
Envoie un email avec un code de vérification

```python
from app.utils import send_verification_email

await send_verification_email(
    email="user@example.com",
    verification_code="123456"
)
```

#### `send_password_reset_email()`
Envoie un email de réinitialisation de mot de passe

```python
from app.utils import send_password_reset_email

await send_password_reset_email(
    email="user@example.com",
    reset_code="789012"
)
```

**💡 Note :** Pour l'instant, les emails sont simulés (affichés dans la console). À configurer avec un vrai service SMTP.

---

### ✅ `validators.py` - Validation de Données

**Validateurs disponibles :**

#### `validate_email()`
Valide un email

```python
from app.utils import validate_email

is_valid, error = validate_email("user@example.com")
if not is_valid:
    raise ValueError(error)
```

#### `validate_password_strength()`
Valide la force d'un mot de passe

```python
from app.utils import validate_password_strength

is_valid, error = validate_password_strength("MyP@ss123")
# Vérifie : 8+ caractères, majuscule, minuscule, chiffre
```

#### `validate_username()`
Valide un nom d'utilisateur

```python
from app.utils.validators import validate_username

is_valid, error = validate_username("john_doe", min_length=3)
```

#### `validate_phone_number()`
Valide un numéro de téléphone

```python
from app.utils.validators import validate_phone_number

is_valid, error = validate_phone_number("06 12 34 56 78", country_code="FR")
```

#### `validate_url()`
Valide une URL

```python
from app.utils.validators import validate_url

is_valid, error = validate_url("https://example.com")
```

---

### 🛠️ `helpers.py` - Fonctions Helpers

**Fonctions disponibles :**

#### `generate_random_string()`
Génère une chaîne aléatoire sécurisée

```python
from app.utils import generate_random_string

token = generate_random_string(32)
# → "aB3dE5fG7hI9jK1lM3nO5pQ7rS9tU1vW3"

api_key = generate_random_string(64, include_special=True)
# → "aB3!dE5@fG7#hI9$jK1%lM3^nO5&pQ7*rS9"
```

#### `generate_verification_code()`
Génère un code numérique de vérification

```python
from app.utils.helpers import generate_verification_code

code = generate_verification_code(6)
# → "123456"
```

#### `slugify()`
Convertit un texte en slug URL-friendly

```python
from app.utils import slugify

slug = slugify("Mon Article 2024!")
# → "mon-article-2024"

slug = slugify("Événement à Paris")
# → "evenement-a-paris"
```

#### `get_client_ip()`
Récupère l'IP du client (avec support proxy)

```python
from app.utils import get_client_ip

@router.get("/")
async def index(request: Request):
    ip = get_client_ip(request)
    logger.info(f"Requête depuis {ip}")
```

#### `format_file_size()`
Formate une taille de fichier

```python
from app.utils.helpers import format_file_size

size = format_file_size(1536)
# → "1.5 KB"

size = format_file_size(1048576)
# → "1.0 MB"
```

#### `time_ago()`
Format "il y a X" pour une date

```python
from app.utils.helpers import time_ago
from datetime import datetime, timedelta

dt = datetime.now() - timedelta(minutes=5)
text = time_ago(dt)
# → "il y a 5 minutes"
```

#### `parse_bool()`
Parse intelligemment un booléen

```python
from app.utils.helpers import parse_bool

parse_bool("true")    # → True
parse_bool("1")       # → True
parse_bool("yes")     # → True
parse_bool("false")   # → False
```

#### `safe_int()`
Convertit en int de manière sûre

```python
from app.utils.helpers import safe_int

safe_int("123")       # → 123
safe_int("abc")       # → 0
safe_int("abc", -1)   # → -1
```

---

### 📋 `constants.py` - Constantes

**Catégories de constantes :**

#### Authentification

```python
from app.utils.constants import (
    PASSWORD_MIN_LENGTH,
    MAX_LOGIN_ATTEMPTS,
    SESSION_TIMEOUT_MINUTES
)

if len(password) < PASSWORD_MIN_LENGTH:
    raise ValueError(f"Minimum {PASSWORD_MIN_LENGTH} caractères")
```

#### Pagination

```python
from app.utils.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

@router.get("/users")
def get_users(page_size: int = DEFAULT_PAGE_SIZE):
    if page_size > MAX_PAGE_SIZE:
        page_size = MAX_PAGE_SIZE
```

#### Fichiers

```python
from app.utils.constants import (
    MAX_FILE_SIZE_MB,
    ALLOWED_IMAGE_EXTENSIONS
)

if file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
    raise ValueError("Fichier trop volumineux")
```

#### Messages

```python
from app.utils.constants import MSG_LOGIN_SUCCESS, MSG_LOGIN_FAILED

if authenticated:
    return {"message": MSG_LOGIN_SUCCESS}
else:
    return {"message": MSG_LOGIN_FAILED}
```

#### Rôles et Statuts

```python
from app.utils.constants import ROLE_ADMIN, STATUS_ACTIVE

if user.role == ROLE_ADMIN and user.status == STATUS_ACTIVE:
    # Autoriser l'accès
```

---

### 🎨 `decorators.py` - Décorateurs

**Décorateurs disponibles :**

#### `@log_execution_time`
Log le temps d'exécution

```python
from app.utils.decorators import log_execution_time

@log_execution_time
async def slow_operation():
    # Code
    
# Log: ⏱️  slow_operation exécuté en 1.234s
```

#### `@require_role()`
Vérifie le rôle de l'utilisateur

```python
from app.utils.decorators import require_role

@require_role("admin")
async def admin_only():
    # Accessible seulement aux admins
```

#### `@cache_result()`
Met en cache le résultat

```python
from app.utils.decorators import cache_result

@cache_result(expiry_seconds=600)
async def expensive_query():
    # Résultat mis en cache 10 minutes
```

#### `@rate_limit()`
Limite le nombre d'appels

```python
from app.utils.decorators import rate_limit

@rate_limit(max_calls=5, window_seconds=60)
async def sensitive_endpoint(request: Request):
    # Max 5 appels par minute par IP
```

#### `@retry()`
Réessaie en cas d'échec

```python
from app.utils.decorators import retry

@retry(max_attempts=3, delay_seconds=2)
async def unstable_api():
    # Réessaie 3 fois avec 2s entre chaque
```

---

## 🎯 Cas d'Usage Pratiques

### Scénario 1 : Créer un Utilisateur avec Validation

```python
from app.utils import validate_email, validate_password_strength
from app.utils.constants import MSG_EMAIL_ALREADY_EXISTS

@router.post("/register")
async def register(email: str, password: str):
    # Valider l'email
    is_valid, error = validate_email(email)
    if not is_valid:
        raise HTTPException(400, detail=error)
    
    # Valider le mot de passe
    is_valid, error = validate_password_strength(password)
    if not is_valid:
        raise HTTPException(400, detail=error)
    
    # Créer l'utilisateur
    # ...
```

### Scénario 2 : Envoyer un Code de Vérification

```python
from app.utils.helpers import generate_verification_code
from app.utils import send_verification_email

# Générer le code
code = generate_verification_code(6)  # "123456"

# Envoyer par email
await send_verification_email(user.email, code)

# Stocker le code
# ...
```

### Scénario 3 : Logger et Optimiser

```python
from app.utils.decorators import log_execution_time, cache_result

@log_execution_time
@cache_result(expiry_seconds=300)
async def get_statistics():
    # Calcul complexe
    # Résultat mis en cache 5 minutes
    # Temps d'exécution loggé
```

### Scénario 4 : Protéger un Endpoint

```python
from app.utils.decorators import rate_limit, require_role

@rate_limit(max_calls=10, window_seconds=60)
@require_role("admin")
async def admin_sensitive_operation(request: Request):
    # Seulement admins
    # Max 10 appels/minute
```

---

## 📊 Différence avec les Autres Dossiers

| Dossier | Contenu | Exemple |
|---------|---------|---------|
| `models/` | Structure des données | `class User(SQLModel)` |
| `schemas/` | Validation Pydantic | `class UserCreate(BaseModel)` |
| `api/` | Routes HTTP | `@router.get("/users")` |
| `core/` | Config, sécurité | `settings`, `get_password_hash()` |
| **`utils/`** | **Fonctions helpers** | **`slugify()`, `send_email()`** |

**Règle :** Si une fonction est **générique** et **réutilisable**, elle va dans `utils/`.

---

## 🎯 Quand Ajouter un Utilitaire ?

### ✅ Ajouter dans utils/ si...

- ✅ La fonction est utilisée dans **plusieurs endroits**
- ✅ La fonction est **générique** (pas de logique métier)
- ✅ La fonction est **réutilisable** dans d'autres projets

**Exemples :**
- `slugify()` - Utilisé partout
- `format_file_size()` - Générique
- `generate_random_string()` - Réutilisable

### ❌ NE PAS mettre dans utils/ si...

- ❌ Logique métier spécifique
- ❌ Manipulation de modèles DB
- ❌ Routes HTTP

**Exemples (à mettre ailleurs) :**
- `create_user()` → dans `services/`
- `calculate_invoice()` → dans `services/`
- `@router.get()` → dans `api/`

---

## 🔄 Utilisation dans le Projet

### Import Simple

```python
# Import depuis __init__.py (recommandé)
from app.utils import send_email, slugify, validate_email

# Ou import direct
from app.utils.helpers import slugify
from app.utils.validators import validate_email
```

### Dans un Endpoint

```python
from fastapi import APIRouter
from app.utils import generate_random_string, send_email
from app.utils.decorators import rate_limit

router = APIRouter()

@router.post("/contact")
@rate_limit(max_calls=3, window_seconds=60)
async def contact(request: Request, email: str, message: str):
    # Générer un ID de ticket
    ticket_id = generate_random_string(16)
    
    # Envoyer l'email
    await send_email(
        to_email=email,
        subject=f"Ticket #{ticket_id}",
        body=message
    )
    
    return {"ticket_id": ticket_id}
```

### Dans un Modèle

```python
from sqlmodel import SQLModel, Field
from app.utils.helpers import slugify

class Article(SQLModel, table=True):
    title: str
    slug: str = ""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.slug and self.title:
            self.slug = slugify(self.title)
```

---

## 🎨 Bonnes Pratiques

### ✅ DO (À Faire)

1. **Fonctions pures autant que possible**
   ```python
   # ✅ Pure : Même entrée = Même sortie
   def slugify(text: str) -> str:
       return text.lower().replace(" ", "-")
   ```

2. **Documentation claire**
   ```python
   def ma_fonction(param: str) -> str:
       """
       Description de la fonction
       
       Args:
           param: Description du paramètre
       
       Returns:
           Description du retour
           
       Example:
           ma_fonction("test")
           → "résultat"
       """
   ```

3. **Type hints**
   ```python
   # ✅ Bon
   def format_size(size: int) -> str:
       ...
   
   # ❌ Mauvais
   def format_size(size):
       ...
   ```

4. **Gestion des erreurs**
   ```python
   def safe_convert(value: str, default: int = 0) -> int:
       try:
           return int(value)
       except ValueError:
           return default
   ```

### ❌ DON'T (À Éviter)

1. **❌ Logique métier complexe**
   ```python
   # ❌ Trop spécifique, mettre dans services/
   def calculate_user_subscription_price(user, plan):
       ...
   ```

2. **❌ Dépendances lourdes**
   ```python
   # ❌ Éviter les dépendances à la DB dans utils
   def get_all_users():
       from app.db.session import Session
       # Non ! Mettre dans services/
   ```

3. **❌ Effets de bord**
   ```python
   # ❌ Éviter les modifications globales
   global_var = []
   def add_to_global(item):
       global_var.append(item)  # Mauvais !
   ```

---

## 📊 Imports Recommandés

### Dans __init__.py

```python
from app.utils import (
    # Email
    send_email,
    send_verification_email,
    
    # Validation
    validate_email,
    validate_password_strength,
    
    # Helpers
    slugify,
    generate_random_string,
    
    # Constants
    PASSWORD_MIN_LENGTH,
    MAX_LOGIN_ATTEMPTS,
)
```

**Avantage :** Import simplifié partout dans le projet

---

## 🧪 Tests des Utilitaires

Créer des tests pour chaque utilitaire :

```python
# tests/unit/test_utils_helpers.py

def test_slugify():
    assert slugify("Mon Article") == "mon-article"
    assert slugify("Événement à Paris") == "evenement-a-paris"

def test_generate_random_string():
    s1 = generate_random_string(32)
    s2 = generate_random_string(32)
    
    assert len(s1) == 32
    assert len(s2) == 32
    assert s1 != s2  # Aléatoires différents
```

---

## 🔍 Structure Complète

```python
app/
├── api/          ← Routes HTTP
├── core/         ← Config, sécurité
├── db/           ← Database
├── models/       ← Modèles ORM
├── schemas/      ← Schémas Pydantic
├── templates/    ← Templates HTML
├── static/       ← CSS, JS, images
│
├── utils/        ← 🔧 UTILITAIRES (vous êtes ici)
│   ├── email.py
│   ├── validators.py
│   ├── helpers.py
│   ├── constants.py
│   └── decorators.py
│
└── services/     ← Logique métier (à créer)
```

---

## 🎯 Utilitaires à Ajouter (Suggestions)

### Actuels ✅

- [x] Email (send_email, templates)
- [x] Validators (email, password, phone, URL)
- [x] Helpers (random, slugify, IP, dates)
- [x] Constants (auth, pagination, messages)
- [x] Decorators (log, cache, rate-limit, retry)

### Futurs 💡

- [ ] `utils/jwt.py` - Gestion des tokens JWT
- [ ] `utils/pagination.py` - Pagination des résultats
- [ ] `utils/files.py` - Upload et gestion de fichiers
- [ ] `utils/encryption.py` - Chiffrement/déchiffrement
- [ ] `utils/notifications.py` - Système de notifications
- [ ] `utils/exporters.py` - Export CSV, Excel, PDF

---

## 📚 Ressources

- [Python Best Practices](https://docs.python-guide.org/writing/structure/)
- [FastAPI Project Structure](https://fastapi.tiangolo.com/tutorial/)
- [Clean Code Principles](https://github.com/zedr/clean-code-python)

---

## ✨ Résumé

| Aspect | Valeur |
|--------|--------|
| **Rôle** | 🔧 Boîte à outils de fonctions réutilisables |
| **Contenu** | Helpers, validateurs, constantes, décorateurs |
| **Usage** | Partout dans l'application |
| **Tests** | Unitaires (très important !) |
| **Import** | `from app.utils import ...` |

**💡 Le dossier utils = La boîte à outils de votre projet. Des fonctions simples, testées et réutilisables !**

