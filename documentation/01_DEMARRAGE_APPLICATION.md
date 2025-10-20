# 📘 Démarrage de l'Application MPPEEP - Du Lancement à la Page Login

## 🎯 Vue d'ensemble

Ce document détaille le **parcours complet** du démarrage de l'application MPPEEP, depuis l'exécution de la commande de lancement jusqu'à l'affichage de la page de connexion dans le navigateur.

---

## 🚀 1. LANCEMENT DE L'APPLICATION

### Commande de démarrage
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 9000
```

### Paramètres expliqués
- `uvicorn` : Serveur ASGI haute performance pour FastAPI
- `app.main:app` : Module Python `app.main` contenant l'instance FastAPI nommée `app`
- `--reload` : Mode développement avec rechargement automatique à chaque modification
- `--host 0.0.0.0` : Écoute sur toutes les interfaces réseau
- `--port 9000` : Port d'écoute HTTP

---

## 📂 2. CHARGEMENT DU MODULE PRINCIPAL

### Fichier : `mppeep/app/main.py`

#### Étape 2.1 : Imports initiaux
```python
from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
```

**Explication** :
- `FastAPI` : Classe principale du framework
- `Request` : Objet représentant la requête HTTP
- `StaticFiles` : Middleware pour servir les fichiers statiques (CSS, JS, images)
- `RedirectResponse` : Réponse de redirection HTTP
- `RequestValidationError` : Exception levée lors d'erreurs de validation Pydantic
- `asynccontextmanager` : Décorateur pour gérer le cycle de vie de l'application

---

## 🔧 3. INITIALISATION DE LA BASE DE DONNÉES

### Étape 3.1 : Lifespan Event

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gère le cycle de vie de l'application"""
    logger.info("🚀 Démarrage de MPPEEP Dashboard...")
    
    # Création des tables
    create_db_and_tables()
    logger.info("✅ Base de données initialisée")
    
    yield  # L'application tourne ici
    
    logger.info("🛑 Arrêt de MPPEEP Dashboard")
```

**Fonction : `create_db_and_tables()`** (fichier `app/db/session.py`)

```python
def create_db_and_tables():
    """Crée toutes les tables de la base de données"""
    # Import de tous les modèles
    from app.models import (
        User, AgentComplet, GradeComplet, Service,
        HRRequest, WorkflowHistory,
        CustomRole, CustomRoleAssignment,
        WorkflowTemplate, WorkflowTemplateStep,
        RequestTypeCustom,
        Article, CategorieArticle, Fournisseur,
        MouvementStock, DemandeStock, Inventaire,
        LotPerissable, Amortissement,
        ObjectifPerformance, IndicateurPerformance,
        RapportPerformance,
        # ... autres modèles
    )
    
    # Création des tables avec SQLModel
    SQLModel.metadata.create_all(engine)
```

**Ce qui se passe** :
1. SQLModel inspecte tous les modèles importés
2. Génère les requêtes SQL `CREATE TABLE IF NOT EXISTS`
3. Exécute les requêtes sur la base SQLite (`mppeep.db`)
4. Crée les index et contraintes de clés étrangères

**Tables créées** :
- `user` : Utilisateurs du système
- `agent_complet` : Agents (personnel)
- `grade_complet` : Grades et catégories
- `service` : Services et directions
- `hrrequest` : Demandes RH
- `workflowhistory` : Historique des workflows
- `custom_role` : Rôles personnalisés
- `custom_role_assignment` : Attributions de rôles
- `workflow_template` : Templates de workflows
- `workflow_template_step` : Étapes des templates
- `request_type_custom` : Types de demandes personnalisés
- `article` : Articles de stock
- `categorie_article` : Catégories d'articles
- `fournisseur` : Fournisseurs
- `mouvement_stock` : Mouvements de stock
- `demande_stock` : Demandes d'approvisionnement
- `inventaire` : Inventaires
- `lot_perissable` : Lots périssables
- `amortissement` : Amortissements
- `objectif_performance` : Objectifs
- `indicateur_performance` : Indicateurs
- `rapport_performance` : Rapports

