# 📘 Modules Frontend et API - Documentation Détaillée

## 🎯 Vue d'ensemble

Ce document complète la documentation des modules MPPEEP en détaillant :
- Les **endpoints API** (routes FastAPI)
- Les **templates** (Jinja2/HTML)
- Les **fichiers statiques** (CSS/JS)

---

# 🌐 MODULE 5 : API ENDPOINTS (Routes)

## Architecture des routes

```
/api/v1/
├── auth/              # Authentification
├── /                  # Accueil
├── admin/             # Administration
│   ├── gestion-utilisateurs/
│   └── parametres-systeme/
├── personnel/         # Gestion du personnel
├── rh/                # Ressources Humaines
├── budget/            # Gestion budgétaire
├── performance/       # Performance
├── stock/             # Gestion de stock
├── referentiels/      # Référentiels
└── workflow/          # Configuration workflows
```

## Fichier : `app/api/v1/endpoints/auth.py`

**Module d'authentification**

### Routes principales

```python
from fastapi import APIRouter, Request, Response, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

router = APIRouter()

@router.get("/login", response_class=HTMLResponse, name="login_page")
async def login_page(request: Request):
    """Affiche la page de connexion"""
    
    # Vérifier si déjà connecté
    token = request.cookies.get("access_token")
    if token:
        try:
            user = await get_current_user_optional(token, session)
            if user:
                return RedirectResponse(url="/api/v1/", status_code=302)
        except:
            pass
    
    return templates.TemplateResponse(
        "pages/login.html",
        get_template_context(request)
    )

@router.post("/login", response_class=JSONResponse, name="login_submit")
async def login_submit(
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    """Traite la soumission du formulaire de connexion"""
    
    # 1. Rechercher l'utilisateur
    user = session.exec(
        select(User).where(User.email == email)
    ).first()
    
    if not user:
        return {"success": False, "error": "Email ou mot de passe incorrect"}
    
    # 2. Vérifier le mot de passe
    if not verify_password(password, user.hashed_password):
        return {"success": False, "error": "Email ou mot de passe incorrect"}
    
    # 3. Vérifier que le compte est actif
    if not user.is_active:
        return {"success": False, "error": "Compte désactivé"}
    
    # 4. Créer le token JWT
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # 5. Créer la réponse avec cookie
    response = JSONResponse({
        "success": True,
        "message": "Connexion réussie",
        "redirect": "/api/v1/"
    })
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,  # Protection XSS
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    
    logger.info(f"✅ Connexion réussie: {user.email}")
    
    return response

@router.get("/logout", name="logout")
async def logout():
    """Déconnexion"""
    response = RedirectResponse(url="/api/v1/auth/login", status_code=302)
    response.delete_cookie("access_token")
    return response

# Dépendance pour obtenir l'utilisateur connecté
def get_current_user(
    request: Request,
    session: Session = Depends(get_session)
) -> User:
    """Récupère l'utilisateur connecté depuis le token JWT"""
    
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")
    
    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    
    return user
```

### Utilisation dans d'autres routes

```python
@router.get("/protected")
def protected_route(
    current_user: User = Depends(get_current_user)
):
    """Route protégée nécessitant une authentification"""
    return {"message": f"Bonjour {current_user.full_name}"}
```

---

## Fichier : `app/api/v1/endpoints/rh.py`

**Module Ressources Humaines**

### Routes principales

