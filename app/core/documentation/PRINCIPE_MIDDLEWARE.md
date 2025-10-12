# 🛡️ Middlewares et CORS

## 🤔 C'est Quoi un Middleware ?

Un **middleware** est comme un **gardien** qui vérifie chaque visiteur (requête) qui entre et sort de votre application.

### 🏗️ Analogie Simple

Imaginez un immeuble avec plusieurs niveaux de sécurité :

```
Client (Navigateur)
    ↓
🚪 Middleware 1 : Gardien (vérifie l'identité)
    ↓
🚪 Middleware 2 : Détecteur de métaux (sécurité)
    ↓
🚪 Middleware 3 : Enregistrement (journal des visiteurs)
    ↓
🎯 Votre Application (endpoint)
    ↓
🚪 Middleware 3 : Ajoute un badge au visiteur
    ↓
🚪 Middleware 2 : Vérification finale
    ↓
🚪 Middleware 1 : Au revoir
    ↓
Client (Réponse)
```

**Chaque middleware peut :**
- ✅ Laisser passer
- ❌ Bloquer
- 📝 Enregistrer (log)
- ➕ Ajouter des informations
- 🔄 Modifier la requête/réponse

---

## 🎯 CORS - Cross-Origin Resource Sharing

### C'est Quoi ?

**CORS** permet à votre API d'être appelée depuis **d'autres domaines**.

### 🌐 Exemple Concret

```
Votre API : https://api.monapp.com
Votre Frontend : https://www.monapp.com

Sans CORS :
Frontend appelle API → ❌ BLOQUÉ par le navigateur !
"Erreur CORS : Origin not allowed"

Avec CORS configuré :
Frontend appelle API → ✅ AUTORISÉ !
```

### Scénarios

#### Scénario 1 : Application Monolithique

```
Tout sur le même domaine : http://localhost:8000
├── / → Frontend (templates)
└── /api/v1/ → Backend (API)

CORS_ALLOW_ALL = False  ← Pas besoin, même domaine !
```

#### Scénario 2 : Frontend/Backend Séparés

```
Frontend : http://localhost:3000 (React/Vue)
Backend  : http://localhost:8000 (FastAPI)

CORS_ALLOW_ALL = True (dev)  ← Autorise localhost:3000
ALLOWED_HOSTS = ["localhost:3000"] (prod)
```

---

## 🔧 Configuration CORS

### Dans `.env` ou `config.py`

```bash
# Développement (autorise tout)
DEBUG=true
CORS_ALLOW_ALL=true
ALLOWED_HOSTS=localhost,127.0.0.1

# Production (strict)
DEBUG=false
CORS_ALLOW_ALL=false
ALLOWED_HOSTS=monapp.com,www.monapp.com,api.monapp.com
```

### Dans le Code

```python
# app/core/config.py

ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
CORS_ALLOW_ALL: bool = False

# En dev : CORS_ALLOW_ALL=True → Autorise tout
# En prod : CORS_ALLOW_ALL=False → Seulement ALLOWED_HOSTS
```

---

## 🛡️ Middlewares Activés

### 1️⃣ **CORS Middleware** 🌐

**Rôle :** Autorise les appels depuis d'autres domaines

**Configuration :**
```python
allow_origins = ["http://localhost", "https://monapp.com"]
allow_credentials = True  # Autorise les cookies
allow_methods = ["GET", "POST", "PUT", "DELETE"]
allow_headers = ["*"]
```

**Logs :**
```
✅ CORS configuré : ["http://localhost", "https://monapp.com"]
```

---

### 2️⃣ **GZip Middleware** 📦

**Rôle :** Compresse les réponses pour aller plus vite

**Effet :**
```
Sans GZip : 1MB de données → 1MB téléchargé
Avec GZip : 1MB de données → 200KB téléchargé ✅
```

**Configuration :**
```python
minimum_size=1000  # Compresse si > 1KB
```

---

### 3️⃣ **Security Headers Middleware** 🔒

**Rôle :** Ajoute des en-têtes de sécurité

**En-têtes ajoutés :**
```
X-Frame-Options: DENY              ← Empêche l'iframe (clickjacking)
X-Content-Type-Options: nosniff    ← Empêche MIME sniffing
Referrer-Policy: strict-origin     ← Protège la vie privée
```

---

### 4️⃣ **Logging Middleware** 📝

**Rôle :** Enregistre toutes les requêtes

**Format du log :**
```
127.0.0.1 GET /api/v1/users 200 0.123s
192.168.1.1 POST /api/v1/login 303 0.456s
```

**Utile pour :**
- Débogage
- Monitoring
- Détection d'attaques

---

### 5️⃣ **Request ID Middleware** 🎫

**Rôle :** Ajoute un ID unique à chaque requête

**Exemple :**
```
Request ID: 550e8400-e29b-41d4-a716-446655440000

Requête → Traitement → Réponse
  ↓           ↓           ↓
Logs avec le même ID partout !
```

**En-tête ajouté :**
```
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

---

## 🚀 Utilisation

### Activation Automatique

Les middlewares sont activés automatiquement au démarrage :

```python
# app/main.py

from app.core.middleware import setup_middlewares

app = FastAPI(title=settings.APP_NAME)