---

## 🏗️ 4. CRÉATION DE L'INSTANCE FASTAPI

```python
app = FastAPI(
    title="MPPEEP Dashboard",
    version="1.0.0",
    description="Système de Gestion Intégré",
    lifespan=lifespan
)
```

**Propriétés** :
- `title` : Nom de l'application (affiché dans la doc auto)
- `version` : Version de l'API
- `description` : Description du système
- `lifespan` : Gestionnaire du cycle de vie

---

## 🎨 5. CONFIGURATION DES FICHIERS STATIQUES

```python
app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)
```

**Explication** :
- Monte le dossier `app/static` sur le chemin `/static`
- Permet d'accéder aux fichiers CSS, JS, images, fonts via `/static/...`
- Exemple : `/static/css/style.css`, `/static/js/app.js`

**Structure du dossier `static`** :
```
app/static/
├── css/
│   ├── style.css          # Styles globaux
│   ├── forms.css          # Styles des formulaires
│   ├── cards.css          # Styles des cartes
│   ├── tables.css         # Styles des tableaux
│   ├── buttons.css        # Styles des boutons
│   └── modals.css         # Styles des modals
├── js/
│   └── app.js             # JavaScript global
└── images/
    └── logo.png           # Logo de l'application
```

---

## 🔌 6. ENREGISTREMENT DES MIDDLEWARES

### Middleware 1 : Logging des requêtes

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log toutes les requêtes HTTP"""
    start_time = time.time()
    request_id = secrets.token_urlsafe(8)
    
    logger.info(f"📥 {request.method} {request.url.path} | Request-ID: {request_id}")
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    logger.info(
        f"📤 {request.method} {request.url.path} | "
        f"Status: {response.status_code} | "
        f"Duration: {duration:.3f}s"
    )
    
    return response
```

**Rôle** :
- Intercepte toutes les requêtes HTTP
- Génère un ID unique pour chaque requête
- Log l'URL, la méthode, le statut et la durée
- Utile pour le debugging et le monitoring

### Middleware 2 : Gestion des erreurs CORS (si activé)

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Rôle** :
- Permet les requêtes cross-origin (pour API REST)
- Autorise tous les domaines (`*` en développement)
- Active les cookies et authentification

---

## 🛣️ 7. ENREGISTREMENT DES ROUTES

```python
from app.api.v1.router import api_router

app.include_router(api_router)
```

**Fichier : `app/api/v1/router.py`**

```python
from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, accueil, admin, personnel,
    rh, budget, performance, stock,
    referentiels, workflow_admin
)

api_router = APIRouter(prefix="/api/v1")

# Inclusion des sous-routeurs
api_router.include_router(auth.router, tags=["Authentication"])
api_router.include_router(accueil.router, tags=["Accueil"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(personnel.router, prefix="/personnel", tags=["Personnel"])
api_router.include_router(rh.router, prefix="/rh", tags=["RH"])
api_router.include_router(budget.router, prefix="/budget", tags=["Budget"])
api_router.include_router(performance.router, prefix="/performance", tags=["Performance"])
api_router.include_router(stock.router, prefix="/stock", tags=["Stock"])
api_router.include_router(referentiels.router, prefix="/referentiels", tags=["Referentiels"])
api_router.include_router(workflow_admin.router, prefix="/workflow", tags=["Workflow"])
```

**Structure des routes** :
- `/api/v1/auth/...` : Authentification (login, logout)
- `/api/v1/` : Page d'accueil
- `/api/v1/admin/...` : Administration
- `/api/v1/personnel/...` : Gestion du personnel
- `/api/v1/rh/...` : Ressources Humaines
- `/api/v1/budget/...` : Gestion budgétaire
- `/api/v1/performance/...` : Performance
- `/api/v1/stock/...` : Gestion de stock
- `/api/v1/referentiels/...` : Référentiels (services, grades, programmes)
- `/api/v1/workflow/...` : Configuration des workflows

---

## 🎯 8. GESTIONNAIRE D'EXCEPTION PERSONNALISÉ

```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Gère les erreurs de validation Pydantic (422)"""
    logger.warning(f"⚠️ Erreur validation sur {request.url.path}: {exc.errors()}")
    
    error_details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:])
        error_type = error["type"]
        error_msg = error["msg"]
        
        if error_type == "missing":
            error_details.append(f"Le champ '{field}' est obligatoire")
        elif error_type == "type_error.integer":
            error_details.append(f"Le champ '{field}' doit être un nombre entier")
        # ... autres types d'erreurs
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": main_message,
            "errors": error_details,
            "field_errors": {...}
        }
    )