```python
@router.get("/", response_class=HTMLResponse, name="rh_home")
def rh_home(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Tableau de bord RH"""
    
    # Récupérer les demandes en attente pour l'utilisateur
    pending_requests = HierarchyService.get_pending_requests_for_user(
        session, current_user.id
    )
    
    return templates.TemplateResponse(
        "pages/rh.html",
        get_template_context(
            request,
            current_user=current_user,
            pending_requests=pending_requests
        )
    )

@router.get("/demandes/new", response_class=HTMLResponse, name="rh_new_demande")
def rh_new_demande(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Page de création d'une nouvelle demande"""
    
    # Récupérer les types de demandes
    request_types = session.exec(
        select(RequestTypeCustom)
        .where(RequestTypeCustom.actif == True)
        .order_by(RequestTypeCustom.ordre)
    ).all()
    
    # Grouper par catégorie
    types_by_category = {}
    for rt in request_types:
        category = rt.categorie or "Autres"
        if category not in types_by_category:
            types_by_category[category] = []
        types_by_category[category].append(rt)
    
    # Récupérer l'agent lié à l'utilisateur
    agent = None
    if current_user.agent_id:
        agent = session.get(AgentComplet, current_user.agent_id)
    
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

@router.post("/api/demandes", response_class=JSONResponse, name="rh_create_demande")
def rh_create_demande(
    agent_id: int = Form(...),
    type: str = Form(...),
    date_debut: Optional[str] = Form(None),
    date_fin: Optional[str] = Form(None),
    objet: Optional[str] = Form(None),
    motif: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Crée une nouvelle demande RH"""
    
    try:
        # Valider que le type existe
        request_type = session.exec(
            select(RequestTypeCustom).where(RequestTypeCustom.code == type)
        ).first()
        
        if not request_type:
            return {"success": False, "error": "Type de demande invalide"}
        
        # Convertir les dates
        date_deb = datetime.strptime(date_debut, '%Y-%m-%d').date() if date_debut else None
        date_f = datetime.strptime(date_fin, '%Y-%m-%d').date() if date_fin else None
        
        # Créer la demande
        req = HRRequest(
            agent_id=agent_id,
            type=type,
            date_debut=date_deb,
            date_fin=date_f,
            objet=objet,
            motif=motif,
            description=description,
            current_state=WorkflowState.DRAFT
        )
        
        session.add(req)
        session.commit()
        session.refresh(req)
        
        # Enregistrer l'activité
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="create",
            target_type="hr_request",
            target_id=req.id,
            description=f"Création de la demande {type}",
            icon="📝"
        )
        
        return {
            "success": True,
            "message": "Demande créée avec succès",
            "data": {"id": req.id}
        }
    
    except Exception as e:
        logger.error(f"Erreur création demande: {e}")
        return {"success": False, "error": str(e)}

@router.get("/demandes/{request_id}", response_class=HTMLResponse, name="rh_demande_detail")
def rh_demande_detail(
    request_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Page de détail d'une demande"""
    
    req = session.get(HRRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    
    # Récupérer l'agent
    agent = session.get(AgentComplet, req.agent_id)
    
    # Récupérer le circuit de workflow
    workflow_circuit = HierarchyService.get_workflow_circuit(session, request_id)
    
    # Récupérer les informations du workflow
    workflow_info = HierarchyService.get_workflow_info(session, request_id)
    
    # Récupérer l'historique
    history = session.exec(
        select(WorkflowHistory)
        .where(WorkflowHistory.request_id == request_id)
        .order_by(WorkflowHistory.created_at)
    ).all()
    
    # Déterminer les actions possibles
    next_states = RHService.next_states_for(session, request_id)
    
    return templates.TemplateResponse(
        "pages/rh_demande_detail.html",
        get_template_context(
            request,
            current_user=current_user,
            req=req,
            agent=agent,
            workflow_circuit=workflow_circuit,
            workflow_info=workflow_info,
            history=history,
            next_states=next_states
        )
    )

@router.post("/api/demandes/{request_id}/transition", response_class=JSONResponse)
def rh_transition_demande(
    request_id: int,
    to_state: str = Form(...),
    commentaire: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Effectue une transition de workflow"""
    
    try:
        # Convertir la chaîne en enum
        state_enum = WorkflowState(to_state)
        
        # Effectuer la transition
        updated_request = RHService.transition(
            session=session,
            request_id=request_id,
            to_state=state_enum,
            user_id=current_user.id,
            commentaire=commentaire
        )
        
        return {
            "success": True,
            "message": f"Demande mise à jour : {state_enum.value}",
            "data": {"current_state": updated_request.current_state.value}
        }
    
    except PermissionError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Erreur transition: {e}")
        return {"success": False, "error": "Erreur lors de la transition"}

@router.get("/api/kpis", response_class=JSONResponse, name="api_kpis")
def api_kpis(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Retourne les KPIs RH"""
    return {"success": True, "data": RHService.kpis(session)}
```

