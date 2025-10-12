# 🏗️ Workflows d'Architecture - MPPEEP Dashboard

## 📋 Table des Matières

1. [Workflow de Démarrage de l'Application](#-workflow-de-démarrage)
2. [Workflow d'une Requête HTTP](#-workflow-dune-requête-http)
3. [Workflow d'Authentification](#-workflow-dauthentification)
4. [Workflow de Création d'Utilisateur](#-workflow-de-création-dutilisateur)

---

## 🚀 Workflow de Démarrage de l'Application

### Vue d'Ensemble

Voici **TOUT** ce qui se passe quand vous lancez `uvicorn app.main:app --reload` :

```
┌─────────────────────────────────────────────────────────────────┐
│  TERMINAL : uvicorn app.main:app --reload                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  1. UVICORN DÉMARRE                                             │
│  - Charge le module Python : app.main                           │
│  - Cherche l'objet : app                                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. IMPORT DE app.main                                          │
│  Fichier : app/main.py                                          │
│                                                                 │
│  from fastapi import FastAPI                                    │
│  from app.api.v1 import api_router          ← Import API        │
│  from app.core.config import settings        ← Import Config    │
│  from app.core.middleware import setup_middlewares              │
│  from app.templates import templates         ← Import Templates │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. CHARGEMENT DE app.core.config                               │
│  Fichier : app/core/config.py                                   │
│                                                                 │
│  class Settings(BaseSettings):                                  │
│      DEBUG = True                                               │
│      ENV = "dev"                                                │
│      DATABASE_URL = None                                        │
│      # ... autres configs                                       │
│                                                                 │
│  ┌──────────────────────────────────────────────────┐           │
│  │ Lecture du fichier .env (si existe)              │           │
│  │ Sinon : utilise les valeurs par défaut           │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                 │
│  settings = Settings()          ← Instanciation                 │
│                                                                 │
│  ┌──────────────────────────────────────────────────┐           │
│  │ @property database_url:                          │           │
│  │   if DATABASE_URL:                               │           │
│  │       return DATABASE_URL                        │           │
│  │   if DEBUG or ENV=="dev":                        │           │
│  │       return "sqlite:///./app.db"  ← CHOIX ICI  │            │
│  │   else:                                          │           │
│  │       return "postgresql://..."                  │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                 │
│  Résultat : database_url = "sqlite:///./app.db"                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  4. CHARGEMENT DE app.db.session                                │
│  Fichier : app/db/session.py                                    │
│                                                                 │
│  from app.core.config import settings  ← Utilise settings       │
│                                                                 │
│  engine = create_engine(                                        │
│      settings.database_url,  ← "sqlite:///./app.db"             │
│      echo=settings.DEBUG     ← True (affiche les SQL)           │
│  )                                                              │
│                                                                 │
│  ✅ Engine SQLite créé et configuré                             │
│                                                                 │
│  def get_session():                                             │
│      with Session(engine) as session:  ← Session SQLite         │
│          yield session                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  5. CHARGEMENT DES AUTRES MODULES                               │
│                                                                 │
│  app/api/v1/ → Routes API                                       │
│  app/models/ → Modèles SQLModel                                 │
│  app/services/ → Services métier                                │
│  app/templates/ → Templates Jinja2                              │
│  app/core/middleware.py → Middlewares                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  6. CRÉATION DE L'APPLICATION FASTAPI                           │
│  Fichier : app/main.py (ligne 9)                                │
│                                                                 │
│  app = FastAPI(title=settings.APP_NAME)                         │
│  ✅ Instance FastAPI créée                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  7. CONFIGURATION DES MIDDLEWARES                               │
│  Fichier : app/main.py (ligne 12)                               │
│                                                                 │
│  setup_middlewares(app, settings)                               │
│                                                                 │
│  ┌──────────────────────────────────────────────────┐           │
│  │ app/core/middleware.py - setup_middlewares()     │           │
│  │                                                   │          │
│  │ 1. HTTPS Redirect (si prod)                      │          │
│  │ 2. Trusted Hosts                                 │          │
│  │ 3. CORS                                          │          │
│  │ 4. Error Handling                                │          │
│  │ 5. Request Size Limit                            │          │
│  │ 6. IP Filter (optionnel)                         │          │
│  │ 7. User Agent Filter (optionnel)                 │          │
│  │ 8. Logging                                       │          │
│  │ 9. Request ID                                    │          │
│  │ 10. GZip Compression                             │          │
│  │ 11. Cache Control                                │          │
│  │ 12. Security Headers                             │          │
│  │ 13. CSP (Content Security Policy)                │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                  │
│  ✅ 13 middlewares configurés (selon flags dans settings)       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  8. MONTAGE DES FICHIERS STATIQUES                              │
│  Fichier : app/main.py (ligne 15)                               │
│                                                                  │
│  app.mount("/static", StaticFiles(directory="app/static"))      │
│                                                                  │
│  ✅ /static/ → app/static/                                     │
│     /static/css/theme.css → app/static/css/theme.css           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  9. INCLUSION DES ROUTES API                                    │
│  Fichier : app/main.py (ligne 18)                               │
│                                                                  │
│  app.include_router(api_router, prefix="/api/v1")               │
│                                                                  │
│  ┌──────────────────────────────────────────────────┐          │
│  │ app/api/v1/router.py - api_router                │          │
│  │                                                   │          │
│  │ from endpoints import health, users, auth        │          │
│  │                                                   │          │
│  │ api_router.include_router(health.router)         │          │
│  │ api_router.include_router(users.router)          │          │
│  │ api_router.include_router(auth.router)           │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                  │
│  ✅ Routes enregistrées :                                      │
│     GET  /api/v1/ping                                           │
│     POST /api/v1/login                                          │
│     GET  /api/v1/users                                          │
│     ... etc                                                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  10. DÉFINITION DES ROUTES RACINE                               │
│  Fichier : app/main.py (lignes 20-45)                           │
│                                                                  │
│  @app.get("/")                                                  │
│  def read_root(request):                                        │
│      return templates.TemplateResponse("login.html", ...)       │
│                                                                  │
│  @app.get("/accueil")                                           │
│  def accueil(request):                                          │
│      return templates.TemplateResponse("pages/accueil.html")    │
│                                                                  │
│  ✅ Routes racine enregistrées                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  11. ÉVÉNEMENT STARTUP                                          │
│  Fichier : app/main.py (lignes 18-30)                           │
│                                                                  │
│  @app.on_event("startup")                                       │
│  async def startup_event():                                     │
│      from scripts.init_db import initialize_database            │
│      initialize_database()                                      │
│                                                                  │
│  ┌──────────────────────────────────────────────────┐          │
│  │ scripts/init_db.py - initialize_database()       │          │
│  │                                                   │          │
│  │ Étape 0 : Créer la base PostgreSQL si besoin     │          │
│  │   if "postgresql" in database_url:               │          │
│  │       Connexion serveur PostgreSQL               │          │
│  │       Vérifier si base existe                    │          │
│  │       Si non → CREATE DATABASE                   │          │
│  │   if "sqlite" in database_url:                   │          │
│  │       → Rien (auto-créé)                         │          │
│  │                                                  │          │
│  │ Étape 1 : Créer les tables                       │          │
│  │   SQLModel.metadata.create_all(engine)           │          │
│  │   → Table user créée (si n'existe pas)           │          │
│  │                                                  │          │
│  │ Étape 2 : Vérifier les admins                    │          │
│  │   admin_count = UserService.get_admin_count()    │          │
│  │                                                  │          │
│  │   if admin_count == 0:                           │          │
│  │       ┌─────────────────────────────────┐        │          │
│  │       │ Créer admin par défaut          │        │          │
│  │       │ - Email: admin@mppeep.com       │        │          │
│  │       │ - Password: admin123            │        │          │
│  │       │ - Type: ADMIN                   │        │          │
│  │       │ - is_superuser: True            │        │          │
│  │       └─────────────────────────────────┘        │          │
│  │       UserService.create_user(...)               │          │
│  │       → Admin créé avec ID=1                     │          │
│  │       → Affiche les identifiants                 │          │
│  │   else:                                          │          │
│  │       → Skip (admin existe déjà)                 │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                  │
│  Console Output :                                               │
│  ================================                               │
│  🚀 Initialisation de la base de données...                    │
│  📂 Type: SQLite                                                │
│  📂 URL: sqlite:///./app.db                                     │
│  --------------------------------------------------             │
│  📁 SQLite: Le fichier sera créé automatiquement               │
│  ✅ Tables de la base de données créées/vérifiées              │
│  ✅ ADMINISTRATEUR CRÉÉ                                         │
│     📧 Email: admin@mppeep.com                                  │
│     🔑 Password: admin123                                       │
│  ✅ Initialisation terminée avec succès!                       │
│  ================================                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  12. APPLICATION PRÊTE                                          │
│                                                                  │
│  INFO: Uvicorn running on http://127.0.0.1:8000                │
│  INFO: Application startup complete.                            │
│                                                                  │
│  État de l'application :                                        │
│  ✅ FastAPI app créée                                          │
│  ✅ 13 middlewares configurés                                   │
│  ✅ Fichiers statiques montés (/static/)                       │
│  ✅ Routes API enregistrées (/api/v1/)                         │
│  ✅ Routes racine enregistrées (/, /accueil)                   │
│  ✅ Base de données initialisée (SQLite ou PostgreSQL)         │
│  ✅ Tables créées                                              │
│  ✅ Admin créé (si base vide)                                  │
│  ✅ Serveur en écoute sur port 8000                            │
│                                                                  │
│  📊 Base de données actuelle :                                 │
│     Type : SQLite (car DEBUG=true)                              │
│     Fichier : ./app.db                                          │
│     Tables : user (avec admin@mppeep.com)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🌐 Workflow d'une Requête HTTP

### Vue d'Ensemble

Voici ce qui se passe quand un client envoie une requête (exemple : `POST /api/v1/login`) :

```
┌─────────────────────────────────────────────────────────────────┐
│  CLIENT (Navigateur)                                            │
│  POST http://localhost:8000/api/v1/login                        │
│  Body: { username: "admin@mppeep.com", password: "admin123" }   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Requête HTTP
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  SERVEUR : Uvicorn (Port 8000)                                  │
│  Reçoit la connexion TCP                                        │
│  Parse la requête HTTP                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  ÉTAPE 1 : PASSAGE DANS LES MIDDLEWARES (Ordre inverse)        │
│                                                                  │
│  ┌──────────────────────────────────────────────────┐          │
│  │ 13. CSP Middleware                                │          │
│  │     → Ajoute Content-Security-Policy              │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   ↓                                              │
│  ┌──────────────────────────────────────────────────┐          │
│  │ 12. Security Headers Middleware                   │          │
│  │     → X-Frame-Options, X-Content-Type-Options     │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   ↓                                              │
│  ┌──────────────────────────────────────────────────┐          │
│  │ 11. Cache Control Middleware                      │          │
│  │     → Ajoute headers de cache                     │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   ↓                                              │
│  ┌──────────────────────────────────────────────────┐          │
│  │ 10. GZip Middleware                               │          │
│  │     → Prêt à compresser la réponse                │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   ↓                                              │
│  ┌──────────────────────────────────────────────────┐          │
│  │ 9. Request ID Middleware                          │          │
│  │    → Génère X-Request-ID: abc-123-def             │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   ↓                                              │
│  ┌──────────────────────────────────────────────────┐          │
│  │ 8. Logging Middleware                             │          │
│  │    → Log: "POST /api/v1/login - Request ID: ..." │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   ↓                                              │
│  ┌──────────────────────────────────────────────────┐          │
│  │ 7-6-5. Autres middlewares (IP, User-Agent, Size) │          │
│  │    → Vérifications de sécurité                    │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   ↓                                              │
│  ┌──────────────────────────────────────────────────┐          │
│  │ 4. Error Handling Middleware                      │          │
│  │    → Capture les erreurs éventuelles              │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   ↓                                              │
│  ┌──────────────────────────────────────────────────┐          │
│  │ 3. CORS Middleware                                │          │
│  │    → Vérification des origines autorisées         │          │
│  │    → Ajoute headers CORS                          │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   ↓                                              │
│  ┌──────────────────────────────────────────────────┐          │
│  │ 2. Trusted Hosts Middleware                       │          │
│  │    → Vérifie Host header                          │          │
│  │    → Bloque si host non autorisé                  │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   ↓                                              │
│  ┌──────────────────────────────────────────────────┐          │
│  │ 1. HTTPS Redirect Middleware (si prod)            │          │
│  │    → Redirige HTTP → HTTPS                        │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   ↓                                              │
│                                                                  │
│  ✅ Tous les middlewares traversés                             │
│  ✅ Requête validée et enrichie                                │
│  ✅ Headers ajoutés                                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  ÉTAPE 2 : ROUTING FASTAPI                                      │
│                                                                  │
│  FastAPI cherche la route correspondante :                      │
│  POST /api/v1/login                                             │
│                                                                  │
│  ┌──────────────────────────────────────────────────┐          │
│  │ Recherche dans :                                  │          │
│  │ 1. Routes racine (/, /accueil) → Non             │          │
│  │ 2. Routes /api/v1/* → OUI ! Trouvé              │          │
│  │                                                   │          │
│  │ Match: POST /api/v1/login                        │          │
│  │ Handler: auth.login_post()                       │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                  │
│  ✅ Route trouvée : app/api/v1/endpoints/auth.py::login_post() │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  ÉTAPE 3 : RÉSOLUTION DES DÉPENDANCES                           │
│                                                                  │
│  La fonction login_post a des paramètres :                      │
│                                                                  │
│  async def login_post(                                          │
│      request: Request,               ← FastAPI inject          │
│      username: str = Form(...),      ← Parse du body           │
│      password: str = Form(...),      ← Parse du body           │
│      session: Session = Depends(get_session)  ← Inject session │
│  ):                                                              │
│                                                                  │
│  ┌──────────────────────────────────────────────────┐          │
│  │ Résolution de Depends(get_session) :             │          │
│  │                                                   │          │
│  │ 1. Appel de get_session()                        │          │
│  │    Fichier: app/db/session.py                    │          │
│  │                                                   │          │
│  │    def get_session():                            │          │
│  │        with Session(engine) as session:          │          │
│  │            yield session                         │          │
│  │                                                   │          │
│  │ 2. Session créée depuis engine                   │          │
│  │    engine → create_engine("sqlite:///./app.db")  │          │
│  │    session → Session SQLite                      │          │
│  │                                                   │          │
│  │ 3. Session injectée dans login_post()            │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                  │
│  ✅ Paramètres résolus :                                       │
│     request = Request object                                    │
│     username = "admin@mppeep.com"                               │
│     password = "admin123"                                       │
│     session = Session(engine SQLite)  ← Pointe vers SQLite     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  ÉTAPE 4 : EXÉCUTION DE LA FONCTION ENDPOINT                    │
│  Fichier : app/api/v1/endpoints/auth.py::login_post()           │
│                                                                  │
│  # Utiliser le service pour authentifier                        │
│  user = UserService.authenticate(session, username, password)   │
│                                                                  │
│  ┌──────────────────────────────────────────────────┐          │
│  │ app/services/user_service.py - authenticate()    │          │
│  │                                                   │          │
│  │ 1. Récupérer l'utilisateur par email             │          │
│  │    user = UserService.get_by_email(session, email)│          │
│  │                                                   │          │
│  │    ┌────────────────────────────────────┐        │          │
│  │    │ SELECT * FROM user                 │        │          │
│  │    │ WHERE email = 'admin@mppeep.com'   │        │          │
│  │    │                                    │        │          │
│  │    │ ✅ Exécuté dans SQLite (app.db)   │        │          │
│  │    │ ✅ User trouvé                     │        │          │
│  │    └────────────────────────────────────┘        │          │
│  │                                                   │          │
│  │ 2. Vérifier le mot de passe                      │          │
│  │    if verify_password(password, user.hashed_...):│          │
│  │        → Bcrypt compare                           │          │
│  │        → Match ✅                                │          │
│  │                                                   │          │
│  │ 3. Retourner l'utilisateur                       │          │
│  │    return user                                    │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                  │
│  if not user:                                                   │
│      → Retourner erreur                                         │
│                                                                  │
│  if not user.is_active:                                         │
│      → Retourner erreur                                         │
│                                                                  │
│  # Authentification réussie                                     │
│  return RedirectResponse(url="/accueil", status_code=303)       │
│                                                                  │
│  ✅ Réponse préparée                                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  ÉTAPE 5 : FERMETURE AUTOMATIQUE DE LA SESSION                 │
│                                                                  │
│  La session était dans un context manager :                     │
│                                                                  │
│  with Session(engine) as session:                               │
│      yield session      ← Endpoint exécuté                      │
│  # Ici : fermeture auto ✅                                     │
│                                                                  │
│  Actions automatiques :                                         │
│  1. session.close() → Ferme la connexion DB                     │
│  2. Libère les ressources                                       │
│  3. Rollback si erreur non committée                            │
│                                                                  │
│  ✅ Pas de fuite de connexion                                  │
│  ✅ Pas de transaction pendante                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  ÉTAPE 6 : RETOUR DANS LES MIDDLEWARES (Ordre inverse)         │
│                                                                  │
│  La réponse traverse les middlewares dans l'ordre inverse :     │
│                                                                  │
│  Response = RedirectResponse(url="/accueil", status=303)        │
│                   ↓                                              │
│  ┌──────────────────────────────────────────────────┐          │
│  │ 1. HTTPS Redirect → Skip (déjà HTTPS)            │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   ↓                                              │
│  ┌──────────────────────────────────────────────────┐          │
│  │ 2. Trusted Hosts → Vérifié ✅                    │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   ↓                                              │
│  ┌──────────────────────────────────────────────────┐          │
│  │ 3. CORS → Ajoute headers Access-Control-*        │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   ↓                                              │
│  │ ... middlewares 4-9 ...                          │          │
│                   ↓                                              │
│  ┌──────────────────────────────────────────────────┐          │
│  │ 10. GZip → Compresse la réponse si > 1KB         │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   ↓                                              │
│  ┌──────────────────────────────────────────────────┐          │
│  │ 11. Cache Control → Cache-Control: no-cache      │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   ↓                                              │
│  ┌──────────────────────────────────────────────────┐          │
│  │ 12. Security Headers                              │          │
│  │     → X-Content-Type-Options: nosniff             │          │
│  │     → X-Frame-Options: DENY                       │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   ↓                                              │
│  ┌──────────────────────────────────────────────────┐          │
│  │ 13. CSP                                           │          │
│  │     → Content-Security-Policy: default-src ...    │          │
│  └────────────────┬─────────────────────────────────┘          │
│                   ↓                                              │
│                                                                  │
│  ✅ Réponse enrichie avec headers de sécurité                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  ÉTAPE 7 : ENVOI AU CLIENT                                      │
│                                                                  │
│  HTTP/1.1 303 See Other                                         │
│  Location: /accueil                                             │
│  X-Request-ID: abc-123-def                                      │
│  Access-Control-Allow-Origin: *                                 │
│  X-Content-Type-Options: nosniff                                │
│  X-Frame-Options: DENY                                          │
│  Content-Security-Policy: default-src 'self'                    │
│  Cache-Control: no-cache                                        │
│  Content-Encoding: gzip                                         │
│                                                                  │
│  ✅ Réponse complète envoyée                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Réponse HTTP
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  CLIENT (Navigateur)                                            │
│  Reçoit 303 Redirect → /accueil                                │
│  Navigue automatiquement vers /accueil                          │
│  ✅ Utilisateur authentifié et redirigé                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Détail : Flux Base de Données dans une Requête

```
REQUÊTE : POST /api/v1/login
    ↓
ENDPOINT : auth.login_post(session)
    │
    │ session injectée par Depends(get_session)
    │ └→ Session liée à engine
    │    └→ engine créé avec settings.database_url
    │       └→ "sqlite:///./app.db" (car DEBUG=true)
    │
    ↓
SERVICE : UserService.authenticate(session, email, password)
    │
    │ 1. get_by_email(session, email)
    │    ├→ statement = select(User).where(User.email == email)
    │    ├→ session.exec(statement)
    │    │  └→ SQLAlchemy traduit en SQL
    │    │     └→ SELECT * FROM user WHERE email = ?
    │    │        └→ Exécuté dans SQLite (app.db) ✅
    │    └→ Résultat : User object
    │
    │ 2. verify_password(password, user.hashed_password)
    │    └→ Bcrypt compare
    │       └→ Match ✅
    │
    ↓
RETOUR à l'endpoint
    │
    │ user trouvé et vérifié
    │ return RedirectResponse(...)
    │
    ↓
RÉPONSE au client
```

---

## 🎯 Points Clés

### ✅ Le Service Ne Sait Pas Où Il Écrit

```python
# Service (agnostique)
def create_user(session, email, ...):
    user = User(...)
    session.add(user)     # ← Ne sait pas si SQLite ou PostgreSQL
    session.commit()      # ← Écrit dans la base liée à la session
    return user
```

**La session "sait" grâce à son engine**

---

### ✅ L'Engine Est Configuré Au Démarrage

```python
# session.py (ligne 6)
engine = create_engine(settings.database_url)
#                      ↑
#                      Choix fait ICI au démarrage
#                      "sqlite:///./app.db" si DEBUG=true
#                      "postgresql://..." si DEBUG=false
```

**Une seule fois au démarrage, puis réutilisé partout**

---

### ✅ Changement Transparent

```
Changer DEBUG=false dans .env
→ Redémarrer l'application
→ Nouveau engine PostgreSQL créé
→ Toutes les sessions pointent vers PostgreSQL
→ Tous les services écrivent dans PostgreSQL
→ AUCUN changement de code nécessaire ✅
```

---

## 📊 Résumé Visuel

```
┌──────────────┐
│   .env       │
│  DEBUG=true  │
└──────┬───────┘
       │
       ↓
┌──────────────────────────┐
│  config.py               │
│  @property database_url  │
│  → "sqlite:///./app.db"  │
└──────┬───────────────────┘
       │
       ↓
┌──────────────────────────┐
│  session.py              │
│  engine = create_engine  │
│  → Engine SQLite         │
└──────┬───────────────────┘
       │
       ↓
┌──────────────────────────┐
│  get_session()           │
│  → Session SQLite        │
└──────┬───────────────────┘
       │
       ↓
┌──────────────────────────┐
│  Endpoint                │
│  session: Depends(...)   │
│  → Reçoit Session SQLite │
└──────┬───────────────────┘
       │
       ↓
┌──────────────────────────┐
│  Service                 │
│  session.add(user)       │
│  → Écrit dans SQLite ✅  │
└──────────────────────────┘
```

**Tout est automatique grâce à la cascade de configuration ! 🎯**
