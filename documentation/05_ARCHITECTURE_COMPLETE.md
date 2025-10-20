# 📘 Architecture Complète MPPEEP Dashboard

## 🎯 Vue d'ensemble

Ce document présente l'**architecture technique complète** du système MPPEEP Dashboard avec diagrammes, schémas de base de données, et flux de données.

---

## 🏛️ ARCHITECTURE GLOBALE

### Schéma de haut niveau

```
┌─────────────────────────────────────────────────────────────────┐
│                        UTILISATEURS                              │
│  👤 Agents  │  👔 Chefs  │  🏛️ DRH  │  💼 DAF  │  👨‍💼 Admin     │
└─────────────────────────────────────────────────────────────────┘
                              ↓ HTTP/HTTPS
┌─────────────────────────────────────────────────────────────────┐
│                    REVERSE PROXY (Production)                    │
│                    Nginx / Caddy / Traefik                       │
│                    - SSL/TLS Termination                         │
│                    - Load Balancing                              │
│                    - Compression gzip                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        APPLICATION LAYER                         │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              UVICORN (ASGI Server)                      │    │
│  │                   Port 9000                             │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │            FastAPI Application                    │  │    │
│  │  │                                                   │  │    │
│  │  │  ┌────────────────────────────────────────────┐  │  │    │
│  │  │  │         MIDDLEWARES                        │  │  │    │
│  │  │  │  - Logging                                 │  │  │    │
│  │  │  │  - CORS                                    │  │  │    │
│  │  │  │  - Exception Handling                      │  │  │    │
│  │  │  └────────────────────────────────────────────┘  │  │    │
│  │  │                      ↓                            │  │    │
│  │  │  ┌────────────────────────────────────────────┐  │  │    │
│  │  │  │         ROUTAGE                            │  │  │    │
│  │  │  │  /api/v1/auth/      - Authentification    │  │  │    │
│  │  │  │  /api/v1/rh/        - Ressources Humaines │  │  │    │
│  │  │  │  /api/v1/personnel/ - Personnel           │  │  │    │
│  │  │  │  /api/v1/stock/     - Stock               │  │  │    │
│  │  │  │  /api/v1/budget/    - Budget              │  │  │    │
│  │  │  │  /api/v1/performance/ - Performance       │  │  │    │
│  │  │  └────────────────────────────────────────────┘  │  │    │
│  │  │                      ↓                            │  │    │
│  │  │  ┌────────────────────────────────────────────┐  │  │    │
│  │  │  │         SERVICES (Logique Métier)         │  │  │    │
│  │  │  │  - RHService                              │  │  │    │
│  │  │  │  - HierarchyService                       │  │  │    │
│  │  │  │  - StockService                           │  │  │    │
│  │  │  │  - WorkflowConfigService                  │  │  │    │
│  │  │  │  - ActivityService                        │  │  │    │
│  │  │  └────────────────────────────────────────────┘  │  │    │
│  │  │                      ↓                            │  │    │
│  │  │  ┌────────────────────────────────────────────┐  │  │    │
│  │  │  │         MODELS (SQLModel ORM)             │  │  │    │
│  │  │  │  - User                                   │  │  │    │
│  │  │  │  - AgentComplet                          │  │  │    │
│  │  │  │  - HRRequest                             │  │  │    │
│  │  │  │  - Article                               │  │  │    │
│  │  │  │  - WorkflowTemplate                      │  │  │    │
│  │  │  └────────────────────────────────────────────┘  │  │    │
│  │  └───────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │         SQLite (Dev) / PostgreSQL (Prod)               │    │
│  │                                                         │    │
│  │  Tables:                                                │    │
│  │  - user                    - workflow_template          │    │
│  │  - agent_complet           - workflow_template_step     │    │
│  │  - hrrequest               - custom_role                │    │
│  │  - workflowhistory         - custom_role_assignment     │    │
│  │  - article                 - request_type_custom        │    │
│  │  - lot_perissable          - grade_complet             │    │
│  │  - amortissement           - service                    │    │
│  │  - mouvement_stock         - ... (30+ tables)           │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ SCHÉMA DE BASE DE DONNÉES

### Relations principales

```
┌────────────────┐
│     USER       │
│ ─────────────  │
│ id (PK)        │──┐
│ email          │  │
│ hashed_password│  │
│ role           │  │
│ agent_id (FK)  │──┼─────────────┐
└────────────────┘  │             │
                    │             ↓
                    │    ┌─────────────────┐
                    │    │  AGENT_COMPLET  │
                    │    │ ──────────────  │
                    │    │ id (PK)         │
                    │    │ matricule       │
                    │    │ nom, prenom     │
                    │    │ grade_id (FK)   │───→ GRADE_COMPLET
                    │    │ service_id (FK) │───→ SERVICE
                    │    └─────────────────┘
                    │             ↑
                    │             │
    ┌───────────────┼─────────────┘
    │               │
    ↓               │