---

## Fichier : `app/api/v1/endpoints/stock.py`

**Module Gestion de Stock**

### Routes principales

```python
@router.get("/", response_class=HTMLResponse, name="stock_home")
def stock_home(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Tableau de bord stock"""
    return templates.TemplateResponse(
        "pages/stock.html",
        get_template_context(request, current_user=current_user)
    )

@router.get("/articles", response_class=HTMLResponse, name="stock_articles")
def stock_articles(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Liste des articles"""
    return templates.TemplateResponse(
        "pages/stock_articles.html",
        get_template_context(request, current_user=current_user)
    )

@router.get("/articles/new", response_class=HTMLResponse, name="stock_article_new")
def stock_article_new(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Formulaire de création d'article"""
    
    categories = session.exec(select(CategorieArticle)).all()
    
    return templates.TemplateResponse(
        "pages/stock_article_form.html",
        get_template_context(
            request,
            current_user=current_user,
            article=None,
            categories=categories
        )
    )

@router.post("/api/articles", response_class=JSONResponse, name="api_create_article")
def api_create_article(
    code: str = Form(...),
    designation: str = Form(...),
    categorie_id: Optional[int] = Form(None),
    unite: str = Form("Unité"),
    quantite_min: float = Form(0),
    quantite_max: Optional[float] = Form(None),
    prix_unitaire: Optional[float] = Form(None),
    emplacement: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    # Périssable
    est_perissable: Optional[str] = Form(None),
    seuil_alerte_peremption_jours: Optional[int] = Form(30),
    # Amortissement
    est_amortissable: Optional[str] = Form(None),
    date_acquisition: Optional[str] = Form(None),
    valeur_acquisition: Optional[float] = Form(None),
    duree_amortissement_annees: Optional[int] = Form(None),
    taux_amortissement: Optional[float] = Form(None),
    valeur_residuelle: Optional[float] = Form(None),
    methode_amortissement: Optional[str] = Form("LINEAIRE"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Crée un nouvel article"""
    
    try:
        # Convertir les checkboxes
        est_perissable_bool = est_perissable == "true" if est_perissable else False
        est_amortissable_bool = est_amortissable == "true" if est_amortissable else False
        
        # Convertir la date d'acquisition
        date_acq = None
        if date_acquisition:
            from datetime import datetime
            try:
                date_acq = datetime.strptime(date_acquisition, '%Y-%m-%d').date()
            except:
                pass
        
        article = StockService.creer_article(
            session=session,
            code=code,
            designation=designation,
            categorie_id=categorie_id,
            unite=unite,
            quantite_min=Decimal(str(quantite_min)),
            quantite_max=Decimal(str(quantite_max)) if quantite_max else None,
            prix_unitaire=Decimal(str(prix_unitaire)) if prix_unitaire else None,
            emplacement=emplacement,
            description=description,
            # Périssable
            est_perissable=est_perissable_bool,
            seuil_alerte_peremption_jours=seuil_alerte_peremption_jours,
            # Amortissement
            est_amortissable=est_amortissable_bool,
            date_acquisition=date_acq,
            valeur_acquisition=Decimal(str(valeur_acquisition)) if valeur_acquisition else None,
            duree_amortissement_annees=duree_amortissement_annees,
            taux_amortissement=Decimal(str(taux_amortissement)) if taux_amortissement else None,
            valeur_residuelle=Decimal(str(valeur_residuelle)) if valeur_residuelle else None,
            methode_amortissement=methode_amortissement
        )
        
        # Log activité
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="create",
            target_type="stock_article",
            target_id=article.id,
            description=f"Création de l'article {article.code} - {article.designation}",
            icon="📦"
        )
        
        return {
            "success": True,
            "message": f"Article '{designation}' créé avec succès",
            "data": {"id": article.id, "code": article.code}
        }
    
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Erreur création article: {e}")
        return {"success": False, "error": "Erreur lors de la création"}

@router.get("/lots-perissables", response_class=HTMLResponse, name="stock_lots_perissables")
def stock_lots_perissables(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Page de suivi des lots périssables"""
    return templates.TemplateResponse(
        "pages/stock_lots_perissables.html",
        get_template_context(request, current_user=current_user)
    )

@router.get("/api/lots-perissables", response_class=JSONResponse, name="api_list_lots_perissables")
def api_list_lots_perissables(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Liste tous les lots périssables"""
    
    try:
        lots = session.exec(
            select(LotPerissable).order_by(LotPerissable.date_peremption)
        ).all()
        
        data = []
        for lot in lots:
            article = session.get(Article, lot.article_id)
            jours_restants = (lot.date_peremption - date.today()).days
            
            data.append({
                "id": lot.id,
                "numero_lot": lot.numero_lot,
                "article_code": article.code if article else "N/A",
                "article_designation": article.designation if article else "N/A",
                "date_fabrication": str(lot.date_fabrication) if lot.date_fabrication else None,
                "date_reception": str(lot.date_reception),
                "date_peremption": str(lot.date_peremption),
                "jours_restants": jours_restants,
                "quantite_initiale": float(lot.quantite_initiale),
                "quantite_restante": float(lot.quantite_restante),
                "statut": lot.statut,
                "observations": lot.observations
            })
        
        return {"success": True, "data": data}
    
    except Exception as e:
        logger.error(f"Erreur liste lots: {e}")
        return {"success": False, "error": str(e)}

@router.get("/amortissements", response_class=HTMLResponse, name="stock_amortissements")
def stock_amortissements(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Page de gestion des amortissements"""
    return templates.TemplateResponse(
        "pages/stock_amortissements.html",
        get_template_context(request, current_user=current_user)
    )

@router.post("/api/amortissements/calculer", response_class=JSONResponse, name="api_calculer_amortissement")
def api_calculer_amortissement(
    article_id: int = Form(...),
    annee: int = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Calcule l'amortissement pour une année"""
    
    try:
        amortissement = StockService.calculer_amortissement_annee(
            session=session,
            article_id=article_id,
            annee=annee
        )
        
        return {
            "success": True,
            "message": f"Amortissement {annee} calculé",
            "data": {
                "id": amortissement.id,
                "annee": amortissement.annee,
                "amortissement_periode": float(amortissement.amortissement_periode),
                "amortissement_cumule": float(amortissement.amortissement_cumule_fin),
                "valeur_nette_comptable": float(amortissement.valeur_nette_comptable)
            }
        }
    
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Erreur calcul: {e}")
        return {"success": False, "error": "Erreur lors du calcul"}
```

