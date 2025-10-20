# 📘 Parcours d'une Requête Client - De la Demande à la Réponse

## 🎯 Vue d'ensemble

Ce document détaille le **parcours complet d'une requête HTTP** depuis le navigateur du client jusqu'à la réponse renvoyée par le serveur, en passant par tous les composants de l'architecture MPPEEP.

---

## 📋 EXEMPLE CONCRET

Nous allons suivre le parcours de cette requête :

**Action utilisateur** : L'utilisateur clique sur "Nouvelle Demande RH" après s'être connecté.

**Requête HTTP** :
```http
GET /api/v1/rh/demandes/new HTTP/1.1
Host: localhost:9000
Cookie: access_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
User-Agent: Mozilla/5.0...
Accept: text/html,application/xhtml+xml...
```

---

## 🔄 PHASE 1 : RÉCEPTION DE LA REQUÊTE

### Étape 1.1 : Uvicorn reçoit la connexion TCP

```
Navigateur (Chrome)  →  TCP/IP  →  Uvicorn (Port 9000)
```

**Ce qui se passe** :
1. Le navigateur établit une connexion TCP sur `localhost:9000`
2. Uvicorn accepte la connexion
3. Uvicorn lit les octets de la requête HTTP
4. Uvicorn parse les headers, la méthode, le chemin, etc.

**Log** :
```
📥 GET /api/v1/rh/demandes/new | Request-ID: xY7k9mN2
```

### Étape 1.2 : Création de l'objet Request

Uvicorn crée un objet `Request` FastAPI :

```python
request = Request(
    scope={
        "type": "http",
        "method": "GET",
        "path": "/api/v1/rh/demandes/new",
        "query_string": b"",
        "headers": [
            (b"host", b"localhost:9000"),
            (b"cookie", b"access_token=eyJ..."),
            (b"user-agent", b"Mozilla/5.0..."),
            ...
        ],
        "server": ("127.0.0.1", 9000),
        "client": ("127.0.0.1", 54321),
    }
)
```

---

## 🛡️ PHASE 2 : MIDDLEWARES (Traitement pré-route)

### Middleware 1 : Logging

**Fichier** : `app/main.py`

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    request_id = secrets.token_urlsafe(8)
    
    # Log de la requête entrante
    logger.info(f"📥 {request.method} {request.url.path} | Request-ID: {request_id}")
    
    # Passer au middleware suivant (ou à la route)
    response = await call_next(request)
    
    # Log de la réponse sortante
    duration = time.time() - start_time
    logger.info(
        f"📤 {request.method} {request.url.path} | "
        f"Status: {response.status_code} | "
        f"Duration: {duration:.3f}s | "
        f"Request-ID: {request_id}"
    )
    
    return response
```

**Résultat** : Request-ID généré = `xY7k9mN2`

### Middleware 2 : CORS (si activé)

```python
# Vérifie les headers Origin, Access-Control-Allow-*
# Ajoute les headers CORS à la réponse
```

---

## 🗺️ PHASE 3 : ROUTAGE

### Étape 3.1 : FastAPI cherche la route correspondante

FastAPI parcourt les routes enregistrées :

```python
routes = [
    Route("/", root),
    Route("/api/v1/auth/login", login_page),
    Route("/api/v1/auth/logout", logout),
    Route("/api/v1/", accueil),
    Route("/api/v1/rh/", rh_home),
    Route("/api/v1/rh/demandes/new", rh_new_demande),  # ✅ MATCH !
    ...
]
```

**Match trouvé** : `rh_new_demande` dans `app/api/v1/endpoints/rh.py`

### Étape 3.2 : Extraction des dépendances

**Signature de la fonction** :

```python
@router.get("/demandes/new", response_class=HTMLResponse, name="rh_new_demande")
def rh_new_demande(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
```

**Dépendances à résoudre** :
1. `request` → Fourni automatiquement par FastAPI
2. `session` → Dépend de `get_session()`
3. `current_user` → Dépend de `get_current_user()`

---

## 🔐 PHASE 4 : RÉSOLUTION DES DÉPENDANCES

### Dépendance 1 : `get_session()`

**Fichier** : `app/db/session.py`

```python
def get_session() -> Session:
    """Crée une session de base de données"""
    with Session(engine) as session:
        yield session
```

**Résultat** : Création d'une session SQLite connectée à `mppeep.db`

### Dépendance 2 : `get_current_user()`

**Fichier** : `app/api/v1/endpoints/auth.py`

```python
def get_current_user(
    request: Request,
    session: Session = Depends(get_session)
) -> User:
    """Récupère l'utilisateur connecté depuis le token JWT"""
    
    # 1. Récupérer le cookie
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Non authentifié"
        )
    
    # 2. Décoder le token JWT
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        user_id: int = payload.get("sub")
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Token invalide"
        )
    
    # 3. Récupérer l'utilisateur en base
    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Utilisateur introuvable ou inactif"
        )
    
    return user