┌────────────────┐  │
│   HRREQUEST    │  │
│ ────────────── │  │
│ id (PK)        │  │
│ agent_id (FK)  │──┘
│ type           │──────→ REQUEST_TYPE_CUSTOM
│ current_state  │
│ date_debut     │
│ date_fin       │
└────────────────┘
    │
    ↓
┌──────────────────┐
│ WORKFLOW_HISTORY │
│ ──────────────── │
│ id (PK)          │
│ request_id (FK)  │
│ from_state       │
│ to_state         │
│ validator_id (FK)│──→ USER
└──────────────────┘

┌─────────────────────┐
│ REQUEST_TYPE_CUSTOM │
│ ─────────────────── │
│ id (PK)             │
│ code                │
│ libelle             │
│ workflow_template_id│───→ WORKFLOW_TEMPLATE
└─────────────────────┘
                            │
                            ↓
                   ┌──────────────────────┐
                   │  WORKFLOW_TEMPLATE   │
                   │ ──────────────────── │
                   │ id (PK)              │
                   │ code, nom            │
                   └──────────────────────┘
                            │
                            ↓
                   ┌──────────────────────────┐
                   │ WORKFLOW_TEMPLATE_STEP   │
                   │ ──────────────────────── │
                   │ id (PK)                  │
                   │ template_id (FK)         │
                   │ ordre                    │
                   │ custom_role_id (FK)      │───→ CUSTOM_ROLE
                   └──────────────────────────┘

┌───────────────────┐
│   CUSTOM_ROLE     │
│ ───────────────── │
│ id (PK)           │
│ code, libelle     │
└───────────────────┘
        │
        ↓
┌──────────────────────────┐
│ CUSTOM_ROLE_ASSIGNMENT   │
│ ──────────────────────── │
│ id (PK)                  │
│ custom_role_id (FK)      │
│ agent_id (FK)            │───→ AGENT_COMPLET
└──────────────────────────┘

┌────────────────┐
│    ARTICLE     │
│ ────────────── │
│ id (PK)        │
│ code           │
│ designation    │
│ est_perissable │
│ est_amortissable│
└────────────────┘
    │
    ├─────→ ┌──────────────────┐
    │       │  LOT_PERISSABLE  │
    │       │ ──────────────── │
    │       │ id (PK)          │
    │       │ article_id (FK)  │
    │       │ numero_lot       │
    │       │ date_peremption  │
    │       │ quantite_restante│
    │       └──────────────────┘
    │
    └─────→ ┌──────────────────┐
            │  AMORTISSEMENT   │
            │ ──────────────── │
            │ id (PK)          │
            │ article_id (FK)  │
            │ annee            │
            │ amortissement_periode│
            │ valeur_nette_comptable│
            └──────────────────┘
```

---

## 🔄 FLUX DE DONNÉES

### 1. Création d'une demande RH

```
┌─────────────┐
│ Utilisateur │ Remplit le formulaire "Nouvelle Demande"
└──────┬──────┘
       │ POST /api/v1/rh/api/demandes
       ↓
┌──────────────────┐
│  rh_create_demande│ Endpoint API
└──────┬───────────┘
       │ Valide les données
       ↓
┌──────────────────┐
│   RHService      │ Logique métier
└──────┬───────────┘
       │ Crée HRRequest
       ↓
┌──────────────────┐
│  SQLModel/DB     │ INSERT INTO hrrequest
└──────┬───────────┘
       │ request.id = 1
       ↓