---

# 🎨 MODULE 6 : TEMPLATES (HTML/Jinja2)

## Architecture des templates

```
app/templates/
├── layouts/
│   └── base.html              # Layout de base
├── components/
│   ├── page_header.html       # En-tête de page
│   ├── navbar.html            # Navigation
│   └── modal.html             # Modals réutilisables
└── pages/
    ├── login.html             # Page de login
    ├── accueil.html           # Page d'accueil
    ├── rh.html                # Dashboard RH
    ├── rh_demande_new.html    # Nouvelle demande
    ├── rh_demande_detail.html # Détail demande
    ├── stock.html             # Dashboard stock
    ├── stock_articles.html    # Liste articles
    ├── stock_article_form.html # Formulaire article
    ├── stock_lots_perissables.html # Lots périssables
    ├── stock_amortissements.html   # Amortissements
    └── ...
```

## Fichier : `app/templates/layouts/base.html`

**Layout de base hérité par toutes les pages**

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ app_name }}{% endblock %}</title>
    
    <!-- CSS globaux -->
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="/static/css/forms.css">
    <link rel="stylesheet" href="/static/css/cards.css">
    <link rel="stylesheet" href="/static/css/tables.css">
    <link rel="stylesheet" href="/static/css/buttons.css">
    <link rel="stylesheet" href="/static/css/modals.css">
    
    <!-- CSS spécifiques à la page -->
    {% block styles %}{% endblock %}