```

**Rôle** :
- Intercepte les erreurs de validation des données
- Traduit les messages techniques en français
- Retourne des messages clairs à l'utilisateur
- Facilite le debugging côté frontend

---

## 🌐 9. ROUTE RACINE ET REDIRECTION

```python
@app.get("/")
async def root():
    """Redirection de la racine vers la page de connexion"""
    return RedirectResponse(url="/api/v1/auth/login", status_code=status.HTTP_302_FOUND)
```

**Comportement** :
1. L'utilisateur accède à `http://localhost:9000/`
2. FastAPI exécute la fonction `root()`
3. Retourne une `RedirectResponse` avec code HTTP 302 (Found)
4. Le navigateur est redirigé vers `/api/v1/auth/login`

---

## 🔐 10. ACCÈS À LA PAGE LOGIN

### Route : `GET /api/v1/auth/login`

**Fichier : `app/api/v1/endpoints/auth.py`**

```python
@router.get("/login", response_class=HTMLResponse, name="login_page")
async def login_page(request: Request):
    """Affiche la page de connexion"""
    
    # Vérifier si l'utilisateur est déjà connecté
    token = request.cookies.get("access_token")
    if token:
        try:
            # Valider le token
            user = await get_current_user_optional(token, session)
            if user:
                # Rediriger vers l'accueil si déjà connecté
                return RedirectResponse(url="/api/v1/", status_code=302)
        except:
            pass  # Token invalide, continuer vers login
    
    # Afficher la page de login
    return templates.TemplateResponse(
        "pages/login.html",
        get_template_context(request)
    )
```

### Fonction : `get_template_context()`

**Fichier : `app/templates/__init__.py`**

```python
def get_template_context(request: Request, **kwargs) -> dict:
    """Génère le contexte pour les templates Jinja2"""
    context = {
        "request": request,
        "app_name": "MPPEEP Dashboard",
        "app_version": "1.0.0",
        "current_year": datetime.now().year,
        "current_user": kwargs.get("current_user"),
        **kwargs  # Autres variables spécifiques
    }
    return context
```

### Template : `login.html`

**Fichier : `app/templates/pages/login.html`**

```html
{% extends "layouts/base.html" %}

{% block title %}Connexion - {{ app_name }}{% endblock %}

{% block content %}
<div class="login-container">
    <div class="login-card">
        <div class="login-header">
            <h1>🏛️ MPPEEP Dashboard</h1>
            <p>Système de Gestion Intégré</p>
        </div>
        
        <form id="loginForm" onsubmit="handleLogin(event)">
            <div class="form-group">
                <label for="email">Email</label>
                <input type="email" id="email" name="email" 
                       class="form-input" required 
                       placeholder="votre.email@exemple.com">
            </div>
            
            <div class="form-group">
                <label for="password">Mot de passe</label>
                <input type="password" id="password" name="password" 
                       class="form-input" required>
            </div>
            
            <button type="submit" class="btn btn-primary btn-block">
                🔐 Se connecter
            </button>
        </form>
        
        <div class="login-footer">
            <p>&copy; {{ current_year }} MPPEEP - Tous droits réservés</p>
        </div>
    </div>
</div>

<script>
async function handleLogin(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    
    try {
        const response = await fetch("/api/v1/auth/login", {
            method: "POST",
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            window.location.href = "/api/v1/";
        } else {
            alert("Erreur : " + result.error);
        }
    } catch (error) {
        alert("Erreur de connexion");
    }
}
</script>
{% endblock %}
```