┌──────────────────┐
│ ActivityService  │ Log l'activité
└──────┬───────────┘
       │ INSERT INTO activity_log
       ↓
┌──────────────────┐
│  Response JSON   │ {"success": true, "data": {"id": 1}}
└──────┬───────────┘
       │
       ↓
┌──────────────────┐
│  Navigateur      │ Redirection vers /api/v1/rh/
└──────────────────┘
```

### 2. Validation d'une demande

```
┌─────────────┐
│ Validateur  │ Clique sur "Valider" (Validation N+1)
└──────┬──────┘
       │ POST /api/v1/rh/api/demandes/1/transition
       │ to_state=VALIDATION_N1
       ↓
┌──────────────────────┐
│ rh_transition_demande│ Endpoint API
└──────┬───────────────┘
       │
       ↓
┌──────────────────────┐
│  HierarchyService    │ can_user_validate(user, request, state)
└──────┬───────────────┘
       │ 1. Récupère le workflow_template du type de demande
       │ 2. Trouve l'étape correspondante (ordre=1)
       │ 3. Récupère le custom_role de l'étape
       │ 4. Vérifie l'assignment du role à l'agent
       │ 5. Compare agent_id avec user.agent_id
       ↓
┌──────────────────────┐
│  Si autorisé ✅      │
└──────┬───────────────┘
       │
       ↓
┌──────────────────────┐
│    RHService         │ transition()
└──────┬───────────────┘
       │ 1. UPDATE hrrequest SET current_state = 'VALIDATION_N1'
       │ 2. INSERT INTO workflowhistory (validator, decision, ...)
       ↓
┌──────────────────────┐
│  Response JSON       │ {"success": true}
└──────┬───────────────┘
       │
       ↓
┌──────────────────────┐
│  Notification        │ (Future : Email/Push au prochain validateur)
└──────────────────────┘
```

### 3. Gestion des lots périssables

```
┌─────────────┐
│ Magasinier  │ Enregistre une entrée de stock
└──────┬──────┘
       │ POST /api/v1/stock/api/mouvements
       │ type=ENTREE, article_id=5 (périssable)
       │ numero_lot=LOT-2025-001
       │ date_peremption=2026-12-31
       ↓
┌──────────────────────┐
│ api_create_mouvement │
└──────┬───────────────┘
       │
       ↓
┌──────────────────────┐
│   StockService       │ enregistrer_mouvement()
└──────┬───────────────┘
       │ 1. INSERT INTO mouvement_stock
       │ 2. UPDATE article SET quantite_actuelle += quantite
       │
       │ Si article.est_perissable:
       │    3. Appelle creer_lot_perissable()
       ↓
┌──────────────────────┐
│   StockService       │ creer_lot_perissable()
└──────┬───────────────┘
       │ 1. Calcule jours_avant_peremption
       │ 2. Détermine statut (ACTIF/ALERTE/PERIME)
       │ 3. INSERT INTO lot_perissable
       ↓
┌──────────────────────┐
│   Alertes Auto       │ Si statut = ALERTE ou PERIME
└──────┬───────────────┘
       │ Affichage sur dashboard
       ↓
┌──────────────────────┐
│   Dashboard Stock    │ KPI "Lots Proches Péremption"
└──────────────────────┘
```

### 4. Calcul d'amortissement

```
┌─────────────┐
│ Comptable   │ Sélectionne année 2025 dans "Amortissements"
└──────┬──────┘
       │ GET /api/v1/stock/api/amortissements/materiels-a-amortir/2025
       ↓
┌──────────────────────┐
│ api_materiels_a_amortir│
└──────┬─────────────────┘
       │
       ↓
┌──────────────────────┐
│   StockService       │ get_materiels_a_amortir(2025)
└──────┬───────────────┘
       │ 1. SELECT * FROM article WHERE est_amortissable = 1
       │ 2. Pour chaque article:
       │    - Vérifie si amortissement_2025 existe
       │    - Si non → ajoute à la liste
       ↓