</head>
<body>
    <!-- Navigation (si connecté) -->
    {% if current_user %}
        {% include 'components/navbar.html' %}
    {% endif %}
    
    <!-- Contenu principal -->
    <main class="container">
        {% block content %}{% endblock %}
    </main>
    
    <!-- Footer -->
    <footer class="footer">
        <p>&copy; {{ current_year }} {{ app_name }} - Tous droits réservés</p>
    </footer>
    
    <!-- Overlay de chargement global -->
    <div id="globalLoadingOverlay" class="loading-overlay">
        <div class="loading-spinner"></div>
        <p id="loadingMessage">Chargement...</p>
        <small id="loadingSubMessage"></small>
    </div>
    
    <!-- JavaScript global -->
    <script src="/static/js/app.js"></script>
    
    <!-- JavaScript spécifique à la page -->
    {% block scripts %}{% endblock %}
</body>
</html>
```

## Fichier : `app/templates/components/page_header.html`

**Composant d'en-tête de page réutilisable**

```html
{% macro page_header(title, breadcrumbs=[], actions=[]) %}
<div class="page-header">
    <div class="page-header-content">
        <h1 class="page-title">{{ title }}</h1>
        
        {% if breadcrumbs %}
        <nav class="breadcrumb">
            {% for crumb in breadcrumbs %}
                {% if loop.last %}
                    <span>{{ crumb.name }}</span>
                {% else %}
                    <a href="{{ crumb.url }}">{{ crumb.name }}</a>
                    <span class="breadcrumb-separator">/</span>
                {% endif %}
            {% endfor %}
        </nav>
        {% endif %}
    </div>
    
    {% if actions %}
    <div class="page-header-actions">
        {% for action in actions %}
            <a href="{{ action.url }}" 
               class="btn {% if action.primary %}btn-primary{% else %}btn-secondary{% endif %}">
                {{ action.label }}
            </a>
        {% endfor %}
    </div>
    {% endif %}
</div>
{% endmacro %}
```

**Utilisation** :
```html
{% from 'components/page_header.html' import page_header %}

{{ page_header(
    title='📦 Gestion des Articles',
    breadcrumbs=[
        {'name': 'Accueil', 'url': url_for('accueil')},
        {'name': 'Stock', 'url': url_for('stock_home')},
        {'name': 'Articles'}
    ],
    actions=[
        {'label': '➕ Nouvel Article', 'url': url_for('stock_article_new'), 'primary': True},
        {'label': '← Retour', 'url': url_for('stock_home'), 'primary': False}
    ]
) }}
```

## Exemple de page : `rh_demande_new.html`

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

<div class="card">
    <form id="demandeForm" onsubmit="submitDemande(event)">
        <!-- Agent demandeur (pré-rempli et readonly) -->
        <div class="form-group">
            <label class="form-label">Agent demandeur *</label>
            <input type="hidden" name="agent_id" value="{{ agent.id if agent else '' }}" readonly>
            <input type="text" class="form-input" readonly
                   value="{{ agent.matricule }} - {{ agent.nom }} {{ agent.prenom }}" 
                   style="background: #f5f5f5;">
        </div>
        
        <!-- Type de demande -->
        <div class="form-group">
            <label class="form-label">Type de demande *</label>
            <select name="type" class="form-select" required>
                <option value="">-- Sélectionner un type --</option>
                {% for category, types in types_by_category.items() %}
                    <optgroup label="{{ category }}">
                        {% for rt in types %}
                            <option value="{{ rt.code }}">{{ rt.libelle }}</option>
                        {% endfor %}
                    </optgroup>
                {% endfor %}
            </select>
        </div>
        
        <!-- Dates -->
        <div class="form-grid">
            <div class="form-group">
                <label class="form-label">Date de début</label>
                <input type="date" name="date_debut" class="form-input">
            </div>
            
            <div class="form-group">
                <label class="form-label">Date de fin</label>
                <input type="date" name="date_fin" class="form-input">
            </div>
        </div>
        
        <!-- Objet et motif -->
        <div class="form-group">
            <label class="form-label">Objet *</label>
            <input type="text" name="objet" class="form-input" required>
        </div>
        
        <div class="form-group">
            <label class="form-label">Motif *</label>
            <textarea name="motif" class="form-textarea" rows="3" required></textarea>
        </div>
        
        <!-- Actions -->
        <div class="form-actions">
            <a href="{{ url_for('rh_home') }}" class="btn btn-secondary">Annuler</a>
            <button type="submit" class="btn btn-primary">Créer la Demande</button>
        </div>
    </form>
</div>
{% endblock %}

{% block scripts %}
<script>
async function submitDemande(event) {
    event.preventDefault();
    
    showGlobalLoading('Création en cours...', 'Veuillez patienter');
    
    const formData = new FormData(event.target);
    
    try {
        const response = await fetch("{{ url_for('rh_create_demande') }}", {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(result.message);
            setTimeout(() => {
                window.location.href = "{{ url_for('rh_home') }}";
            }, 800);
        } else {
            hideGlobalLoading();
            showError(result.error);
        }
    } catch (error) {
        hideGlobalLoading();
        console.error('Erreur:', error);
        showError('Erreur lors de la création');
    }
}
</script>
{% endblock %}
```