---

## 📊 11. RENDU FINAL DANS LE NAVIGATEUR

### Étapes de rendu

1. **Jinja2 compile le template** :
   - Remplace `{{ app_name }}` par "MPPEEP Dashboard"
   - Remplace `{{ current_year }}` par 2025
   - Insère le contenu du `{% block content %}`

2. **Le layout de base est appliqué** :
   - Fichier : `app/templates/layouts/base.html`
   - Inclut le `<head>` avec les CSS
   - Inclut la navigation (si connecté)
   - Inclut le `<footer>`

3. **Le HTML est envoyé au navigateur** :
```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Connexion - MPPEEP Dashboard</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="/static/css/forms.css">
</head>
<body class="login-page">
    <div class="login-container">
        <!-- Contenu du formulaire -->
    </div>
    
    <script src="/static/js/app.js"></script>
</body>
</html>
```

4. **Le navigateur charge les ressources** :
   - Télécharge `/static/css/style.css`
   - Télécharge `/static/css/forms.css`
   - Télécharge `/static/js/app.js`
   - Applique les styles CSS
   - Exécute le JavaScript

5. **La page est affichée** :
   - Formulaire de login visible
   - Styles appliqués (couleurs, bordures, animations)
   - JavaScript prêt à intercepter la soumission du formulaire

---

## 🔄 12. RÉSUMÉ DU FLUX COMPLET

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Commande Shell                                           │
│    uvicorn app.main:app --reload --port 9000                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Uvicorn démarre                                          │
│    - Charge le module app.main                              │
│    - Import FastAPI et dépendances                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Lifespan Event (startup)                                 │
│    - create_db_and_tables()                                 │
│    - Création de toutes les tables SQLite                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Création instance FastAPI                                │
│    app = FastAPI(...)                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Configuration                                            │
│    - app.mount("/static", StaticFiles(...))                 │
│    - app.add_middleware(log_requests)                       │
│    - app.include_router(api_router)                         │
│    - app.exception_handler(RequestValidationError)          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Serveur prêt                                             │
│    INFO: Uvicorn running on http://0.0.0.0:9000            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. Utilisateur ouvre navigateur                            │
│    http://localhost:9000/                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. Route "/" exécutée                                       │
│    return RedirectResponse("/api/v1/auth/login")            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 9. Navigateur redirigé                                      │
│    GET /api/v1/auth/login                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 10. Route login_page() exécutée                             │
│     - Vérification du cookie access_token                   │
│     - Si non connecté : afficher login.html                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 11. Template Jinja2 rendu                                   │
│     - Compilation de login.html                             │
│     - Remplacement des variables                            │
│     - Génération du HTML final                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 12. HTML envoyé au navigateur                               │
│     Content-Type: text/html; charset=utf-8                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 13. Navigateur charge les ressources                        │
│     - GET /static/css/style.css                             │
│     - GET /static/css/forms.css                             │
│     - GET /static/js/app.js                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 14. Page affichée                                           │
│     ✅ Formulaire de connexion visible                      │
│     ✅ Styles CSS appliqués                                 │
│     ✅ JavaScript actif                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 LOGS CONSOLE TYPIQUES