```

**Étapes détaillées** :

1. **Extraction du cookie** :
```python
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzM1MDg5NjAwfQ..."
```

2. **Décodage JWT** :
```python
payload = {
    "sub": "1",  # ID de l'utilisateur
    "exp": 1735089600  # Date d'expiration (timestamp)
}
```

3. **Requête SQL** :
```sql
SELECT * FROM user WHERE id = 1;
```

4. **Résultat** :
```python
user = User(
    id=1,
    email="admin@mppeep.gov",
    full_name="Administrateur",
    role=UserRole.ADMIN,
    is_active=True,
    agent_id=1
)
```

**Si erreur** : `HTTPException(401)` levée → Fin du traitement, réponse 401 envoyée

---

## 🎯 PHASE 5 : EXÉCUTION DE LA ROUTE

### Fonction : `rh_new_demande()`

**Fichier** : `app/api/v1/endpoints/rh.py`

```python
@router.get("/demandes/new", response_class=HTMLResponse, name="rh_new_demande")
def rh_new_demande(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Page de création d'une nouvelle demande RH"""
    
    # 1. Récupérer les types de demandes personnalisés
    request_types = session.exec(
        select(RequestTypeCustom)
        .where(RequestTypeCustom.actif == True)
        .order_by(RequestTypeCustom.ordre)
    ).all()
    
    # 2. Grouper par catégorie
    types_by_category = {}
    for rt in request_types:
        category = rt.categorie or "Autres"
        if category not in types_by_category:
            types_by_category[category] = []
        types_by_category[category].append(rt)
    
    # 3. Récupérer l'agent lié à l'utilisateur
    agent = None
    if current_user.agent_id:
        agent = session.get(AgentComplet, current_user.agent_id)
    
    # 4. Retourner le template avec les données
    return templates.TemplateResponse(
        "pages/rh_demande_new.html",
        get_template_context(
            request,
            current_user=current_user,
            request_types_custom=request_types,
            types_by_category=types_by_category,
            agent=agent
        )
    )
```

### Étape 5.1 : Requêtes SQL exécutées

**Requête 1 : Types de demandes**
```sql
SELECT * 
FROM request_type_custom 
WHERE actif = 1 
ORDER BY ordre;
```

**Résultat** :
```python
[
    RequestTypeCustom(id=1, code="CONGE", libelle="Demande de Congé", categorie="Congés"),
    RequestTypeCustom(id=2, code="MISSION", libelle="Ordre de Mission", categorie="Missions"),
    RequestTypeCustom(id=3, code="FORMATION", libelle="Demande de Formation", categorie="Formation"),
]
```

**Requête 2 : Agent de l'utilisateur**
```sql
SELECT * 
FROM agent_complet 
WHERE id = 1;
```

**Résultat** :
```python
agent = AgentComplet(
    id=1,
    matricule="2025-001",
    nom="DUPONT",
    prenom="Jean",
    grade_id=5,
    service_id=3,
    fonction="Chef de Service"
)
```

### Étape 5.2 : Préparation du contexte template

```python
context = {
    "request": request,
    "app_name": "MPPEEP Dashboard",
    "current_user": User(id=1, email="admin@mppeep.gov", ...),
    "current_year": 2025,
    "request_types_custom": [...],
    "types_by_category": {
        "Congés": [...],
        "Missions": [...],
        "Formation": [...]
    },
    "agent": AgentComplet(id=1, matricule="2025-001", ...)
}
```

---

## 🎨 PHASE 6 : RENDU DU TEMPLATE JINJA2

### Étape 6.1 : Chargement du template

**Fichier** : `app/templates/pages/rh_demande_new.html`

```html
{% extends "layouts/base.html" %}
{% from 'components/page_header.html' import page_header %}

{% block title %}Nouvelle Demande - {{ app_name }}{% endblock %}

{% block content %}
{{ page_header(
    title='➕ Nouvelle Demande RH',
    breadcrumbs=[
        {'name': 'Accueil', 'url': url_for('accueil')},
        {'name': 'RH', 'url': url_for('rh_home')},
        {'name': 'Nouvelle Demande'}
    ]
) }}

<form id="demandeForm" onsubmit="submitDemande(event)">
    <!-- Agent demandeur (pré-rempli) -->
    <div class="form-group">
        <label>Agent demandeur</label>
        <input type="hidden" name="agent_id" value="{{ agent.id if agent else '' }}" readonly>
        <input type="text" class="form-input" readonly
               value="{{ agent.matricule }} - {{ agent.nom }} {{ agent.prenom }}" >
    </div>
    
    <!-- Type de demande -->
    <div class="form-group">
        <label>Type de demande *</label>
        <select name="type" class="form-select" required>
            <option value="">-- Sélectionner --</option>
            {% for category, types in types_by_category.items() %}
                <optgroup label="{{ category }}">
                    {% for rt in types %}
                        <option value="{{ rt.code }}">{{ rt.libelle }}</option>
                    {% endfor %}
                </optgroup>
            {% endfor %}
        </select>
    </div>
    
    <!-- Autres champs... -->
    
    <button type="submit" class="btn btn-primary">Créer la Demande</button>
</form>
{% endblock %}
```

### Étape 6.2 : Compilation Jinja2

Jinja2 remplace les variables et exécute la logique :

**Avant** :
```html
<input type="text" value="{{ agent.matricule }} - {{ agent.nom }} {{ agent.prenom }}">
```

**Après** :
```html
<input type="text" value="2025-001 - DUPONT Jean">
```

**Avant** :
```html
{% for category, types in types_by_category.items() %}
    <optgroup label="{{ category }}">
        {% for rt in types %}
            <option value="{{ rt.code }}">{{ rt.libelle }}</option>
        {% endfor %}
    </optgroup>
{% endfor %}
```

**Après** :
```html
<optgroup label="Congés">
    <option value="CONGE">Demande de Congé</option>
</optgroup>
<optgroup label="Missions">
    <option value="MISSION">Ordre de Mission</option>
</optgroup>
<optgroup label="Formation">
    <option value="FORMATION">Demande de Formation</option>
</optgroup>
```

### Étape 6.3 : Application du layout de base

**Fichier** : `app/templates/layouts/base.html`

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ app_name }}{% endblock %}</title>
    
    <!-- CSS -->
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="/static/css/forms.css">
    <link rel="stylesheet" href="/static/css/cards.css">
    
    {% block styles %}{% endblock %}
</head>
<body>
    <!-- Navigation -->
    {% if current_user %}
        {% include 'components/navbar.html' %}
    {% endif %}
    
    <!-- Contenu principal -->
    <main class="container">
        {% block content %}{% endblock %}
    </main>
    
    <!-- Footer -->
    <footer>
        <p>&copy; {{ current_year }} {{ app_name }} - Tous droits réservés</p>
    </footer>
    
    <!-- JavaScript -->
    <script src="/static/js/app.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

### Étape 6.4 : HTML final généré

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Nouvelle Demande - MPPEEP Dashboard</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="/static/css/forms.css">
</head>
<body>
    <nav class="navbar">
        <div class="navbar-brand">MPPEEP Dashboard</div>
        <div class="navbar-menu">
            <a href="/api/v1/">Accueil</a>
            <a href="/api/v1/rh/">RH</a>
            <a href="/api/v1/personnel/">Personnel</a>
            <span>👤 admin@mppeep.gov</span>
        </div>
    </nav>
    
    <main class="container">
        <div class="page-header">
            <h1>➕ Nouvelle Demande RH</h1>
            <nav class="breadcrumb">
                <a href="/api/v1/">Accueil</a> / 
                <a href="/api/v1/rh/">RH</a> / 
                <span>Nouvelle Demande</span>
            </nav>
        </div>
        
        <form id="demandeForm">
            <div class="form-group">
                <label>Agent demandeur</label>
                <input type="hidden" name="agent_id" value="1">
                <input type="text" value="2025-001 - DUPONT Jean" readonly>
            </div>
            
            <div class="form-group">
                <label>Type de demande *</label>
                <select name="type" required>
                    <option value="">-- Sélectionner --</option>
                    <optgroup label="Congés">
                        <option value="CONGE">Demande de Congé</option>
                    </optgroup>
                    <optgroup label="Missions">
                        <option value="MISSION">Ordre de Mission</option>
                    </optgroup>
                </select>
            </div>
            
            <button type="submit">Créer la Demande</button>
        </form>
    </main>
    
    <footer>
        <p>&copy; 2025 MPPEEP Dashboard - Tous droits réservés</p>
    </footer>
    
    <script src="/static/js/app.js"></script>
</body>
</html>
```

**Taille du HTML** : ~15 Ko

---

## 📤 PHASE 7 : CONSTRUCTION DE LA RÉPONSE HTTP

### Étape 7.1 : Création de l'objet Response

```python
response = HTMLResponse(
    content=html_final,  # Le HTML compilé
    status_code=200,
    headers={
        "content-type": "text/html; charset=utf-8",
        "content-length": "15234",
    }
)
```

### Étape 7.2 : Retour au middleware de logging

Le middleware calcule la durée :

```python
duration = time.time() - start_time  # 0.125 secondes
logger.info(f"📤 GET /api/v1/rh/demandes/new | Status: 200 | Duration: 0.125s")
```

---

## 🌐 PHASE 8 : ENVOI DE LA RÉPONSE

### Étape 8.1 : Sérialisation HTTP

Uvicorn convertit l'objet Response en octets HTTP :

```http
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Content-Length: 15234
Set-Cookie: session_id=abc123; Path=/; HttpOnly
Date: Sun, 19 Oct 2025 01:15:30 GMT
Server: uvicorn

<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Nouvelle Demande - MPPEEP Dashboard</title>
    ...
</body>
</html>
```

### Étape 8.2 : Envoi sur le socket TCP

```
Uvicorn → TCP/IP → Navigateur (Chrome)
```

**Octets envoyés** : ~15 Ko de HTML

---

## 🖥️ PHASE 9 : RENDU DANS LE NAVIGATEUR

### Étape 9.1 : Parsing HTML

Le navigateur parse le HTML et construit le DOM (Document Object Model) :

```
DOM Tree:
├── html
    ├── head
    │   ├── meta (charset)
    │   ├── title
    │   ├── link (style.css)
    │   └── link (forms.css)
    └── body
        ├── nav (navbar)
        ├── main (container)
        │   ├── div (page-header)
        │   └── form (demandeForm)
        └── footer
```

### Étape 9.2 : Chargement des ressources

Le navigateur détecte les ressources à charger :

**Requête 2** :
```http
GET /static/css/style.css HTTP/1.1
```

**Requête 3** :
```http
GET /static/css/forms.css HTTP/1.1
```

**Requête 4** :
```http
GET /static/js/app.js HTTP/1.1
```

Chaque requête passe par les mêmes phases 1-8 (mais sans authentification pour les fichiers statiques).

### Étape 9.3 : Application des styles CSS

Le navigateur applique les règles CSS :

```css
.form-group {
    margin-bottom: 1.5rem;
}

.form-input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #ccc;
    border-radius: 4px;
}

.btn-primary {
    background-color: #007bff;
    color: white;
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}
```

**CSSOM (CSS Object Model)** construit.

### Étape 9.4 : Calcul du layout (Render Tree)

Le navigateur calcule la position et la taille de chaque élément :

```
Render Tree:
├── Body (1920x1080px)
    ├── Navbar (1920x60px, top:0)
    ├── Main Container (1200x800px, centered)
    │   ├── Page Header (1200x80px)
    │   └── Form (1200x500px)
    │       ├── Form Group 1 (1200x80px)
    │       ├── Form Group 2 (1200x80px)
    │       └── Button (150x40px)
    └── Footer (1920x60px, bottom:0)
```

### Étape 9.5 : Peinture (Painting)

Le navigateur dessine les pixels à l'écran :

1. **Arrière-plan** : Couleur de fond blanche
2. **Navbar** : Fond bleu, texte blanc
3. **Formulaire** : Champs de saisie, bordures grises
4. **Bouton** : Fond bleu, texte blanc, ombre portée
5. **Footer** : Texte gris centré

### Étape 9.6 : Exécution JavaScript

Le navigateur exécute `app.js` :

```javascript
// Gestion globale des erreurs
function handleFetchError(response, result) {
    if (result && result.detail) {
        alert(result.detail);
    }
}

// Fonction de soumission du formulaire
async function submitDemande(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    
    try {
        const response = await fetch("/api/v1/rh/api/demandes", {
            method: "POST",
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert("Demande créée avec succès !");
            window.location.href = "/api/v1/rh/";
        } else {
            handleFetchError(response, result);
        }
    } catch (error) {
        alert("Erreur réseau");
    }
}
```

**Event Listener** attaché au formulaire.

---

## ⏱️ PHASE 10 : PAGE AFFICHÉE

### Durées typiques

| Phase | Durée |
|-------|-------|
| Réception requête | 1 ms |
| Middlewares | 2 ms |
| Routage | 1 ms |
| Authentification | 5 ms |
| Requêtes SQL | 15 ms |
| Rendu template | 80 ms |
| Envoi réponse | 5 ms |
| **Total serveur** | **~110 ms** |
| Chargement CSS/JS | 20 ms |
| Parsing HTML | 10 ms |
| Calcul layout | 15 ms |
| Peinture | 5 ms |
| **Total navigateur** | **~50 ms** |
| **TOTAL** | **~160 ms** |

---

## 🔄 RÉSUMÉ VISUEL DU FLUX

```
┌──────────────────────────────────────────────────────────────┐
│ 🌐 NAVIGATEUR                                                │
│    Utilisateur clique sur "Nouvelle Demande"                │
│    GET /api/v1/rh/demandes/new                              │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 🌍 TCP/IP                                                    │
│    Transmission sur le réseau                               │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 🚀 UVICORN (Port 9000)                                       │
│    - Accepte la connexion                                   │
│    - Parse la requête HTTP                                  │
│    - Crée l'objet Request                                   │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 🛡️ MIDDLEWARES                                              │
│    1. Logging : 📥 GET /api/v1/rh/demandes/new             │
│    2. CORS (si activé)                                      │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 🗺️ ROUTAGE                                                  │
│    FastAPI cherche la route                                │
│    → Trouvé : rh_new_demande()                             │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 🔐 DÉPENDANCES                                              │
│    1. get_session() → Session DB                            │
│    2. get_current_user()                                    │
│       ├─ Lire cookie access_token                          │
│       ├─ Décoder JWT                                        │
│       ├─ SQL: SELECT * FROM user WHERE id = 1              │
│       └─ Retour: User(id=1, email="admin@...")            │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 🎯 FONCTION rh_new_demande()                                │
│    1. SQL: SELECT * FROM request_type_custom               │
│    2. Grouper par catégorie                                │
│    3. SQL: SELECT * FROM agent_complet WHERE id = 1        │
│    4. Préparer le contexte                                 │
│    5. Retourner templates.TemplateResponse(...)            │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 🎨 JINJA2                                                    │
│    1. Charger rh_demande_new.html                          │
│    2. Appliquer layouts/base.html                          │
│    3. Remplacer {{ variables }}                            │
│    4. Exécuter {% for %} loops                             │
│    5. Générer HTML final (15 Ko)                           │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 📤 RÉPONSE HTTP                                             │
│    HTTP/1.1 200 OK                                          │
│    Content-Type: text/html; charset=utf-8                  │
│    Content-Length: 15234                                    │
│                                                             │
│    <!DOCTYPE html>                                          │
│    <html>...</html>                                         │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 🛡️ MIDDLEWARES (retour)                                    │
│    Logging : 📤 Status: 200 | Duration: 0.125s            │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 🌍 TCP/IP                                                    │
│    Transmission de la réponse                               │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 🌐 NAVIGATEUR                                                │
│    1. Parse HTML → DOM                                      │
│    2. Requêtes: /static/css/style.css, forms.css, app.js  │
│    3. Apply CSS → CSSOM                                     │
│    4. Layout → Render Tree                                  │
│    5. Paint → Pixels à l'écran                             │
│    6. Execute JavaScript                                    │
│    7. ✅ PAGE AFFICHÉE (160ms total)                       │
└──────────────────────────────────────────────────────────────┘
```

---

## 📊 MÉTRIQUES DE PERFORMANCE

### Logs serveur

```
📥 GET /api/v1/rh/demandes/new | Request-ID: xY7k9mN2
📤 GET /api/v1/rh/demandes/new | Status: 200 | Duration: 0.125s | Request-ID: xY7k9mN2
📥 GET /static/css/style.css | Request-ID: aB3f8pQ1
📤 GET /static/css/style.css | Status: 200 | Duration: 0.008s | Request-ID: aB3f8pQ1
📥 GET /static/css/forms.css | Request-ID: cD5h2rT9
📤 GET /static/css/forms.css | Status: 200 | Duration: 0.006s | Request-ID: cD5h2rT9
📥 GET /static/js/app.js | Request-ID: eF7j4sU3
📤 GET /static/js/app.js | Status: 200 | Duration: 0.007s | Request-ID: eF7j4sU3
```

### Optimisations possibles

1. **Cache SQL** : Mettre en cache les types de demandes (Redis)
2. **CDN** : Servir les CSS/JS via un CDN
3. **Compression** : Activer gzip pour HTML/CSS/JS
4. **HTTP/2** : Multiplexage des requêtes CSS/JS
5. **Lazy loading** : Charger le JavaScript après le DOM

---

## 🔍 POINTS CLÉS

### Sécurité
- ✅ Authentification JWT vérifie à chaque requête
- ✅ Cookie `httpOnly` empêche le XSS
- ✅ Validation des données avec Pydantic
- ✅ SQL paramétré empêche l'injection SQL

### Performance
- ✅ Requêtes SQL optimisées (index, select spécifique)
- ✅ Session DB réutilisée (pas de nouvelle connexion à chaque requête)
- ✅ Templates compilés et mis en cache par Jinja2
- ✅ Fichiers statiques servis directement (pas de Python)

### Debugging
- ✅ Request-ID unique pour tracer chaque requête
- ✅ Logs détaillés (méthode, path, statut, durée)
- ✅ Exceptions capturées et loguées
- ✅ Mode `--reload` pour hot-reload

---

## 📚 FICHIERS IMPLIQUÉS

| Fichier | Rôle dans le flux |
|---------|-------------------|
| `app/main.py` | Middlewares, routage |
| `app/api/v1/router.py` | Enregistrement des routes |
| `app/api/v1/endpoints/rh.py` | Fonction `rh_new_demande()` |
| `app/api/v1/endpoints/auth.py` | Authentification `get_current_user()` |
| `app/db/session.py` | Session DB `get_session()` |
| `app/models/rh.py` | Modèles `HRRequest`, `RequestTypeCustom` |
| `app/models/personnel.py` | Modèle `AgentComplet` |
| `app/templates/pages/rh_demande_new.html` | Template de la page |
| `app/templates/layouts/base.html` | Layout de base |
| `app/static/css/style.css` | Styles globaux |
| `app/static/js/app.js` | JavaScript global |

---

**Prochaine étape** : Voir `03_MODULES_DETAILS.md` pour une explication détaillée de chaque module du projet.