┌──────────────────────┐
│   Liste retournée    │ [Ordinateur #1, Véhicule #2, ...]
└──────┬───────────────┘
       │ Affichage dans le tableau
       ↓
┌─────────────┐
│ Comptable   │ Clique sur "💾 Calculer" pour Ordinateur #1
└──────┬──────┘
       │ POST /api/v1/stock/api/amortissements/calculer
       │ article_id=1, annee=2025
       ↓
┌──────────────────────┐
│ api_calculer_amortissement│
└──────┬─────────────────┘
       │
       ↓
┌──────────────────────┐
│   StockService       │ calculer_amortissement_annee(1, 2025)
└──────┬───────────────┘
       │ 1. Récupère article
       │ 2. Récupère amortissement_cumule de 2024
       │ 3. Calcule selon méthode (LINEAIRE/DEGRESSIF)
       │ 4. INSERT INTO amortissement
       ↓
┌──────────────────────┐
│   Amortissement      │ annee=2025, amort_periode=450000
└──────┬───────────────┘
       │ VNC = 1050000 FCFA
       ↓
┌──────────────────────┐
│   Response JSON      │ {"success": true, "data": {...}}
└──────────────────────┘
```

---

## 🔐 SÉCURITÉ EN COUCHES

```
┌─────────────────────────────────────────────────────────────┐
│ COUCHE 1 : RÉSEAU                                           │
│ - HTTPS (SSL/TLS)                                           │
│ - Firewall                                                  │
│ - Rate limiting (Nginx)                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ COUCHE 2 : APPLICATION                                      │
│ - CORS configuré                                            │
│ - Cookie httpOnly, secure, samesite                         │
│ - JWT avec expiration                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ COUCHE 3 : AUTHENTIFICATION                                 │
│ - Vérification du token à chaque requête                    │
│ - Vérification compte actif                                 │
│ - Rôles et permissions                                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ COUCHE 4 : VALIDATION                                       │
│ - Validation Pydantic (types, formats)                      │
│ - Règles métier (HierarchyService)                          │
│ - Contraintes DB (foreign keys, unique)                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ COUCHE 5 : BASE DE DONNÉES                                  │
│ - Requêtes paramétrées (SQL injection)                      │
│ - Transactions ACID                                         │
│ - Mot de passe hashé bcrypt                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 WORKFLOW PERSONNALISÉ - ARCHITECTURE

### Configuration

```
┌─────────────────────────────────────────────────────────────┐
│ 1. CRÉER DES RÔLES PERSONNALISÉS                           │
└─────────────────────────────────────────────────────────────┘
    │
    ↓
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   CUSTOM_ROLE       │  │   CUSTOM_ROLE       │  │   CUSTOM_ROLE       │
│ ─────────────────── │  │ ─────────────────── │  │ ─────────────────── │
│ code: VALID_CONGE   │  │ code: VALID_RH      │  │ code: VALID_BUDGET  │
│ libelle: Validateur │  │ libelle: DRH        │  │ libelle: DAF        │
│        Congés       │  │                     │  │                     │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 2. ATTRIBUER LES RÔLES AUX AGENTS                          │
└─────────────────────────────────────────────────────────────┘
    │
    ↓
┌──────────────────────────────┐
│  CUSTOM_ROLE_ASSIGNMENT      │
│ ──────────────────────────── │
│ VALID_CONGE → Agent #5       │ (Chef de Service)
│ VALID_RH    → Agent #2       │ (Directeur RH)
│ VALID_BUDGET → Agent #3      │ (DAF)
└──────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 3. CRÉER UN TEMPLATE DE WORKFLOW                           │
└─────────────────────────────────────────────────────────────┘
    │
    ↓
┌──────────────────────┐
│  WORKFLOW_TEMPLATE   │
│ ──────────────────── │
│ code: WF_CONGE       │
│ nom: Workflow Congés │
└──────────────────────┘
        │
        ↓
┌──────────────────────────────────────────────────────────┐
│           WORKFLOW_TEMPLATE_STEP                         │
│ ──────────────────────────────────────────────────────── │
│ Ordre 1 : VALID_CONGE   (Chef de Service)               │
│ Ordre 2 : VALID_RH      (DRH)                            │
│ Ordre 3 : VALID_BUDGET  (DAF)                            │
└──────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 4. CRÉER UN TYPE DE DEMANDE                                │
└─────────────────────────────────────────────────────────────┘
    │
    ↓
┌──────────────────────────┐
│  REQUEST_TYPE_CUSTOM     │
│ ──────────────────────── │
│ code: CONGE_ANNUEL       │
│ libelle: Congé Annuel    │
│ workflow_template: WF_CONGE│
└──────────────────────────┘
```

### Exécution d'une demande

```
┌─────────────────────────────────────────────────────────────┐
│ Agent crée une demande de type CONGE_ANNUEL                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│          Circuit de validation généré automatiquement        │
│ ──────────────────────────────────────────────────────────  │
│                                                              │
│  DRAFT → SUBMITTED → VALIDATION_N1 → VALIDATION_N2 →        │
│         VALIDATION_N3 → ARCHIVED                             │
│                                                              │
│  Mapping :                                                   │
│  - VALIDATION_N1 = VALID_CONGE (Agent #5)                   │
│  - VALIDATION_N2 = VALID_RH (Agent #2)                      │
│  - VALIDATION_N3 = VALID_BUDGET (Agent #3)                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  HierarchyService.get_expected_validator()                  │
│  → Retourne l'agent assigné au rôle de l'étape en cours     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  HierarchyService.can_user_validate()                       │
│  → Vérifie que current_user.agent_id == expected_validator  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Si autorisé : Transition effectuée                         │
│  Sinon : PermissionError                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 💾 STRATÉGIE DE PERSISTENCE

### SQLite (Développement)

**Avantages** :
- ✅ Fichier unique (`mppeep.db`)
- ✅ Pas de serveur à installer
- ✅ Rapide pour le développement
- ✅ Facile à sauvegarder (copier le fichier)

**Limites** :
- ❌ Pas de concurrence écriture
- ❌ Performance limitée (>100k lignes)
- ❌ Pas de réplication

### PostgreSQL (Production recommandé)

**Avantages** :
- ✅ Concurrence élevée
- ✅ Performance optimale
- ✅ Réplication et haute disponibilité
- ✅ Fonctionnalités avancées (JSON, Full-text search)

**Configuration** :
```bash
# .env production
DATABASE_URL=postgresql://mppeep_user:password@localhost:5432/mppeep_prod
```

---

## 🚦 GESTION DES ÉTATS

### États de demande RH (WorkflowState)

```
DRAFT           = Brouillon (non soumis)
    ↓
SUBMITTED       = Soumis (en attente de validation)
    ↓
VALIDATION_N1   = Validation niveau 1 (ex: Chef de Service)
    ↓
VALIDATION_N2   = Validation niveau 2 (ex: Directeur)
    ↓
VALIDATION_N3   = Validation niveau 3 (ex: DRH)
    ↓
VALIDATION_N4   = Validation niveau 4 (ex: DAF)
    ↓
VALIDATION_N5   = Validation niveau 5 (si nécessaire)
    ↓
VALIDATION_N6   = Validation niveau 6 (si nécessaire)
    ↓
ARCHIVED        = Archivé (traité)

    ↓ (à tout moment)
REJECTED        = Rejeté
```

### États de lot périssable

```
ACTIF    = Plus de X jours avant péremption (X = seuil_alerte)
    ↓
ALERTE   = Moins de X jours avant péremption
    ↓
PERIME   = Date de péremption dépassée
    ↓
EPUISE   = Quantité restante = 0
```

---

## 🔄 CYCLE DE VIE D'UNE REQUÊTE HTTP

```
┌──────────────────┐
│   1. CLIENT      │ Navigateur envoie GET /api/v1/rh/
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│   2. UVICORN     │ Serveur ASGI reçoit la connexion TCP
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│ 3. MIDDLEWARE    │ Logging : 📥 GET /api/v1/rh/ | Request-ID: abc123
│    (Logging)     │
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│ 4. MIDDLEWARE    │ Vérifie Origin, ajoute headers CORS
│    (CORS)        │
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│ 5. ROUTAGE       │ FastAPI match la route : rh_home()
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│ 6. DÉPENDANCES   │ get_session() → Session DB
│                  │ get_current_user() → User
└────────┬─────────┘
         │ JWT décodé, user récupéré en DB
         ↓
┌──────────────────┐
│ 7. ENDPOINT      │ rh_home(request, session, current_user)
│    (rh_home)     │
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│ 8. SERVICE       │ HierarchyService.get_pending_requests_for_user()
│                  │ RHService.kpis()
└────────┬─────────┘
         │ SELECT * FROM hrrequest WHERE ...
         ↓
┌──────────────────┐
│ 9. MODELS/DB     │ Exécution des requêtes SQL
└────────┬─────────┘
         │ Résultats retournés
         ↓
┌──────────────────┐
│ 10. TEMPLATE     │ Jinja2 compile rh.html avec les données
│     (Jinja2)     │
└────────┬─────────┘
         │ HTML généré
         ↓
┌──────────────────┐
│ 11. RESPONSE     │ HTMLResponse(content=html, status=200)
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│ 12. MIDDLEWARE   │ Logging : 📤 Status: 200 | Duration: 0.125s
│     (retour)     │
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│ 13. UVICORN      │ Envoie la réponse HTTP
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│ 14. CLIENT       │ Navigateur affiche la page
└──────────────────┘
```

---

## 🎯 POINTS CLÉS D'ARCHITECTURE

### 1. Séparation des responsabilités

```
Controllers (Endpoints) → Services → Models → Database
       ↑                     ↑         ↑
   HTTP/JSON            Logique    SQLModel
                        Métier
```

### 2. Dependency Injection

FastAPI gère automatiquement l'injection des dépendances :
```python
def endpoint(
    session: Session = Depends(get_session),  # Auto-injecté
    user: User = Depends(get_current_user)    # Auto-injecté
):
```

### 3. Type Safety

Type hints partout = validation automatique :
```python
def create_user(email: str, password: str) -> User:
    # Pydantic valide automatiquement les types
```

### 4. DRY (Don't Repeat Yourself)

- Services réutilisables
- Templates avec héritage
- Composants réutilisables (page_header, modals)
- CSS avec variables

---

## 📈 SCALABILITÉ

### Vertical Scaling (monter en puissance)

```
1 worker  →  4 workers  →  8 workers
1 CPU     →  4 CPU      →  8 CPU
2GB RAM   →  8GB RAM    →  16GB RAM
```

### Horizontal Scaling (multiple instances)

```
┌─────────────┐
│ Load Balancer│
└──────┬──────┘
       │
   ┌───┴───┬───────┬───────┐
   │       │       │       │
   ↓       ↓       ↓       ↓
┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
│App 1│ │App 2│ │App 3│ │App 4│
└──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘
   │       │       │       │
   └───┬───┴───┬───┴───┬───┘
       │       │       │
       ↓       ↓       ↓
┌─────────────────────────┐
│   PostgreSQL (Master)   │
└─────────────────────────┘
```

---

## 🔍 MONITORING ET OBSERVABILITÉ

### Logs

```
Format:
[HH:MM:SS] LEVEL | MODULE | MESSAGE

Exemple:
[14:23:45] INFO | app.main | 🚀 Démarrage de MPPEEP Dashboard...
[14:23:46] INFO | app.db.session | ✅ Base de données initialisée
[14:23:50] INFO | app.api.v1.endpoints.rh | 📥 GET /api/v1/rh/ | Request-ID: xY7k9mN2
[14:23:50] INFO | app.api.v1.endpoints.rh | 📤 Status: 200 | Duration: 0.125s
```

### Métriques

- **Request-ID** : Traçage de bout en bout
- **Duration** : Temps de réponse
- **Status Code** : Succès/Erreur
- **User** : Qui a fait l'action

---

## 🎓 PATTERNS UTILISÉS

### 1. Repository Pattern
Services agissent comme des repositories :
```python
StockService.creer_article()
StockService.get_article()
StockService.update_article()
```

### 2. Dependency Injection
FastAPI injecte automatiquement les dépendances

### 3. Template Method Pattern
Base template → Page templates

### 4. Strategy Pattern
Amortissement : Linéaire vs Dégressif

### 5. Observer Pattern
Workflow transitions → Activity logs

---

**Architecture solide, moderne et évolutive ! 🏗️**

Prochaine étape : Voir la [documentation complète](README.md)