# ✅ Configuration des middlewares
setup_middlewares(app, settings)
```

### Vérification

```bash
# Lancer l'application
uvicorn app.main:app --reload

# Log au démarrage :
INFO: ✅ Middlewares configurés
```

---

## 🔧 Personnalisation

### Activer/Désactiver dans `.env`

```bash
# .env

# CORS
CORS_ALLOW_ALL=true              # Dev: autorise tout
ALLOWED_HOSTS=localhost,monapp.com  # Prod: liste blanche

# Middlewares
ENABLE_CORS=true
ENABLE_GZIP=true
ENABLE_SECURITY_HEADERS=true
ENABLE_LOGGING=true
ENABLE_REQUEST_ID=true
```

### Modifier la Configuration CORS

```python
# app/core/middleware.py

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,           # Origines autorisées
    allow_credentials=True,          # Autorise les cookies
    allow_methods=["*"],             # Toutes les méthodes
    allow_headers=["*"],             # Tous les headers
    max_age=3600,                    # Cache preflight 1h
)
```

---

## 🧪 Tester CORS

### Test 1 : Vérifier les Headers

```bash
# Requête OPTIONS (preflight)
curl -X OPTIONS http://localhost:8000/api/v1/ping \
  -H "Origin: http://localhost:3000"

# Réponse attendue :
Access-Control-Allow-Origin: http://localhost:3000
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: *
```

### Test 2 : Depuis le Navigateur

```javascript
// Dans la console du navigateur (depuis localhost:3000)

fetch('http://localhost:8000/api/v1/ping')
  .then(res => res.json())
  .then(data => console.log(data))

// Avec CORS configuré : ✅ Fonctionne
// Sans CORS : ❌ Erreur CORS
```

---

## 🎯 Cas d'Usage

### Use Case 1 : SPA (React/Vue) sur Port Différent

```bash
# Frontend
http://localhost:3000  (React)

# Backend
http://localhost:8000  (FastAPI)

# Configuration CORS nécessaire
CORS_ALLOW_ALL=true
# Ou
ALLOWED_HOSTS=localhost:3000
```

### Use Case 2 : Application Monolithique

```bash
# Tout sur le même port
http://localhost:8000
├── / → Templates HTML
└── /api/v1/ → API

# CORS pas vraiment nécessaire
CORS_ALLOW_ALL=false
```

### Use Case 3 : Production avec Domaines Multiples

```bash
# Plusieurs domaines
https://app.monsite.com     (Frontend)
https://api.monsite.com     (API)
https://admin.monsite.com   (Admin)

# Configuration
CORS_ALLOW_ALL=false
ALLOWED_HOSTS=app.monsite.com,api.monsite.com,admin.monsite.com
```

---

## 🆘 Problèmes Courants

### Erreur CORS dans le Navigateur

```
Access to fetch at 'http://localhost:8000/api/v1/users'
from origin 'http://localhost:3000' has been blocked by CORS policy
```

**Solutions :**

1. **En développement :**
   ```python
   # Dans .env
   CORS_ALLOW_ALL=true
   ```

2. **En production :**
   ```python
   # Ajouter l'origine dans ALLOWED_HOSTS
   ALLOWED_HOSTS=localhost:3000,monapp.com
   ```

3. **Vérifier que setup_middlewares est appelé :**
   ```python
   # Dans main.py
   setup_middlewares(app, settings)  # ← Important !
   ```

---

## 📊 Ordre des Middlewares

L'ordre est **important** ! Ils s'exécutent comme des poupées russes :

```
Requête →
  1. CORS (autorise l'origine)
  2. GZip (compression)
  3. Security Headers
  4. Logging
  5. Request ID
  → Votre endpoint
  5. Request ID (ajoute l'ID)
  4. Logging (log la réponse)
  3. Security Headers (ajoute les headers)
  2. GZip (compresse)
  1. CORS (ajoute headers CORS)
← Réponse
```

---

## 🎓 Pour Aller Plus Loin

### Ajouter un Middleware Personnalisé

```python
from starlette.middleware.base import BaseHTTPMiddleware

class MonMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Avant la requête
        print(f"Avant: {request.url}")
        
        # Exécuter la requête
        response = await call_next(request)
        
        # Après la requête
        print(f"Après: {response.status_code}")
        
        return response

# Dans setup_middlewares()
app.add_middleware(MonMiddleware)
```

### Désactiver Temporairement

```python
# Dans setup_middlewares()

# Commenter pour désactiver
# app.add_middleware(LoggingMiddleware)
```

---

## ✅ Résumé

| Middleware | Rôle | Activé |
|------------|------|--------|
| **CORS** | Autorise appels cross-origin | ✅ Oui |
| **GZip** | Compresse les réponses | ✅ Oui |
| **Security Headers** | Ajoute headers sécurité | ✅ Oui |
| **Logging** | Enregistre toutes les requêtes | ✅ Oui |
| **Request ID** | ID unique par requête | ✅ Oui |

### Configuration CORS Actuelle

```python
# Développement (par défaut)
CORS_ALLOW_ALL = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Autorise :
# - http://localhost
# - https://localhost
# - http://127.0.0.1
# - https://127.0.0.1
```

---

**🎉 CORS et middlewares configurés et prêts à l'emploi !**