```
INFO:     Uvicorn running on http://0.0.0.0:9000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
🚀 Démarrage de MPPEEP Dashboard...
✅ Base de données initialisée
INFO:     Application startup complete.

📥 GET / | Request-ID: xY7k9mN2
📤 GET / | Status: 302 | Duration: 0.005s

📥 GET /api/v1/auth/login | Request-ID: aB3f8pQ1
📤 GET /api/v1/auth/login | Status: 200 | Duration: 0.125s

📥 GET /static/css/style.css | Request-ID: cD5h2rT9
📤 GET /static/css/style.css | Status: 200 | Duration: 0.008s

📥 GET /static/css/forms.css | Request-ID: eF7j4sU3
📤 GET /static/css/forms.css | Status: 200 | Duration: 0.006s

📥 GET /static/js/app.js | Request-ID: gH9l6vW5
📤 GET /static/js/app.js | Status: 200 | Duration: 0.007s
```

---

## 🎓 CONCEPTS CLÉS

### 1. **ASGI (Asynchronous Server Gateway Interface)**
- Standard pour les serveurs Python asynchrones
- Permet la concurrence (plusieurs requêtes simultanées)
- Uvicorn implémente ASGI

### 2. **FastAPI**
- Framework web Python moderne et rapide
- Basé sur les type hints Python
- Validation automatique avec Pydantic
- Documentation auto-générée (OpenAPI/Swagger)

### 3. **SQLModel**
- ORM (Object-Relational Mapping)
- Combine SQLAlchemy et Pydantic
- Permet de définir des modèles Python qui deviennent des tables SQL

### 4. **Jinja2**
- Moteur de templates
- Permet d'insérer des variables Python dans du HTML
- Supporte l'héritage de templates (`{% extends %}`)

### 5. **Middleware**
- Code qui s'exécute avant/après chaque requête
- Utilisé pour : logging, CORS, authentification, compression, etc.

### 6. **Lifespan Events**
- Code exécuté au démarrage et à l'arrêt de l'application
- Utile pour : connexion DB, chargement de cache, nettoyage

---

## 🔍 POINTS D'ATTENTION

### Performance
- Les middlewares s'exécutent pour CHAQUE requête
- Les imports lourds ralentissent le démarrage
- SQLModel crée les tables au démarrage (peut être lent avec beaucoup de tables)

### Sécurité
- Les cookies `access_token` doivent être `httpOnly` et `secure` en production
- Les mots de passe doivent être hashés avec `bcrypt`
- CORS doit être restreint en production (`allow_origins=["https://votredomaine.com"]`)

### Debugging
- Les logs montrent toutes les requêtes et leur durée
- Les erreurs 422 sont capturées et traduites en français
- Le mode `--reload` permet le hot-reload pendant le développement

---

## ✅ CHECKLIST DE DÉMARRAGE

- [x] Base de données créée (`mppeep.db`)
- [x] Tables créées (user, agent_complet, service, etc.)
- [x] Serveur Uvicorn démarré sur le port 9000
- [x] Middlewares enregistrés (logging, CORS)
- [x] Routes enregistrées (`/api/v1/...`)
- [x] Fichiers statiques montés (`/static/...`)
- [x] Templates Jinja2 configurés
- [x] Exception handlers installés
- [x] Page login accessible et fonctionnelle

---

## 📚 FICHIERS IMPORTANTS

| Fichier | Rôle |
|---------|------|
| `app/main.py` | Point d'entrée, configuration FastAPI |
| `app/db/session.py` | Connexion DB, création des tables |
| `app/api/v1/router.py` | Enregistrement des routes |
| `app/api/v1/endpoints/auth.py` | Routes d'authentification |
| `app/templates/pages/login.html` | Template de la page login |
| `app/templates/layouts/base.html` | Layout de base (header, footer) |
| `app/static/css/style.css` | Styles globaux |
| `app/core/logging_config.py` | Configuration des logs |

---

**Durée totale du démarrage** : ~2-5 secondes (selon le nombre de tables et la puissance de la machine)

**Prochaine étape** : Voir `02_PARCOURS_REQUETE_CLIENT.md` pour comprendre le traitement d'une requête complète.

