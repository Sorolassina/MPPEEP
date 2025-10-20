# app/api/v1/endpoints/stock.py
"""
Routes API pour le module Gestion des Stocks
"""
from fastapi import APIRouter, Depends, Request, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlmodel import Session, select, func
from typing import Optional
from decimal import Decimal
from datetime import datetime, date
from pathlib import Path
import secrets

from app.db.session import get_session
from app.models.user import User
from app.models.stock import (
    Article, CategorieArticle, Fournisseur,
    MouvementStock, DemandeStock, Inventaire, LigneInventaire,
    LotPerissable, Amortissement
)
from app.services.stock_service import StockService
from app.api.v1.endpoints.auth import get_current_user
from app.templates import templates, get_template_context
from app.core.logging_config import get_logger
from app.services.activity_service import ActivityService

logger = get_logger(__name__)

router = APIRouter()


# ============================================
# PAGES HTML
# ============================================

@router.get("/aide", response_class=HTMLResponse, name="aide_stock")
def aide_stock(request: Request):
    """Page d'aide pour le module Stock"""
    from app.templates import templates, get_template_context
    return templates.TemplateResponse(
        "pages/aide_stock.html",
        get_template_context(request)
    )


@router.get("/", response_class=HTMLResponse, name="stock_home")
def stock_home(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Page principale du module Stocks"""
    
    return templates.TemplateResponse(
        "pages/stock.html",
        get_template_context(request)
    )


@router.get("/articles", response_class=HTMLResponse, name="stock_articles")
def stock_articles(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Page de gestion des articles"""
    
    # Récupérer tous les articles
    articles = session.exec(
        select(Article).order_by(Article.designation)
    ).all()
    
    # Récupérer les catégories
    categories = session.exec(
        select(CategorieArticle).order_by(CategorieArticle.libelle)
    ).all()
    
    return templates.TemplateResponse(
        "pages/stock_articles.html",
        get_template_context(
            request,
            articles=articles,
            categories=categories
        )
    )


@router.get("/mouvements", response_class=HTMLResponse, name="stock_mouvements")
def stock_mouvements(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Page des mouvements de stock"""
    
    # Récupérer les derniers mouvements
    mouvements = session.exec(
        select(MouvementStock)
        .order_by(MouvementStock.created_at.desc())
        .limit(50)
    ).all()
    
    # Récupérer tous les articles pour le mapping
    articles = session.exec(select(Article)).all()
    
    return templates.TemplateResponse(
        "pages/stock_mouvements.html",
        get_template_context(request, mouvements=mouvements, articles=articles)
    )


@router.get("/demandes", response_class=HTMLResponse, name="stock_demandes")
def stock_demandes(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Page des demandes de stock"""
    
    # Récupérer les demandes
    demandes = session.exec(
        select(DemandeStock)
        .order_by(DemandeStock.created_at.desc())
    ).all()
    
    return templates.TemplateResponse(
        "pages/stock_demandes.html",
        get_template_context(request, demandes=demandes)
    )


@router.get("/articles/new", response_class=HTMLResponse, name="stock_article_new")
def stock_article_new(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Formulaire de création d'article"""
    
    categories = session.exec(
        select(CategorieArticle).order_by(CategorieArticle.libelle)
    ).all()
    
    return templates.TemplateResponse(
        "pages/stock_article_form.html",
        get_template_context(request, categories=categories)
    )


@router.get("/articles/{article_id}", response_class=HTMLResponse, name="stock_article_detail")
def stock_article_detail(
    article_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Page de détail d'un article"""
    
    article = session.get(Article, article_id)
    if not article:
        # Rediriger vers la liste des articles au lieu d'afficher une erreur JSON
        return RedirectResponse(url=str(request.url_for("stock_articles")), status_code=303)
    
    # Récupérer la catégorie
    categorie = session.get(CategorieArticle, article.categorie_id) if article.categorie_id else None
    
    # Récupérer les derniers mouvements de cet article
    mouvements = session.exec(
        select(MouvementStock)
        .where(MouvementStock.article_id == article_id)
        .order_by(MouvementStock.created_at.desc())
        .limit(10)
    ).all()
    
    return templates.TemplateResponse(
        "pages/stock_article_detail.html",
        get_template_context(request, article=article, categorie=categorie, mouvements=mouvements)
    )


@router.get("/articles/{article_id}/edit", response_class=HTMLResponse, name="stock_article_edit")
def stock_article_edit(
    article_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Formulaire de modification d'article"""
    
    article = session.get(Article, article_id)
    if not article:
        # Rediriger vers la liste des articles au lieu d'afficher une erreur JSON
        return RedirectResponse(url=str(request.url_for("stock_articles")), status_code=303)
    
    categories = session.exec(
        select(CategorieArticle).order_by(CategorieArticle.libelle)
    ).all()
    
    return templates.TemplateResponse(
        "pages/stock_article_form.html",
        get_template_context(request, article=article, categories=categories)
    )


@router.get("/mouvements/new", response_class=HTMLResponse, name="stock_mouvement_new")
def stock_mouvement_new(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Formulaire d'enregistrement de mouvement"""
    
    articles = session.exec(
        select(Article).where(Article.actif == True).order_by(Article.designation)
    ).all()
    
    fournisseurs = session.exec(
        select(Fournisseur).where(Fournisseur.actif == True).order_by(Fournisseur.nom)
    ).all()
    
    return templates.TemplateResponse(
        "pages/stock_mouvement_form.html",
        get_template_context(request, articles=articles, fournisseurs=fournisseurs)
    )


@router.get("/demandes/new", response_class=HTMLResponse, name="stock_demande_new")
def stock_demande_new(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Formulaire de création de demande"""
    
    articles = session.exec(
        select(Article).where(Article.actif == True).order_by(Article.designation)
    ).all()
    
    return templates.TemplateResponse(
        "pages/stock_demande_form.html",
        get_template_context(request, articles=articles)
    )


@router.get("/fournisseurs", response_class=HTMLResponse, name="stock_fournisseurs")
def stock_fournisseurs(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Page des fournisseurs"""
    
    fournisseurs = session.exec(
        select(Fournisseur).order_by(Fournisseur.nom)
    ).all()
    
    return templates.TemplateResponse(
        "pages/stock_fournisseurs.html",
        get_template_context(request, fournisseurs=fournisseurs)
    )


@router.get("/inventaires", response_class=HTMLResponse, name="stock_inventaires")
def stock_inventaires(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Page des inventaires"""
    
    inventaires = session.exec(
        select(Inventaire).order_by(Inventaire.created_at.desc())
    ).all()
    
    return templates.TemplateResponse(
        "pages/stock_inventaires.html",
        get_template_context(request, inventaires=inventaires)
    )


@router.get("/rapports", response_class=HTMLResponse, name="stock_rapports")
def stock_rapports(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Page des rapports et statistiques"""
    
    return templates.TemplateResponse(
        "pages/stock_rapports.html",
        get_template_context(request)
    )


@router.get("/inventaires/new", response_class=HTMLResponse, name="stock_inventaire_new")
def stock_inventaire_new(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Formulaire de création d'inventaire"""
    
    return templates.TemplateResponse(
        "pages/stock_inventaire_form.html",
        get_template_context(request)
    )


@router.get("/inventaires/{inventaire_id}", response_class=HTMLResponse, name="stock_inventaire_detail")
def stock_inventaire_detail(
    inventaire_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Page de détail d'un inventaire"""
    
    inventaire = session.get(Inventaire, inventaire_id)
    if not inventaire:
        return RedirectResponse(url=str(request.url_for("stock_inventaires")), status_code=303)
    
    # Récupérer le responsable
    from app.models import User
    responsable = session.get(User, inventaire.responsable_id)
    
    # Récupérer les lignes d'inventaire
    lignes_db = session.exec(
        select(LigneInventaire)
        .where(LigneInventaire.inventaire_id == inventaire_id)
        .order_by(LigneInventaire.created_at)
    ).all()
    
    # Créer une liste enrichie avec les données des articles et compteurs
    lignes = []
    for ligne in lignes_db:
        article = session.get(Article, ligne.article_id)
        compteur = session.get(User, ligne.compteur_id) if ligne.compteur_id else None
        
        lignes.append({
            'id': ligne.id,
            'article_id': ligne.article_id,
            'article': article,
            'quantite_theorique': ligne.quantite_theorique,
            'quantite_physique': ligne.quantite_physique,
            'ecart': ligne.ecart,
            'observations': ligne.observations,
            'compteur_id': ligne.compteur_id,
            'compteur': compteur,
            'date_comptage': ligne.date_comptage
        })
    
    # Récupérer les articles non encore ajoutés
    articles_deja_ajoutes = [ligne['article_id'] for ligne in lignes]
    articles_disponibles = session.exec(
        select(Article)
        .where(
            Article.actif == True,
            Article.id.notin_(articles_deja_ajoutes) if articles_deja_ajoutes else True
        )
        .order_by(Article.code)
    ).all()
    
    return templates.TemplateResponse(
        "pages/stock_inventaire_detail.html",
        get_template_context(
            request,
            inventaire=inventaire,
            responsable=responsable,
            lignes=lignes,
            articles_disponibles=articles_disponibles
        )
    )


# ============================================
# API JSON - KPIs & STATS
# ============================================

@router.get("/api/kpis", response_class=JSONResponse, name="api_get_stock_kpis")
def api_kpis(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Récupère les KPIs du module stock"""
    try:
        kpis = StockService.get_kpis(session)
        return {"success": True, "data": kpis}
    except Exception as e:
        logger.error(f"Erreur récupération KPIs stock: {e}")
        return {"success": False, "error": str(e)}


@router.get("/api/alertes", response_class=JSONResponse, name="api_get_stock_alertes")
def api_alertes(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Récupère toutes les alertes de stock (ruptures, stock faible, surstock)"""
    try:
        alertes = StockService.get_alertes_stock(session)
        return {"success": True, "data": alertes}
    except Exception as e:
        logger.error(f"Erreur récupération alertes stock: {e}")
        return {"success": False, "error": str(e)}


# ============================================
# API JSON - ARTICLES
# ============================================

@router.get("/api/articles", response_class=JSONResponse, name="api_list_articles")
def api_list_articles(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    rupture: Optional[bool] = None
):
    """Liste des articles"""
    try:
        query = select(Article)
        
        if rupture:
            query = query.where(Article.quantite_stock <= Article.quantite_min)
        
        articles = session.exec(query.order_by(Article.designation)).all()
        
        return {
            "success": True,
            "data": [
                {
                    "id": a.id,
                    "code": a.code,
                    "designation": a.designation,
                    "unite": a.unite,
                    "quantite_stock": float(a.quantite_stock),
                    "quantite_min": float(a.quantite_min),
                    "prix_unitaire": float(a.prix_unitaire) if a.prix_unitaire else None,
                    "en_rupture": a.quantite_stock <= a.quantite_min
                }
                for a in articles
            ]
        }
    except Exception as e:
        logger.error(f"Erreur liste articles: {e}")
        return {"success": False, "error": str(e)}


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
    # NOUVEAUTÉ : Champs périssables
    est_perissable: Optional[str] = Form(None),
    duree_conservation_jours: Optional[int] = Form(None),
    seuil_alerte_peremption_jours: Optional[int] = Form(30),
    # NOUVEAUTÉ : Champs amortissement
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
        # Convertir les checkboxes en boolean
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
            duree_conservation_jours=duree_conservation_jours,
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
        
        # Enregistrer l'activité
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
        return {"success": False, "error": "Erreur lors de la création de l'article"}


@router.put("/api/articles/{article_id}", response_class=JSONResponse, name="api_update_article_put")
@router.patch("/api/articles/{article_id}", response_class=JSONResponse, name="api_update_article")
def api_update_article(
    article_id: int,
    designation: Optional[str] = Form(None),
    categorie_id: Optional[int] = Form(None),
    unite: Optional[str] = Form(None),
    quantite_min: Optional[float] = Form(None),
    quantite_max: Optional[float] = Form(None),
    prix_unitaire: Optional[float] = Form(None),
    emplacement: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    actif: Optional[bool] = Form(None),
    # NOUVEAUTÉ : Champs périssables
    est_perissable: Optional[str] = Form(None),
    duree_conservation_jours: Optional[int] = Form(None),
    seuil_alerte_peremption_jours: Optional[int] = Form(None),
    # NOUVEAUTÉ : Champs amortissement
    est_amortissable: Optional[str] = Form(None),
    date_acquisition: Optional[str] = Form(None),
    valeur_acquisition: Optional[float] = Form(None),
    duree_amortissement_annees: Optional[int] = Form(None),
    taux_amortissement: Optional[float] = Form(None),
    valeur_residuelle: Optional[float] = Form(None),
    methode_amortissement: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Met à jour un article"""
    try:
        article = session.get(Article, article_id)
        if not article:
            return {"success": False, "error": "Article introuvable"}
        
        # Mettre à jour uniquement les champs fournis
        if designation is not None:
            article.designation = designation
        if categorie_id is not None:
            article.categorie_id = categorie_id
        if unite is not None:
            article.unite = unite
        if quantite_min is not None:
            article.quantite_min = Decimal(str(quantite_min))
        if quantite_max is not None:
            article.quantite_max = Decimal(str(quantite_max))
        if prix_unitaire is not None:
            article.prix_unitaire = Decimal(str(prix_unitaire))
        if emplacement is not None:
            article.emplacement = emplacement
        if description is not None:
            article.description = description
        if actif is not None:
            article.actif = actif
        
        # NOUVEAUTÉ : Champs périssables
        if est_perissable is not None:
            article.est_perissable = est_perissable == "true"
        if duree_conservation_jours is not None:
            article.duree_conservation_jours = duree_conservation_jours
        if seuil_alerte_peremption_jours is not None:
            article.seuil_alerte_peremption_jours = seuil_alerte_peremption_jours
        
        # NOUVEAUTÉ : Champs amortissement
        if est_amortissable is not None:
            article.est_amortissable = est_amortissable == "true"
        if date_acquisition is not None:
            from datetime import datetime as dt
            try:
                article.date_acquisition = dt.strptime(date_acquisition, '%Y-%m-%d').date()
            except:
                pass
        if valeur_acquisition is not None:
            article.valeur_acquisition = Decimal(str(valeur_acquisition))
        if duree_amortissement_annees is not None:
            article.duree_amortissement_annees = duree_amortissement_annees
        if taux_amortissement is not None:
            article.taux_amortissement = Decimal(str(taux_amortissement))
        if valeur_residuelle is not None:
            article.valeur_residuelle = Decimal(str(valeur_residuelle))
        if methode_amortissement is not None:
            article.methode_amortissement = methode_amortissement
        
        article.updated_at = datetime.now()
        
        session.add(article)
        session.commit()
        session.refresh(article)
        
        # Enregistrer l'activité
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="update",
            target_type="stock_article",
            target_id=article.id,
            description=f"Modification de l'article {article.code} - {article.designation}",
            icon="✏️"
        )
        
        return {
            "success": True,
            "message": f"Article '{article.designation}' mis à jour avec succès"
        }
    except Exception as e:
        logger.error(f"Erreur mise à jour article: {e}")
        return {"success": False, "error": "Erreur lors de la mise à jour"}


@router.delete("/api/articles/{article_id}", response_class=JSONResponse, name="api_delete_article")
def api_delete_article(
    article_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Supprime un article (soft delete - désactivation)"""
    try:
        article = session.get(Article, article_id)
        if not article:
            return {"success": False, "error": "Article introuvable"}
        
        # Vérifier s'il y a des mouvements liés
        mouvements_count = session.exec(
            select(func.count(MouvementStock.id)).where(
                MouvementStock.article_id == article_id
            )
        ).one()
        
        if mouvements_count > 0:
            # Soft delete - désactiver l'article
            article.actif = False
            article.updated_at = datetime.now()
            session.add(article)
            message = f"Article '{article.designation}' désactivé (il a {mouvements_count} mouvement(s) associé(s))"
        else:
            # Hard delete - suppression réelle
            session.delete(article)
            message = f"Article '{article.designation}' supprimé définitivement"
        
        session.commit()
        
        # Enregistrer l'activité
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="delete",
            target_type="stock_article",
            target_id=article_id,
            description=f"Suppression de l'article {article.code}",
            icon="🗑️"
        )
        
        return {
            "success": True,
            "message": message
        }
    except Exception as e:
        logger.error(f"Erreur suppression article: {e}")
        return {"success": False, "error": "Erreur lors de la suppression"}


# ============================================
# API JSON - MOUVEMENTS
# ============================================

@router.post("/api/mouvements", response_class=JSONResponse, name="api_create_mouvement")
async def api_create_mouvement(
    article_id: int = Form(...),
    type_mouvement: str = Form(...),
    quantite: float = Form(...),
    motif: str = Form(...),
    fournisseur_id: Optional[int] = Form(None),
    beneficiaire: Optional[str] = Form(None),
    prix_unitaire_reel: Optional[float] = Form(None),
    observations: Optional[str] = Form(None),
    document: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Enregistre un mouvement de stock avec document justificatif et prix optionnels"""
    try:
        # Gérer l'upload du document si présent
        document_path = None
        document_filename = None
        
        if document and document.filename:
            # Créer le dossier uploads/stock si nécessaire
            upload_dir = Path("uploads/stock")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Générer un nom de fichier unique
            file_extension = Path(document.filename).suffix
            unique_filename = f"mouvement_{secrets.token_hex(8)}{file_extension}"
            file_path = upload_dir / unique_filename
            
            # Sauvegarder le fichier
            content = await document.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            document_path = f"stock/{unique_filename}"
            document_filename = document.filename
            
            logger.info(f"Document uploadé : {document_filename} -> {document_path}")
        
        # Vérifier le stock disponible pour les sorties
        if type_mouvement == "SORTIE":
            disponible, msg_alerte = StockService.verifier_stock_disponible(
                session=session,
                article_id=article_id,
                quantite_demandee=Decimal(str(quantite))
            )
            if not disponible:
                return {"success": False, "error": msg_alerte}
        
        # Calculer le montant total si prix fourni
        montant_total = None
        if prix_unitaire_reel is not None:
            montant_total = Decimal(str(quantite)) * Decimal(str(prix_unitaire_reel))
        
        # Enregistrer le mouvement
        mouvement, alerte = StockService.enregistrer_mouvement(
            session=session,
            article_id=article_id,
            type_mouvement=type_mouvement,
            quantite=Decimal(str(quantite)),
            motif=motif,
            user_id=current_user.id,
            fournisseur_id=fournisseur_id,
            beneficiaire=beneficiaire,
            prix_unitaire_reel=Decimal(str(prix_unitaire_reel)) if prix_unitaire_reel else None,
            montant_total=montant_total,
            observations=observations,
            document_path=document_path,
            document_filename=document_filename
        )
        
        # Enregistrer l'activité
        article = session.get(Article, article_id)
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="create",
            target_type="stock_mouvement",
            target_id=mouvement.id,
            description=f"{type_mouvement} : {article.designation} - {quantite} {article.unite}",
            icon="📦"
        )
        
        return {
            "success": True,
            "message": "Mouvement enregistré avec succès",
            "alerte": alerte,  # Alerte de stock faible si applicable
            "data": {
                "id": mouvement.id,
                "quantite_avant": float(mouvement.quantite_avant),
                "quantite_apres": float(mouvement.quantite_apres),
                "document_path": document_path
            }
        }
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Erreur création mouvement: {e}", exc_info=True)
        return {"success": False, "error": "Erreur lors de l'enregistrement du mouvement"}


@router.get("/api/mouvements/{mouvement_id}", response_class=JSONResponse, name="api_get_mouvement")
async def api_get_mouvement(
    mouvement_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Récupérer les détails d'un mouvement"""
    try:
        mouvement = session.get(MouvementStock, mouvement_id)
        if not mouvement:
            return {"success": False, "error": "Mouvement non trouvé"}
        
        return {
            "success": True,
            "data": {
                "id": mouvement.id,
                "article_id": mouvement.article_id,
                "type_mouvement": mouvement.type_mouvement,
                "quantite": float(mouvement.quantite),
                "quantite_avant": float(mouvement.quantite_avant),
                "quantite_apres": float(mouvement.quantite_apres),
                "motif": mouvement.motif,
                "fournisseur_id": mouvement.fournisseur_id,
                "beneficiaire": mouvement.beneficiaire,
                "prix_unitaire_reel": float(mouvement.prix_unitaire_reel) if mouvement.prix_unitaire_reel else None,
                "montant_total": float(mouvement.montant_total) if mouvement.montant_total else None,
                "observations": mouvement.observations,
                "date_mouvement": mouvement.date_mouvement.isoformat(),
                "document_path": mouvement.document_path,
                "document_filename": mouvement.document_filename
            }
        }
    except Exception as e:
        logger.error(f"Erreur récupération mouvement: {e}", exc_info=True)
        return {"success": False, "error": "Erreur lors de la récupération du mouvement"}


@router.delete("/api/mouvements/{mouvement_id}", response_class=JSONResponse, name="api_delete_mouvement")
async def api_delete_mouvement(
    mouvement_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Supprimer un mouvement de stock"""
    try:
        # Récupérer le mouvement
        mouvement = session.get(MouvementStock, mouvement_id)
        if not mouvement:
            return {"success": False, "error": "Mouvement non trouvé"}
        
        # Récupérer l'article pour recalculer le stock
        article = session.get(Article, mouvement.article_id)
        if not article:
            return {"success": False, "error": "Article non trouvé"}
        
        # Inverser le mouvement pour recalculer le stock
        if mouvement.type_mouvement == "ENTREE":
            # Si c'était une entrée, on retire la quantité
            article.quantite_stock -= mouvement.quantite
        elif mouvement.type_mouvement == "SORTIE":
            # Si c'était une sortie, on rajoute la quantité
            article.quantite_stock += mouvement.quantite
        elif mouvement.type_mouvement == "AJUSTEMENT":
            # Pour un ajustement, on revient à l'état avant
            article.quantite_stock = mouvement.quantite_avant
        
        # Supprimer le document associé si existant
        if mouvement.document_path:
            document_file = Path("uploads") / mouvement.document_path
            if document_file.exists():
                document_file.unlink()
        
        # Enregistrer l'activité avant suppression
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="delete",
            target_type="stock_mouvement",
            target_id=mouvement.id,
            description=f"Suppression {mouvement.type_mouvement} : {article.designation} - {mouvement.quantite} {article.unite}",
            icon="🗑️"
        )
        
        # Supprimer le mouvement
        session.delete(mouvement)
        session.add(article)
        session.commit()
        
        logger.info(f"Mouvement {mouvement_id} supprimé par {current_user.email}")
        
        return {
            "success": True,
            "message": "Mouvement supprimé avec succès"
        }
        
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur suppression mouvement: {e}", exc_info=True)
        return {"success": False, "error": "Erreur lors de la suppression du mouvement"}


# ============================================
# API JSON - DEMANDES
# ============================================

@router.post("/api/demandes", response_class=JSONResponse, name="api_create_demande")
async def api_create_demande(
    type_demande: str = Form(...),
    article_id: int = Form(...),
    quantite_demandee: float = Form(...),
    motif: str = Form(...),
    service_demandeur: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    document: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Crée une demande de stock avec document justificatif optionnel"""
    try:
        # Gérer l'upload du document si présent
        document_path = None
        document_filename = None
        
        if document and document.filename:
            # Créer le dossier uploads/stock si nécessaire
            upload_dir = Path("uploads/stock")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Générer un nom de fichier unique
            file_extension = Path(document.filename).suffix
            unique_filename = f"demande_{secrets.token_hex(8)}{file_extension}"
            file_path = upload_dir / unique_filename
            
            # Sauvegarder le fichier
            content = await document.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            document_path = f"stock/{unique_filename}"
            document_filename = document.filename
            
            logger.info(f"Document uploadé : {document_filename} -> {document_path}")
        
        # Créer la demande
        demande = StockService.creer_demande(
            session=session,
            type_demande=type_demande,
            demandeur_id=current_user.id,
            article_id=article_id,
            quantite_demandee=Decimal(str(quantite_demandee)),
            motif=motif,
            service_demandeur=service_demandeur,
            description=description,
            document_path=document_path,
            document_filename=document_filename
        )
        
        # Enregistrer l'activité
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="create",
            target_type="stock_demande",
            target_id=demande.id,
            description=f"Demande {demande.numero} créée",
            icon="📝"
        )
        
        return {
            "success": True,
            "message": f"Demande {demande.numero} créée avec succès",
            "data": {
                "id": demande.id,
                "numero": demande.numero,
                "document_path": document_path
            }
        }
    except Exception as e:
        logger.error(f"Erreur création demande: {e}", exc_info=True)
        return {"success": False, "error": "Erreur lors de la création de la demande"}


@router.post("/api/demandes/{demande_id}/valider", response_class=JSONResponse, name="api_valider_demande")
def api_valider_demande(
    demande_id: int,
    accepte: bool = Form(...),
    commentaire: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Valide ou rejette une demande"""
    try:
        demande, alerte = StockService.valider_demande(
            session=session,
            demande_id=demande_id,
            valideur_id=current_user.id,
            accepte=accepte,
            commentaire=commentaire
        )
        
        # Enregistrer l'activité
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="update",
            target_type="stock_demande",
            target_id=demande.id,
            description=f"Demande {demande.numero} {'validée' if accepte else 'rejetée'}",
            icon="✅" if accepte else "❌"
        )
        
        return {
            "success": True,
            "message": f"Demande {'validée' if accepte else 'rejetée'} avec succès",
            "alerte": alerte
        }
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Erreur validation demande: {e}")
        return {"success": False, "error": "Erreur lors de la validation"}


# ============================================
# API JSON - DONNÉES GRAPHIQUES
# ============================================

@router.get("/api/stats/mouvements-mois", response_class=JSONResponse, name="api_get_stats_mouvements_mois")
def api_stats_mouvements_mois(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Statistiques des mouvements par mois (12 derniers mois)"""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import extract, and_
        
        # Date de début (12 mois avant)
        date_debut = datetime.now() - timedelta(days=365)
        
        # Grouper par mois
        mouvements_entree = session.exec(
            select(
                extract('month', MouvementStock.date_mouvement).label('mois'),
                extract('year', MouvementStock.date_mouvement).label('annee'),
                func.count(MouvementStock.id).label('count')
            ).where(
                and_(
                    MouvementStock.type_mouvement == "ENTREE",
                    MouvementStock.date_mouvement >= date_debut.date()
                )
            ).group_by('mois', 'annee').order_by('annee', 'mois')
        ).all()
        
        mouvements_sortie = session.exec(
            select(
                extract('month', MouvementStock.date_mouvement).label('mois'),
                extract('year', MouvementStock.date_mouvement).label('annee'),
                func.count(MouvementStock.id).label('count')
            ).where(
                and_(
                    MouvementStock.type_mouvement == "SORTIE",
                    MouvementStock.date_mouvement >= date_debut.date()
                )
            ).group_by('mois', 'annee').order_by('annee', 'mois')
        ).all()
        
        return {
            "success": True,
            "data": {
                "entrees": [{"mois": m.mois, "annee": m.annee, "count": m.count} for m in mouvements_entree],
                "sorties": [{"mois": m.mois, "annee": m.annee, "count": m.count} for m in mouvements_sortie]
            }
        }
    except Exception as e:
        logger.error(f"Erreur stats mouvements: {e}")
        return {"success": False, "error": str(e)}


@router.get("/api/stats/articles-categorie", response_class=JSONResponse, name="api_get_stats_articles_categorie")
def api_stats_articles_categorie(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Répartition des articles par catégorie"""
    try:
        stats = session.exec(
            select(
                CategorieArticle.libelle,
                func.count(Article.id).label('count')
            ).join(
                Article, Article.categorie_id == CategorieArticle.id
            ).where(
                Article.actif == True
            ).group_by(CategorieArticle.libelle)
        ).all()
        
        return {
            "success": True,
            "data": [{"categorie": s.libelle, "count": s.count} for s in stats]
        }
    except Exception as e:
        logger.error(f"Erreur stats catégories: {e}")
        return {"success": False, "error": str(e)}


# ============================================
# API JSON - GESTION DES CATÉGORIES
# ============================================

@router.get("/api/categories", response_class=JSONResponse, name="api_list_categories")
def api_list_categories(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Liste des catégories d'articles"""
    try:
        categories = session.exec(
            select(CategorieArticle).order_by(CategorieArticle.libelle)
        ).all()
        
        return {
            "success": True,
            "data": [
                {
                    "id": c.id,
                    "code": c.code,
                    "libelle": c.libelle,
                    "description": c.description
                }
                for c in categories
            ]
        }
    except Exception as e:
        logger.error(f"Erreur liste catégories: {e}")
        return {"success": False, "error": str(e)}


@router.post("/api/categories", response_class=JSONResponse, name="api_create_categorie")
def api_create_categorie(
    code: str = Form(...),
    libelle: str = Form(...),
    description: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Crée une nouvelle catégorie"""
    try:
        # Vérifier que le code est unique
        existing = session.exec(
            select(CategorieArticle).where(CategorieArticle.code == code)
        ).first()
        
        if existing:
            return {"success": False, "error": f"Une catégorie avec le code '{code}' existe déjà"}
        
        categorie = CategorieArticle(
            code=code,
            libelle=libelle,
            description=description
        )
        
        session.add(categorie)
        session.commit()
        session.refresh(categorie)
        
        logger.info(f"Catégorie créée : {code} - {libelle}")
        
        return {
            "success": True,
            "message": f"Catégorie '{libelle}' créée avec succès",
            "data": {"id": categorie.id, "code": categorie.code}
        }
    except Exception as e:
        logger.error(f"Erreur création catégorie: {e}")
        return {"success": False, "error": "Erreur lors de la création"}


@router.get("/api/generer-code/{categorie_id}", response_class=JSONResponse, name="api_generer_code_article")
def api_generer_code_article(
    categorie_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Génère automatiquement le code d'un article basé sur la catégorie"""
    try:
        # Récupérer la catégorie
        categorie = session.get(CategorieArticle, categorie_id)
        if not categorie:
            return {"success": False, "error": "Catégorie introuvable"}
        
        # Compter les articles existants dans cette catégorie
        count = session.exec(
            select(func.count(Article.id)).where(
                Article.categorie_id == categorie_id
            )
        ).one()
        
        # Générer le code : CODE_CATEGORIE-XXX
        numero = str(count + 1).zfill(3)
        code_genere = f"{categorie.code}-{numero}"
        
        return {
            "success": True,
            "data": {
                "code": code_genere,
                "categorie_code": categorie.code,
                "numero": count + 1
            }
        }
    except Exception as e:
        logger.error(f"Erreur génération code: {e}")
        return {"success": False, "error": "Erreur lors de la génération du code"}


# ============================================
# API FOURNISSEURS
# ============================================

@router.post("/api/fournisseurs", response_class=JSONResponse, name="api_create_fournisseur")
def api_create_fournisseur(
    code: str = Form(...),
    nom: str = Form(...),
    telephone: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    adresse: Optional[str] = Form(None),
    actif: Optional[bool] = Form(True),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Créer un nouveau fournisseur"""
    try:
        # Vérifier si le code existe déjà
        existing = session.exec(
            select(Fournisseur).where(Fournisseur.code == code)
        ).first()
        
        if existing:
            return {"success": False, "error": f"Le code {code} existe déjà"}
        
        fournisseur = Fournisseur(
            code=code,
            nom=nom,
            telephone=telephone,
            email=email,
            adresse=adresse,
            actif=actif if actif is not None else True
        )
        
        session.add(fournisseur)
        session.commit()
        session.refresh(fournisseur)
        
        # Enregistrer l'activité
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="create",
            target_type="fournisseur",
            target_id=fournisseur.id,
            description=f"Création du fournisseur {fournisseur.code} - {fournisseur.nom}",
            icon="🏢"
        )
        
        return {
            "success": True,
            "message": f"Fournisseur '{nom}' créé avec succès",
            "data": {"id": fournisseur.id}
        }
    except Exception as e:
        logger.error(f"Erreur création fournisseur: {e}")
        return {"success": False, "error": "Erreur lors de la création du fournisseur"}


@router.get("/api/fournisseurs/{fournisseur_id}", response_class=JSONResponse, name="api_get_fournisseur")
def api_get_fournisseur(
    fournisseur_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Récupérer les données d'un fournisseur"""
    fournisseur = session.get(Fournisseur, fournisseur_id)
    
    if not fournisseur:
        return {"success": False, "error": "Fournisseur introuvable"}
    
    return {
        "success": True,
        "data": {
            "id": fournisseur.id,
            "code": fournisseur.code,
            "nom": fournisseur.nom,
            "telephone": fournisseur.telephone,
            "email": fournisseur.email,
            "adresse": fournisseur.adresse,
            "actif": fournisseur.actif
        }
    }


@router.put("/api/fournisseurs/{fournisseur_id}", response_class=JSONResponse, name="api_update_fournisseur")
def api_update_fournisseur(
    fournisseur_id: int,
    code: Optional[str] = Form(None),
    nom: Optional[str] = Form(None),
    telephone: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    adresse: Optional[str] = Form(None),
    actif: Optional[bool] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Mettre à jour un fournisseur"""
    try:
        fournisseur = session.get(Fournisseur, fournisseur_id)
        
        if not fournisseur:
            return {"success": False, "error": "Fournisseur introuvable"}
        
        # Vérifier l'unicité du code si changé
        if code and code != fournisseur.code:
            existing = session.exec(
                select(Fournisseur).where(Fournisseur.code == code)
            ).first()
            if existing:
                return {"success": False, "error": f"Le code {code} existe déjà"}
            fournisseur.code = code
        
        if nom is not None:
            fournisseur.nom = nom
        if telephone is not None:
            fournisseur.telephone = telephone
        if email is not None:
            fournisseur.email = email
        if adresse is not None:
            fournisseur.adresse = adresse
        if actif is not None:
            fournisseur.actif = actif
        
        session.add(fournisseur)
        session.commit()
        session.refresh(fournisseur)
        
        # Enregistrer l'activité
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="update",
            target_type="fournisseur",
            target_id=fournisseur.id,
            description=f"Modification du fournisseur {fournisseur.code} - {fournisseur.nom}",
            icon="✏️"
        )
        
        return {
            "success": True,
            "message": f"Fournisseur '{fournisseur.nom}' mis à jour avec succès"
        }
    except Exception as e:
        logger.error(f"Erreur mise à jour fournisseur: {e}")
        return {"success": False, "error": "Erreur lors de la mise à jour"}


@router.delete("/api/fournisseurs/{fournisseur_id}", response_class=JSONResponse, name="api_delete_fournisseur")
def api_delete_fournisseur(
    fournisseur_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Supprimer un fournisseur"""
    try:
        fournisseur = session.get(Fournisseur, fournisseur_id)
        
        if not fournisseur:
            return {"success": False, "error": "Fournisseur introuvable"}
        
        # Vérifier s'il y a des mouvements liés
        mouvements_count = session.exec(
            select(func.count(MouvementStock.id)).where(
                MouvementStock.fournisseur_id == fournisseur_id
            )
        ).one()
        
        if mouvements_count > 0:
            # Désactiver au lieu de supprimer
            fournisseur.actif = False
            session.add(fournisseur)
            session.commit()
            
            return {
                "success": True,
                "message": f"Le fournisseur a été désactivé (il a {mouvements_count} mouvement(s) associé(s))"
            }
        else:
            # Supprimer complètement
            nom = fournisseur.nom
            session.delete(fournisseur)
            session.commit()
            
            # Enregistrer l'activité
            ActivityService.log_activity(
                db_session=session,
                user_id=current_user.id,
                user_email=current_user.email,
                user_full_name=current_user.full_name,
                action_type="delete",
                target_type="fournisseur",
                target_id=fournisseur_id,
                description=f"Suppression du fournisseur {nom}",
                icon="🗑️"
            )
            
            return {
                "success": True,
                "message": f"Fournisseur '{nom}' supprimé avec succès"
            }
    except Exception as e:
        logger.error(f"Erreur suppression fournisseur: {e}")
        return {"success": False, "error": "Erreur lors de la suppression"}


# ============================================
# API RAPPORTS
# ============================================

@router.get("/api/rapports/valorisation", response_class=JSONResponse, name="api_rapport_valorisation")
def api_rapport_valorisation(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Rapport de valorisation du stock"""
    try:
        # Valorisation totale
        valeur_totale = session.exec(
            select(func.sum(Article.quantite_stock * Article.prix_unitaire))
            .where(Article.actif == True)
        ).one() or 0
        
        nb_articles = session.exec(
            select(func.count(Article.id)).where(Article.actif == True)
        ).one()
        
        # Valorisation par catégorie
        par_categorie = session.exec(
            select(
                CategorieArticle.libelle,
                func.count(Article.id).label('nb_articles'),
                func.sum(Article.quantite_stock).label('quantite_totale'),
                func.sum(Article.quantite_stock * Article.prix_unitaire).label('valeur')
            )
            .join(Article, Article.categorie_id == CategorieArticle.id)
            .where(Article.actif == True)
            .group_by(CategorieArticle.id, CategorieArticle.libelle)
        ).all()
        
        return {
            "success": True,
            "data": {
                "valeur_totale": float(valeur_totale),
                "nb_articles": nb_articles,
                "par_categorie": [
                    {
                        "categorie": row[0],
                        "nb_articles": row[1],
                        "quantite_totale": float(row[2] or 0),
                        "valeur": float(row[3] or 0)
                    }
                    for row in par_categorie
                ]
            }
        }
    except Exception as e:
        logger.error(f"Erreur rapport valorisation: {e}")
        return {"success": False, "error": "Erreur lors de la génération du rapport"}


@router.get("/api/rapports/mouvements", response_class=JSONResponse, name="api_rapport_mouvements")
def api_rapport_mouvements(
    mois: int = 6,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Rapport des mouvements"""
    try:
        from datetime import timedelta
        date_debut = date.today().replace(day=1) - timedelta(days=mois*30)
        
        # Total entrées/sorties
        entrees = session.exec(
            select(func.count(MouvementStock.id))
            .where(
                MouvementStock.type_mouvement == "ENTREE",
                MouvementStock.date_mouvement >= date_debut
            )
        ).one()
        
        sorties = session.exec(
            select(func.count(MouvementStock.id))
            .where(
                MouvementStock.type_mouvement == "SORTIE",
                MouvementStock.date_mouvement >= date_debut
            )
        ).one()
        
        # Par mois (simplifié - en production, utiliser des requêtes plus avancées)
        mouvements = session.exec(
            select(MouvementStock)
            .where(MouvementStock.date_mouvement >= date_debut)
            .order_by(MouvementStock.date_mouvement)
        ).all()
        
        # Grouper par mois
        from collections import defaultdict
        par_mois = defaultdict(lambda: {"entrees": 0, "sorties": 0})
        
        for mvt in mouvements:
            mois_key = mvt.date_mouvement.strftime("%Y-%m")
            if mvt.type_mouvement == "ENTREE":
                par_mois[mois_key]["entrees"] += 1
            elif mvt.type_mouvement == "SORTIE":
                par_mois[mois_key]["sorties"] += 1
        
        return {
            "success": True,
            "data": {
                "total_entrees": entrees,
                "total_sorties": sorties,
                "par_mois": [
                    {
                        "mois": mois_key,
                        "entrees": data["entrees"],
                        "sorties": data["sorties"]
                    }
                    for mois_key, data in sorted(par_mois.items())
                ]
            }
        }
    except Exception as e:
        logger.error(f"Erreur rapport mouvements: {e}")
        return {"success": False, "error": "Erreur lors de la génération du rapport"}


@router.get("/api/rapports/fournisseurs", response_class=JSONResponse, name="api_rapport_fournisseurs")
def api_rapport_fournisseurs(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Rapport des achats par fournisseur"""
    try:
        fournisseurs_stats = session.exec(
            select(
                Fournisseur.nom,
                func.count(MouvementStock.id).label('nb_mouvements'),
                func.sum(MouvementStock.quantite).label('quantite_totale'),
                func.sum(MouvementStock.montant_total).label('montant_total')
            )
            .join(MouvementStock, MouvementStock.fournisseur_id == Fournisseur.id)
            .where(MouvementStock.type_mouvement == "ENTREE")
            .group_by(Fournisseur.id, Fournisseur.nom)
            .order_by(func.count(MouvementStock.id).desc())
        ).all()
        
        return {
            "success": True,
            "data": [
                {
                    "nom": row[0],
                    "nb_mouvements": row[1],
                    "quantite_totale": float(row[2] or 0),
                    "montant_total": float(row[3] or 0)
                }
                for row in fournisseurs_stats
            ]
        }
    except Exception as e:
        logger.error(f"Erreur rapport fournisseurs: {e}")
        return {"success": False, "error": "Erreur lors de la génération du rapport"}


# ============================================
# API INVENTAIRES
# ============================================

@router.post("/api/inventaires", response_class=JSONResponse, name="api_create_inventaire")
def api_create_inventaire(
    numero: str = Form(...),
    libelle: str = Form(...),
    date_debut: str = Form(...),
    date_fin: Optional[str] = Form(None),
    observations: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Créer un nouvel inventaire"""
    try:
        from datetime import datetime as dt
        
        # Vérifier si le numéro existe déjà
        existing = session.exec(
            select(Inventaire).where(Inventaire.numero == numero)
        ).first()
        
        if existing:
            return {"success": False, "error": f"Le numéro {numero} existe déjà"}
        
        inventaire = Inventaire(
            numero=numero,
            libelle=libelle,
            date_debut=dt.strptime(date_debut, '%Y-%m-%d').date(),
            date_fin=dt.strptime(date_fin, '%Y-%m-%d').date() if date_fin else None,
            statut="EN_COURS",
            observations=observations,
            responsable_id=current_user.id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        session.add(inventaire)
        session.commit()
        session.refresh(inventaire)
        
        # Enregistrer l'activité
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="create",
            target_type="inventaire",
            target_id=inventaire.id,
            description=f"Création de l'inventaire {inventaire.numero}",
            icon="📋"
        )
        
        return {
            "success": True,
            "message": f"Inventaire '{numero}' créé avec succès",
            "data": {"id": inventaire.id}
        }
    except Exception as e:
        logger.error(f"Erreur création inventaire: {e}")
        return {"success": False, "error": "Erreur lors de la création de l'inventaire"}


@router.post("/api/inventaires/{inventaire_id}/lignes", response_class=JSONResponse, name="api_add_lignes_inventaire")
async def api_add_lignes_inventaire(
    inventaire_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Ajouter des articles à un inventaire"""
    try:
        body = await request.json()
        articles_ids = body.get('articles', [])
        
        if not articles_ids:
            return {"success": False, "error": "Aucun article sélectionné"}
        
        inventaire = session.get(Inventaire, inventaire_id)
        if not inventaire:
            return {"success": False, "error": "Inventaire introuvable"}
        
        if inventaire.statut != "EN_COURS":
            return {"success": False, "error": "Cet inventaire est clôturé"}
        
        lignes_creees = 0
        for article_id in articles_ids:
            article = session.get(Article, article_id)
            if not article:
                continue
            
            # Vérifier si l'article n'est pas déjà dans l'inventaire
            existing = session.exec(
                select(LigneInventaire).where(
                    LigneInventaire.inventaire_id == inventaire_id,
                    LigneInventaire.article_id == article_id
                )
            ).first()
            
            if existing:
                continue
            
            ligne = LigneInventaire(
                inventaire_id=inventaire_id,
                article_id=article_id,
                quantite_theorique=article.quantite_stock,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(ligne)
            lignes_creees += 1
        
        session.commit()
        
        return {
            "success": True,
            "message": f"{lignes_creees} article(s) ajouté(s) à l'inventaire"
        }
    except Exception as e:
        logger.error(f"Erreur ajout lignes inventaire: {e}")
        return {"success": False, "error": "Erreur lors de l'ajout des articles"}


@router.get("/api/inventaires/lignes/{ligne_id}", response_class=JSONResponse, name="api_get_ligne_inventaire")
def api_get_ligne_inventaire(
    ligne_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Récupérer les données d'une ligne d'inventaire"""
    ligne = session.get(LigneInventaire, ligne_id)
    
    if not ligne:
        return {"success": False, "error": "Ligne introuvable"}
    
    article = session.get(Article, ligne.article_id)
    
    return {
        "success": True,
        "data": {
            "id": ligne.id,
            "article_code": article.code if article else "N/A",
            "article_designation": article.designation if article else "N/A",
            "quantite_theorique": float(ligne.quantite_theorique),
            "quantite_physique": float(ligne.quantite_physique) if ligne.quantite_physique is not None else None,
            "observations": ligne.observations
        }
    }


@router.post("/api/inventaires/lignes/{ligne_id}/compter", response_class=JSONResponse, name="api_compter_ligne_inventaire")
def api_compter_ligne_inventaire(
    ligne_id: int,
    quantite_physique: float = Form(...),
    observations: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Enregistrer le comptage d'une ligne d'inventaire"""
    try:
        ligne = session.get(LigneInventaire, ligne_id)
        
        if not ligne:
            return {"success": False, "error": "Ligne introuvable"}
        
        inventaire = session.get(Inventaire, ligne.inventaire_id)
        if inventaire.statut != "EN_COURS":
            return {"success": False, "error": "Cet inventaire est clôturé"}
        
        # Mettre à jour la ligne
        ligne.quantite_physique = Decimal(str(quantite_physique))
        ligne.ecart = ligne.quantite_physique - ligne.quantite_theorique
        ligne.observations = observations
        ligne.compteur_id = current_user.id
        ligne.date_comptage = date.today()
        ligne.updated_at = datetime.now()
        
        session.add(ligne)
        session.commit()
        
        return {
            "success": True,
            "message": "Comptage enregistré avec succès"
        }
    except Exception as e:
        logger.error(f"Erreur comptage ligne: {e}")
        return {"success": False, "error": "Erreur lors de l'enregistrement du comptage"}


@router.delete("/api/inventaires/lignes/{ligne_id}", response_class=JSONResponse, name="api_delete_ligne_inventaire")
def api_delete_ligne_inventaire(
    ligne_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Supprimer une ligne d'inventaire"""
    try:
        ligne = session.get(LigneInventaire, ligne_id)
        
        if not ligne:
            return {"success": False, "error": "Ligne introuvable"}
        
        inventaire = session.get(Inventaire, ligne.inventaire_id)
        if inventaire.statut != "EN_COURS":
            return {"success": False, "error": "Impossible de modifier un inventaire clôturé"}
        
        session.delete(ligne)
        session.commit()
        
        return {
            "success": True,
            "message": "Article retiré de l'inventaire"
        }
    except Exception as e:
        logger.error(f"Erreur suppression ligne: {e}")
        return {"success": False, "error": "Erreur lors de la suppression"}


@router.post("/api/inventaires/{inventaire_id}/cloturer", response_class=JSONResponse, name="api_cloturer_inventaire")
def api_cloturer_inventaire(
    inventaire_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Clôturer un inventaire"""
    try:
        inventaire = session.get(Inventaire, inventaire_id)
        
        if not inventaire:
            return {"success": False, "error": "Inventaire introuvable"}
        
        if inventaire.statut != "EN_COURS":
            return {"success": False, "error": "Cet inventaire est déjà clôturé"}
        
        # Vérifier que tous les articles ont été comptés
        lignes_non_comptees = session.exec(
            select(func.count(LigneInventaire.id))
            .where(
                LigneInventaire.inventaire_id == inventaire_id,
                LigneInventaire.quantite_physique.is_(None)
            )
        ).one()
        
        if lignes_non_comptees > 0:
            return {
                "success": False,
                "error": f"Il reste {lignes_non_comptees} article(s) non compté(s)"
            }
        
        # Clôturer l'inventaire
        inventaire.statut = "CLOTURE"
        inventaire.date_fin = date.today()
        inventaire.updated_at = datetime.now()
        
        session.add(inventaire)
        session.commit()
        
        # Enregistrer l'activité
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="update",
            target_type="inventaire",
            target_id=inventaire.id,
            description=f"Clôture de l'inventaire {inventaire.numero}",
            icon="🔒"
        )
        
        return {
            "success": True,
            "message": f"Inventaire '{inventaire.numero}' clôturé avec succès"
        }
    except Exception as e:
        logger.error(f"Erreur clôture inventaire: {e}")
        return {"success": False, "error": "Erreur lors de la clôture"}


# ============================================
# NOUVEAUTÉ : GESTION DES LOTS PÉRISSABLES
# ============================================

@router.get("/lots-perissables", response_class=HTMLResponse, name="stock_lots_perissables")
def stock_lots_perissables(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Page de gestion des lots périssables"""
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
            select(LotPerissable)
            .order_by(LotPerissable.date_peremption)
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


@router.post("/api/lots-perissables", response_class=JSONResponse, name="api_create_lot_perissable")
def api_create_lot_perissable(
    article_id: int = Form(...),
    numero_lot: str = Form(...),
    date_peremption: str = Form(...),
    quantite: float = Form(...),
    date_fabrication: Optional[str] = Form(None),
    fournisseur_id: Optional[int] = Form(None),
    observations: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Crée un nouveau lot périssable"""
    try:
        from datetime import datetime as dt
        
        # Convertir les dates
        date_perem = dt.strptime(date_peremption, '%Y-%m-%d').date()
        date_fab = dt.strptime(date_fabrication, '%Y-%m-%d').date() if date_fabrication else None
        
        # Créer le lot
        lot = StockService.creer_lot_perissable(
            session=session,
            article_id=article_id,
            numero_lot=numero_lot,
            quantite=Decimal(str(quantite)),
            date_peremption=date_perem,
            date_fabrication=date_fab,
            fournisseur_id=fournisseur_id,
            observations=observations
        )
        
        # Enregistrer l'activité
        article = session.get(Article, article_id)
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="create",
            target_type="lot_perissable",
            target_id=lot.id,
            description=f"Création du lot {numero_lot} - {article.designation if article else 'Article'}",
            icon="🍃"
        )
        
        return {
            "success": True,
            "message": f"Lot périssable '{numero_lot}' créé avec succès",
            "data": {"id": lot.id, "numero_lot": lot.numero_lot}
        }
    except Exception as e:
        logger.error(f"Erreur création lot: {e}")
        return {"success": False, "error": str(e)}


@router.get("/api/lots-perissables/alertes", response_class=JSONResponse, name="api_alertes_peremption")
def api_alertes_peremption(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Récupère les lots proches de la péremption"""
    try:
        from datetime import timedelta
        
        # Lots à vérifier dans les 60 prochains jours
        date_limite = date.today() + timedelta(days=60)
        
        lots_alerte = StockService.get_lots_proches_peremption(
            session=session,
            jours=60
        )
        
        lots_perimes = StockService.get_lots_perimes(session=session)
        
        data = {
            "lots_alerte": [],
            "lots_perimes": []
        }
        
        for lot in lots_alerte:
            article = session.get(Article, lot.article_id)
            jours_restants = (lot.date_peremption - date.today()).days
            
            data["lots_alerte"].append({
                "id": lot.id,
                "numero_lot": lot.numero_lot,
                "article": article.designation if article else "N/A",
                "date_peremption": str(lot.date_peremption),
                "jours_restants": jours_restants,
                "quantite_restante": float(lot.quantite_restante)
            })
        
        for lot in lots_perimes:
            article = session.get(Article, lot.article_id)
            jours_perime = (date.today() - lot.date_peremption).days
            
            data["lots_perimes"].append({
                "id": lot.id,
                "numero_lot": lot.numero_lot,
                "article": article.designation if article else "N/A",
                "date_peremption": str(lot.date_peremption),
                "jours_perime": jours_perime,
                "quantite_restante": float(lot.quantite_restante)
            })
        
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Erreur alertes péremption: {e}")
        return {"success": False, "error": str(e)}


# ============================================
# NOUVEAUTÉ : GESTION DES AMORTISSEMENTS
# ============================================

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


@router.get("/api/articles/{article_id}/plan-amortissement", response_class=JSONResponse, name="api_plan_amortissement")
def api_plan_amortissement(
    article_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Récupère le plan d'amortissement complet d'un article"""
    try:
        plan = StockService.get_plan_amortissement(session, article_id)
        return {"success": True, "data": plan}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Erreur plan amortissement: {e}")
        return {"success": False, "error": "Erreur lors de la récupération du plan"}


@router.post("/api/amortissements/calculer", response_class=JSONResponse, name="api_calculer_amortissement")
def api_calculer_amortissement(
    article_id: int = Form(...),
    annee: int = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Calcule l'amortissement pour une année donnée"""
    try:
        amortissement = StockService.calculer_amortissement_annee(
            session=session,
            article_id=article_id,
            annee=annee
        )
        
        # Enregistrer l'activité
        article = session.get(Article, article_id)
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="create",
            target_type="amortissement",
            target_id=amortissement.id,
            description=f"Calcul amortissement {annee} - {article.designation if article else 'Article'}",
            icon="💰"
        )
        
        return {
            "success": True,
            "message": f"Amortissement {annee} calculé avec succès",
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
        logger.error(f"Erreur calcul amortissement: {e}")
        return {"success": False, "error": "Erreur lors du calcul"}


@router.get("/api/amortissements/materiels-a-amortir/{annee}", response_class=JSONResponse, name="api_materiels_a_amortir")
def api_materiels_a_amortir(
    annee: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Liste les matériels nécessitant un calcul d'amortissement pour une année"""
    try:
        materiels = StockService.get_materiels_a_amortir(session, annee)
        
        data = []
        for item in materiels:
            article = item["article"]
            data.append({
                "id": article.id,
                "code": article.code,
                "designation": article.designation,
                "date_acquisition": str(article.date_acquisition),
                "valeur_acquisition": float(article.valeur_acquisition),
                "duree_amortissement": article.duree_amortissement_annees,
                "methode": article.methode_amortissement,
                "raison": item["raison"]
            })
        
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Erreur liste matériels: {e}")
        return {"success": False, "error": str(e)}

