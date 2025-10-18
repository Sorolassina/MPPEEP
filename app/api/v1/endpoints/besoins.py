# app/api/v1/endpoints/besoins.py
"""
Endpoints pour la gestion des besoins en agents
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import Session, select, func
from datetime import datetime, date

from app.db.session import get_session
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.models.besoins import BesoinAgent, SuiviBesoin, ConsolidationBesoin
from app.models.personnel import Programme, Direction, Service, GradeComplet
from app.templates import templates, get_template_context
from app.core.logging_config import get_logger
from app.services.activity_service import ActivityService

logger = get_logger(__name__)
router = APIRouter()


# ============================================
# PAGES HTML
# ============================================

@router.get("/", response_class=HTMLResponse, name="besoins_home")
def besoins_home(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Page principale de gestion des besoins en agents
    """
    # Année en cours
    annee_actuelle = datetime.now().year
    
    # Statistiques globales
    total_besoins = session.exec(
        select(func.count(BesoinAgent.id))
        .where(BesoinAgent.annee == annee_actuelle)
        .where(BesoinAgent.actif == True)
    ).one()
    
    total_demande = session.exec(
        select(func.sum(BesoinAgent.nombre_demande))
        .where(BesoinAgent.annee == annee_actuelle)
        .where(BesoinAgent.actif == True)
    ).one() or 0
    
    total_obtenu = session.exec(
        select(func.sum(BesoinAgent.nombre_obtenu))
        .where(BesoinAgent.annee == annee_actuelle)
        .where(BesoinAgent.actif == True)
    ).one() or 0
    
    taux_satisfaction = (total_obtenu / total_demande * 100) if total_demande > 0 else 0
    
    # Besoins récents
    besoins = session.exec(
        select(BesoinAgent)
        .where(BesoinAgent.annee == annee_actuelle)
        .where(BesoinAgent.actif == True)
        .order_by(BesoinAgent.created_at.desc())
        .limit(20)
    ).all()
    
    # Récupérer les référentiels pour les jointures
    services = {s.id: s for s in session.exec(select(Service)).all()}
    directions = {d.id: d for d in session.exec(select(Direction)).all()}
    programmes = {p.id: p for p in session.exec(select(Programme)).all()}
    grades = {g.id: g for g in session.exec(select(GradeComplet)).all()}
    
    return templates.TemplateResponse(
        "pages/besoins.html",
        get_template_context(
            request,
            annee_actuelle=annee_actuelle,
            total_besoins=total_besoins,
            total_demande=int(total_demande),
            total_obtenu=int(total_obtenu),
            taux_satisfaction=round(taux_satisfaction, 1),
            besoins=besoins,
            services=services,
            directions=directions,
            programmes=programmes,
            grades=grades,
            current_user=current_user
        )
    )