---

# 💅 MODULE 7 : STATIC (CSS/JS)

## Structure des fichiers statiques

```
app/static/
├── css/
│   ├── style.css       # Styles globaux
│   ├── forms.css       # Formulaires
│   ├── cards.css       # Cartes
│   ├── tables.css      # Tableaux
│   ├── buttons.css     # Boutons
│   └── modals.css      # Modals
├── js/
│   └── app.js          # JavaScript global
└── images/
    └── logo.png
```

## Fichier : `app/static/css/style.css`

**Styles globaux**

```css
/* Variables CSS */
:root {
    --primary-color: #007bff;
    --secondary-color: #6c757d;
    --success-color: #28a745;
    --danger-color: #dc3545;
    --warning-color: #ffc107;
    --info-color: #17a2b8;
    
    --text-color: #212529;
    --text-muted: #6c757d;
    --border-color: #dee2e6;
    --background-color: #f8f9fa;
    
    --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    --border-radius: 8px;
    --transition-speed: 0.3s;
}

/* Reset & Base */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: var(--font-family);
    font-size: 16px;
    line-height: 1.6;
    color: var(--text-color);
    background-color: var(--background-color);
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
}

/* Page Header */
.page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
    padding-bottom: 1rem;
    border-bottom: 2px solid var(--border-color);
}

.page-title {
    font-size: 2rem;
    font-weight: 700;
    color: var(--text-color);
}

.breadcrumb {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    color: var(--text-muted);
}

.breadcrumb a {
    color: var(--primary-color);
    text-decoration: none;
}

.breadcrumb a:hover {
    text-decoration: underline;
}

/* Loading Overlay */
.loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    display: none;
    justify-content: center;
    align-items: center;
    flex-direction: column;
    z-index: 9999;
}

.loading-overlay.show {
    display: flex;
}

.loading-spinner {
    width: 50px;
    height: 50px;
    border: 4px solid #f3f3f3;
    border-top: 4px solid var(--primary-color);
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Footer */
.footer {
    text-align: center;
    padding: 2rem;
    margin-top: 4rem;
    color: var(--text-muted);
    border-top: 1px solid var(--border-color);
}
```

## Fichier : `app/static/js/app.js`

**JavaScript global**

```javascript
// ============================================
// GESTION DU LOADING OVERLAY
// ============================================

function showGlobalLoading(message = 'Chargement...', submessage = '') {
    const overlay = document.getElementById('globalLoadingOverlay');
    const messageEl = document.getElementById('loadingMessage');
    const submessageEl = document.getElementById('loadingSubMessage');
    
    if (overlay) {
        if (messageEl) messageEl.textContent = message;
        if (submessageEl) submessageEl.textContent = submessage;
        overlay.classList.add('show');
    }
}

function hideGlobalLoading() {
    const overlay = document.getElementById('globalLoadingOverlay');
    if (overlay) {
        overlay.classList.remove('show');
    }
}

// ============================================
// NOTIFICATIONS
// ============================================

function showSuccess(message) {
    // Implémentation simple avec alert (peut être amélioré)
    alert('✅ ' + message);
}

function showError(message) {
    alert('❌ Erreur : ' + message);
}

function showInfo(message, title = 'Info', duration = 3000) {
    alert('ℹ️ ' + title + '\n\n' + message);
}

// ============================================
// GESTION DES ERREURS FETCH
// ============================================

async function handleFetchError(response, result) {
    /**
     * Gère les erreurs de fetch et affiche un message approprié
     * Supporte les erreurs 422 avec détails de validation
     */
    
    if (!response.ok) {
        if (response.status === 422 && result.detail) {
            // Erreur de validation
            if (Array.isArray(result.errors) && result.errors.length > 0) {
                // Plusieurs erreurs
                const errorList = result.errors.join('\n• ');
                showError(result.detail + '\n\n• ' + errorList);
            } else {
                // Une seule erreur
                showError(result.detail);
            }
            
            // Mettre en évidence les champs en erreur
            if (result.field_errors) {
                Object.keys(result.field_errors).forEach(fieldName => {
                    const field = document.querySelector(`[name="${fieldName}"]`);
                    if (field) {
                        field.style.borderColor = 'var(--danger-color)';
                        field.addEventListener('input', function() {
                            this.style.borderColor = '';
                        }, { once: true });
                    }
                });
            }
        } else if (result && result.error) {
            // Erreur personnalisée du serveur
            showError(result.error);
        } else {
            // Erreur générique
            showError('Une erreur est survenue');
        }
    }
}

// ============================================
// UTILITAIRES
// ============================================

function formatNumber(num, decimals = 0) {
    return new Intl.NumberFormat('fr-FR', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(num);
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return new Intl.DateFormat('fr-FR').format(date);
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('fr-FR', {
        style: 'currency',
        currency: 'XOF',  // Franc CFA
        minimumFractionDigits: 0
    }).format(amount);
}

// ============================================
// INITIALISATION
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ MPPEEP Dashboard initialisé');
    
    // Fermer l'overlay au chargement
    hideGlobalLoading();
});
```

---

## 📊 RÉSUMÉ DES MODULES

| Module | Rôle | Technologies |
|--------|------|--------------|
| **Auth** | Authentification | FastAPI, JWT, bcrypt |
| **RH** | Gestion des demandes RH | FastAPI, SQLModel, Jinja2 |
| **Stock** | Gestion de stock | FastAPI, SQLModel, Decimal |
| **Personnel** | Gestion du personnel | FastAPI, SQLModel |
| **Budget** | Gestion budgétaire | FastAPI, SQLModel |
| **Performance** | Suivi de performance | FastAPI, SQLModel |
| **Workflow** | Configuration workflows | FastAPI, SQLModel |
| **Templates** | Interface web | Jinja2, HTML5 |
| **CSS** | Styles | CSS3, CSS Variables |
| **JavaScript** | Interactivité | Vanilla JS, Fetch API |

---

## 🔐 SÉCURITÉ

### Authentification
- ✅ JWT avec expiration (24h par défaut)
- ✅ Cookie `httpOnly` (protection XSS)
- ✅ Mot de passe hashé avec bcrypt
- ✅ Vérification du compte actif

### Validation
- ✅ Validation Pydantic côté serveur
- ✅ Validation JavaScript côté client
- ✅ Messages d'erreur détaillés et traduits

### Protection
- ✅ CORS configuré
- ✅ SQL paramétré (protection injection SQL)
- ✅ Dépendances avec `get_current_user`

---

## 🚀 PERFORMANCES

### Backend
- ✅ Sessions DB réutilisées (pas de nouvelle connexion par requête)
- ✅ Requêtes SQL optimisées (index, jointures)
- ✅ Logs structurés avec Request-ID

### Frontend
- ✅ CSS minifié en production
- ✅ JavaScript asynchrone (Fetch API)
- ✅ Loading overlay pour feedback utilisateur

---

**Fin de la documentation complète des modules MPPEEP** 🎉

Ces 4 documents couvrent l'intégralité du système :
1. Démarrage de l'application
2. Parcours d'une requête
3. Modèles et services
4. API et frontend