@router.get("/nouveau", response_class=HTMLResponse, name="besoin_nouveau")
def besoin_nouveau(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Formulaire de création d'un nouveau besoin"""
    # Référentiels
    services = session.exec(select(Service).where(Service.actif == True).order_by(Service.libelle)).all()
    directions = session.exec(select(Direction).where(Direction.actif == True).order_by(Direction.libelle)).all()
    programmes = session.exec(select(Programme).where(Programme.actif == True).order_by(Programme.libelle)).all()
    grades = session.exec(select(GradeComplet).where(GradeComplet.actif == True).order_by(GradeComplet.code)).all()
    
    return templates.TemplateResponse(
        "pages/besoin_form.html",
        get_template_context(
            request,
            mode="create",
            services=services,
            directions=directions,
            programmes=programmes,
            grades=grades,
            current_user=current_user
        )
    )


@router.get("/consolidation", response_class=HTMLResponse, name="besoins_consolidation")
def besoins_consolidation(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Vue consolidée des besoins par Direction et Programme
    """
    annee_actuelle = datetime.now().year
    
    # Consolidations existantes
    consolidations = session.exec(
        select(ConsolidationBesoin)
        .where(ConsolidationBesoin.annee == annee_actuelle)
        .order_by(ConsolidationBesoin.created_at.desc())
    ).all()
    
    # Référentiels
    directions = {d.id: d for d in session.exec(select(Direction)).all()}
    programmes = {p.id: p for p in session.exec(select(Programme)).all()}
    
    return templates.TemplateResponse(
        "pages/besoins_consolidation.html",
        get_template_context(
            request,
            annee_actuelle=annee_actuelle,
            consolidations=consolidations,
            directions=directions,
            programmes=programmes,
            current_user=current_user
        )
    )


# ============================================
# API - CRUD BESOINS
# ============================================

@router.get("/api/besoins", name="list_besoins_api")
def api_list_besoins(
    annee: Optional[int] = None,
    service_id: Optional[int] = None,
    direction_id: Optional[int] = None,
    statut: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Liste les besoins avec filtres optionnels"""
    query = select(BesoinAgent).where(BesoinAgent.actif == True)
    
    if annee:
        query = query.where(BesoinAgent.annee == annee)
    if service_id:
        query = query.where(BesoinAgent.service_id == service_id)
    if direction_id:
        query = query.where(BesoinAgent.direction_id == direction_id)
    if statut:
        query = query.where(BesoinAgent.statut == statut)
    
    besoins = session.exec(query.order_by(BesoinAgent.created_at.desc())).all()
    
    # Récupérer référentiels
    services = {s.id: s for s in session.exec(select(Service)).all()}
    directions = {d.id: d for d in session.exec(select(Direction)).all()}
    grades = {g.id: g for g in session.exec(select(GradeComplet)).all()}
    
    return [
        {
            "id": b.id,
            "annee": b.annee,
            "periode": b.periode,
            "poste_libelle": b.poste_libelle,
            "grade_code": grades[b.grade_id].code if b.grade_id and b.grade_id in grades else None,
            "service_libelle": services[b.service_id].libelle if b.service_id and b.service_id in services else None,
            "direction_libelle": directions[b.direction_id].libelle if b.direction_id and b.direction_id in directions else None,
            "nombre_demande": b.nombre_demande,
            "nombre_obtenu": b.nombre_obtenu,
            "statut": b.statut,
            "urgence": b.urgence,
            "date_expression": b.date_expression.isoformat() if b.date_expression else None
        }
        for b in besoins
    ]


@router.post("/api/besoins", name="create_besoin_api")
def api_create_besoin(
    annee: int = Form(...),
    periode: Optional[str] = Form(None),
    service_id: Optional[int] = Form(None),
    direction_id: Optional[int] = Form(None),
    programme_id: Optional[int] = Form(None),
    poste_libelle: str = Form(...),
    grade_id: Optional[int] = Form(None),
    categorie_souhaitee: Optional[str] = Form(None),
    nombre_demande: int = Form(1),
    motif: Optional[str] = Form(None),
    urgence: str = Form("Normale"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Créer un nouveau besoin"""
    besoin = BesoinAgent(
        annee=annee,
        periode=periode,
        service_id=service_id,
        direction_id=direction_id,
        programme_id=programme_id,
        poste_libelle=poste_libelle,
        grade_id=grade_id,
        categorie_souhaitee=categorie_souhaitee,
        nombre_demande=nombre_demande,
        motif=motif,
        urgence=urgence,
        statut="Exprimé",
        exprime_par_user_id=current_user.id
    )
    
    session.add(besoin)
    session.commit()
    session.refresh(besoin)
    
    # Créer le suivi initial
    suivi = SuiviBesoin(
        besoin_id=besoin.id,
        ancien_statut=None,
        nouveau_statut="Exprimé",
        nombre_obtenu_avant=0,
        nombre_obtenu_apres=0,
        modifie_par_user_id=current_user.id,
        commentaire="Besoin créé"
    )
    session.add(suivi)
    session.commit()
    
    logger.info(f"✅ Besoin créé : {poste_libelle} ({nombre_demande}) par {current_user.email}")
    
    # Log activité
    ActivityService.log_user_activity(
        session=session,
        user=current_user,
        action_type="create",
        target_type="besoin_agent",
        description=f"Création d'un besoin - {poste_libelle} ({nombre_demande} poste{'s' if nombre_demande > 1 else ''})",
        target_id=besoin.id,
        icon="📊"
    )
    
    return {"ok": True, "id": besoin.id, "message": "Besoin créé avec succès"}


@router.put("/api/besoins/{besoin_id}", name="update_besoin_api")
def api_update_besoin(
    besoin_id: int,
    nombre_obtenu: Optional[int] = Form(None),
    statut: Optional[str] = Form(None),
    date_transmission: Optional[str] = Form(None),
    observations: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Mettre à jour un besoin (notamment le nombre obtenu et le statut)"""
    besoin = session.get(BesoinAgent, besoin_id)
    if not besoin:
        raise HTTPException(404, "Besoin non trouvé")
    
    ancien_statut = besoin.statut
    ancien_nombre = besoin.nombre_obtenu
    
    # Mettre à jour les champs
    if nombre_obtenu is not None:
        besoin.nombre_obtenu = nombre_obtenu
        # Auto-update statut selon satisfaction
        if nombre_obtenu == 0:
            besoin.statut = "En attente"
        elif nombre_obtenu < besoin.nombre_demande:
            besoin.statut = "Partiellement satisfait"
        elif nombre_obtenu >= besoin.nombre_demande:
            besoin.statut = "Satisfait"
            besoin.date_satisfaction = date.today()
    
    if statut:
        besoin.statut = statut
        if statut == "Transmis" and not besoin.date_transmission:
            besoin.date_transmission = date.today()
    
    if date_transmission:
        besoin.date_transmission = date.fromisoformat(date_transmission)
    
    if observations:
        besoin.observations = observations
    
    besoin.updated_at = datetime.utcnow()
    session.add(besoin)
    session.commit()
    
    # Créer le suivi si changement
    if ancien_statut != besoin.statut or ancien_nombre != besoin.nombre_obtenu:
        suivi = SuiviBesoin(
            besoin_id=besoin.id,
            ancien_statut=ancien_statut,
            nouveau_statut=besoin.statut,
            nombre_obtenu_avant=ancien_nombre,
            nombre_obtenu_apres=besoin.nombre_obtenu,
            modifie_par_user_id=current_user.id,
            commentaire=observations
        )
        session.add(suivi)
        session.commit()
    
    # Logger l'activité
    ActivityService.log_user_activity(
        session=session,
        user=current_user,
        action_type="update",
        target_type="besoin_agent",
        target_id=besoin.id,
        description=f"Mise à jour du besoin - {besoin.poste_libelle} (statut: {besoin.statut})",
        icon="✏️"
    )
    
    logger.info(f"✅ Besoin mis à jour : ID {besoin_id} par {current_user.email}")
    return {"ok": True, "message": "Besoin mis à jour avec succès"}


@router.delete("/api/besoins/{besoin_id}", name="delete_besoin_api")
def api_delete_besoin(
    besoin_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Désactiver un besoin"""
    besoin = session.get(BesoinAgent, besoin_id)
    if not besoin:
        raise HTTPException(404, "Besoin non trouvé")
    
    besoin_libelle = besoin.poste_libelle
    
    besoin.actif = False
    besoin.updated_at = datetime.utcnow()
    session.add(besoin)
    session.commit()
    
    # Logger l'activité
    ActivityService.log_user_activity(
        session=session,
        user=current_user,
        action_type="delete",
        target_type="besoin_agent",
        target_id=besoin_id,
        description=f"Suppression du besoin - {besoin_libelle}",
        icon="🗑️"
    )
    
    logger.info(f"✅ Besoin désactivé : ID {besoin_id} par {current_user.email}")
    return {"ok": True, "message": "Besoin désactivé avec succès"}


# ============================================
# API - CONSOLIDATION
# ============================================

@router.post("/api/consolidation/generer", name="generer_consolidation_api")
def api_generer_consolidation(
    annee: int = Form(...),
    niveau: str = Form(...),  # "Direction" ou "Programme"
    direction_id: Optional[int] = Form(None),
    programme_id: Optional[int] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Générer une consolidation des besoins
    Agrège les besoins au niveau Direction ou Programme
    """
    # Requête de base
    query = select(BesoinAgent).where(BesoinAgent.annee == annee).where(BesoinAgent.actif == True)
    
    if niveau == "Direction" and direction_id:
        query = query.where(BesoinAgent.direction_id == direction_id)
    elif niveau == "Programme" and programme_id:
        query = query.where(BesoinAgent.programme_id == programme_id)
    
    besoins = session.exec(query).all()
    
    if not besoins:
        raise HTTPException(400, "Aucun besoin trouvé pour cette sélection")
    
    # Calculer les agrégats
    total_demande = sum(b.nombre_demande for b in besoins)
    total_obtenu = sum(b.nombre_obtenu for b in besoins)
    taux_satisfaction = (total_obtenu / total_demande * 100) if total_demande > 0 else 0
    
    # Par catégorie
    demande_cat_a = sum(b.nombre_demande for b in besoins if b.categorie_souhaitee == "A")
    obtenu_cat_a = sum(b.nombre_obtenu for b in besoins if b.categorie_souhaitee == "A")
    demande_cat_b = sum(b.nombre_demande for b in besoins if b.categorie_souhaitee == "B")
    obtenu_cat_b = sum(b.nombre_obtenu for b in besoins if b.categorie_souhaitee == "B")
    demande_cat_c = sum(b.nombre_demande for b in besoins if b.categorie_souhaitee == "C")
    obtenu_cat_c = sum(b.nombre_obtenu for b in besoins if b.categorie_souhaitee == "C")
    demande_cat_d = sum(b.nombre_demande for b in besoins if b.categorie_souhaitee == "D")
    obtenu_cat_d = sum(b.nombre_obtenu for b in besoins if b.categorie_souhaitee == "D")
    
    # Créer la consolidation
    consolidation = ConsolidationBesoin(
        annee=annee,
        niveau=niveau,
        direction_id=direction_id,
        programme_id=programme_id,
        total_demande=total_demande,
        total_obtenu=total_obtenu,
        taux_satisfaction=round(taux_satisfaction, 2),
        demande_cat_a=demande_cat_a,
        obtenu_cat_a=obtenu_cat_a,
        demande_cat_b=demande_cat_b,
        obtenu_cat_b=obtenu_cat_b,
        demande_cat_c=demande_cat_c,
        obtenu_cat_c=obtenu_cat_c,
        demande_cat_d=demande_cat_d,
        obtenu_cat_d=obtenu_cat_d,
        statut="En cours"
    )
    
    session.add(consolidation)
    session.commit()
    session.refresh(consolidation)
    
    # Logger l'activité
    ActivityService.log_user_activity(
        session=session,
        user=current_user,
        action_type="generate",
        target_type="consolidation_besoin",
        target_id=consolidation.id,
        description=f"Génération de consolidation - {niveau} - Année {annee}",
        icon="📊"
    )
    
    logger.info(f"✅ Consolidation générée : {niveau} - Année {annee} par {current_user.email}")
    return {"ok": True, "id": consolidation.id, "message": "Consolidation générée avec succès"}


@router.get("/api/consolidation/{consolidation_id}/export", name="export_consolidation_api")
def api_export_consolidation(
    consolidation_id: int,
    session: Session = Depends(get_session)
):
    """Exporter une consolidation (données pour rapport)"""
    consolidation = session.get(ConsolidationBesoin, consolidation_id)
    if not consolidation:
        raise HTTPException(404, "Consolidation non trouvée")
    
    # Récupérer les besoins associés
    query = select(BesoinAgent).where(BesoinAgent.annee == consolidation.annee)
    
    if consolidation.direction_id:
        query = query.where(BesoinAgent.direction_id == consolidation.direction_id)
    if consolidation.programme_id:
        query = query.where(BesoinAgent.programme_id == consolidation.programme_id)
    
    besoins = session.exec(query).all()
    
    # Référentiels
    services = {s.id: s for s in session.exec(select(Service)).all()}
    grades = {g.id: g for g in session.exec(select(GradeComplet)).all()}
    
    return {
        "consolidation": {
            "annee": consolidation.annee,
            "niveau": consolidation.niveau,
            "total_demande": consolidation.total_demande,
            "total_obtenu": consolidation.total_obtenu,
            "taux_satisfaction": float(consolidation.taux_satisfaction) if consolidation.taux_satisfaction else 0,
            "par_categorie": {
                "A": {"demande": consolidation.demande_cat_a, "obtenu": consolidation.obtenu_cat_a},
                "B": {"demande": consolidation.demande_cat_b, "obtenu": consolidation.obtenu_cat_b},
                "C": {"demande": consolidation.demande_cat_c, "obtenu": consolidation.obtenu_cat_c},
                "D": {"demande": consolidation.demande_cat_d, "obtenu": consolidation.obtenu_cat_d}
            }
        },
        "besoins_detail": [
            {
                "poste": b.poste_libelle,
                "grade": grades[b.grade_id].libelle if b.grade_id and b.grade_id in grades else "-",
                "service": services[b.service_id].libelle if b.service_id and b.service_id in services else "-",
                "demande": b.nombre_demande,
                "obtenu": b.nombre_obtenu,
                "statut": b.statut
            }
            for b in besoins
        ]
    }


@router.get("/api/statistiques", name="statistiques_besoins_api")
def api_statistiques_besoins(
    annee: Optional[int] = None,
    session: Session = Depends(get_session)
):
    """Statistiques globales sur les besoins"""
    if not annee:
        annee = datetime.now().year
    
    # Stats globales
    besoins = session.exec(
        select(BesoinAgent)
        .where(BesoinAgent.annee == annee)
        .where(BesoinAgent.actif == True)
    ).all()
    
    total_demande = sum(b.nombre_demande for b in besoins)
    total_obtenu = sum(b.nombre_obtenu for b in besoins)
    
    # Par statut
    stats_par_statut = {}
    for statut in ["Exprimé", "Transmis", "En attente", "Partiellement satisfait", "Satisfait", "Rejeté"]:
        besoins_statut = [b for b in besoins if b.statut == statut]
        stats_par_statut[statut] = {
            "nombre": len(besoins_statut),
            "demande": sum(b.nombre_demande for b in besoins_statut),
            "obtenu": sum(b.nombre_obtenu for b in besoins_statut)
        }
    
    # Par catégorie
    stats_par_categorie = {}
    for cat in ["A", "B", "C", "D"]:
        besoins_cat = [b for b in besoins if b.categorie_souhaitee == cat]
        stats_par_categorie[cat] = {
            "demande": sum(b.nombre_demande for b in besoins_cat),
            "obtenu": sum(b.nombre_obtenu for b in besoins_cat)
        }
    
    # Par urgence
    stats_par_urgence = {}
    for urgence in ["Faible", "Normale", "Élevée", "Critique"]:
        besoins_urgence = [b for b in besoins if b.urgence == urgence]
        stats_par_urgence[urgence] = len(besoins_urgence)
    
    return {
        "annee": annee,
        "total_besoins": len(besoins),
        "total_demande": total_demande,
        "total_obtenu": total_obtenu,
        "taux_satisfaction": round((total_obtenu / total_demande * 100) if total_demande > 0 else 0, 1),
        "par_statut": stats_par_statut,
        "par_categorie": stats_par_categorie,
        "par_urgence": stats_par_urgence
    }

