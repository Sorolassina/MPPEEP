# app/api/v1/endpoints/plannification.py
"""
Routes pour le module Plannification
Système de gestion des événements et calendrier
"""

from datetime import date, datetime, time, timedelta
from typing import Optional
from calendar import monthrange

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlmodel import Session, select

from app.api.v1.endpoints.auth import get_current_user
from app.core.logging_config import get_logger
from app.db.session import get_session
from app.models.plannification import (
    EvenementPlannification,
    PrioriteEvenement,
    StatutEvenement,
    TypeEvenement,
)
from app.models.user import User
from app.services.activity_service import ActivityService
from app.templates import get_template_context, templates

logger = get_logger(__name__)

router = APIRouter()

# ============================================
# PAGES HTML
# ============================================


@router.get("", response_class=HTMLResponse, name="plannification_home")
def plannification_home(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    annee: Optional[int] = Query(None),
    mois: Optional[int] = Query(None),
):
    """
    Page principale du module Plannification avec calendrier
    """
    # Vérifier l'accès au module Plannification
    if not current_user.can_access_module("plannification") and not current_user.is_guest:
        return RedirectResponse(
            url=request.url_for("access_denied").include_query_params(module="plannification"), status_code=302
        )

    # Déterminer l'année et le mois à afficher
    if not annee:
        annee = datetime.now().year
    if not mois:
        mois = datetime.now().month

    # Récupérer les événements pour le mois sélectionné
    date_debut_mois = date(annee, mois, 1)
    # Calculer le dernier jour du mois
    if mois == 12:
        date_fin_mois = date(annee + 1, 1, 1)
    else:
        date_fin_mois = date(annee, mois + 1, 1)

    evenements = session.exec(
        select(EvenementPlannification)
        .where(EvenementPlannification.date_debut >= date_debut_mois)
        .where(EvenementPlannification.date_debut < date_fin_mois)
        .order_by(EvenementPlannification.date_debut, EvenementPlannification.heure_debut)
    ).all()

    # Récupérer tous les utilisateurs pour les sélecteurs de responsables
    from app.models.user import User as UserModel

    utilisateurs = session.exec(select(UserModel).where(UserModel.is_active == True).order_by(UserModel.full_name)).all()

    # Préparer les données du calendrier
    premier_jour = date(annee, mois, 1)
    jour_semaine = premier_jour.weekday()  # 0 = lundi, 6 = dimanche
    jours_avant = jour_semaine
    nb_jours_mois = monthrange(annee, mois)[1]
    
    # Créer un dictionnaire des événements par jour pour faciliter l'affichage
    evenements_par_jour = {}
    for evt in evenements:
        jour = evt.date_debut
        if jour not in evenements_par_jour:
            evenements_par_jour[jour] = []
        evenements_par_jour[jour].append(evt)
    
    # Préparer les jours du calendrier (42 cases = 6 semaines)
    jours_calendrier = []
    aujourdhui = date.today()
    
    # Jours du mois précédent
    if jours_avant > 0:
        mois_precedent = mois - 1 if mois > 1 else 12
        annee_precedente = annee if mois > 1 else annee - 1
        nb_jours_mois_precedent = monthrange(annee_precedente, mois_precedent)[1]
        for i in range(jours_avant):
            jour_num = nb_jours_mois_precedent - jours_avant + i + 1
            jour_date = date(annee_precedente, mois_precedent, jour_num)
            jours_calendrier.append({"jour": jour_num, "date": jour_date, "mois_courant": False, "aujourdhui": jour_date == aujourdhui, "evenements": []})
    
    # Jours du mois courant
    for jour_num in range(1, nb_jours_mois + 1):
        jour_date = date(annee, mois, jour_num)
        jours_calendrier.append({
            "jour": jour_num, 
            "date": jour_date, 
            "mois_courant": True, 
            "aujourdhui": jour_date == aujourdhui,
            "evenements": evenements_par_jour.get(jour_date, [])
        })
    
    # Jours du mois suivant pour compléter la grille
    jours_apres = 42 - len(jours_calendrier)
    if jours_apres > 0:
        mois_suivant = mois + 1 if mois < 12 else 1
        annee_suivante = annee if mois < 12 else annee + 1
        for jour_num in range(1, jours_apres + 1):
            jour_date = date(annee_suivante, mois_suivant, jour_num)
            jours_calendrier.append({"jour": jour_num, "date": jour_date, "mois_courant": False, "aujourdhui": jour_date == aujourdhui, "evenements": []})

    context = get_template_context(
        request,
        evenements=evenements,
        jours_calendrier=jours_calendrier,
        annee=annee,
        mois=mois,
        utilisateurs=utilisateurs,
        TypeEvenement=TypeEvenement,
        StatutEvenement=StatutEvenement,
        PrioriteEvenement=PrioriteEvenement,
        current_user=current_user,
    )

    return templates.TemplateResponse("pages/plannification.html", context)


@router.get("/evenements/nouveau", response_class=HTMLResponse, name="plannification_evenement_nouveau")
def plannification_evenement_nouveau(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    date_selected: Optional[str] = Query(None),
):
    """
    Formulaire de création d'un nouvel événement
    """
    if not current_user.can_access_module("plannification") and not current_user.is_guest:
        return RedirectResponse(
            url=request.url_for("access_denied").include_query_params(module="plannification"), status_code=302
        )

    # Récupérer tous les utilisateurs pour le sélecteur de responsable
    from app.models.user import User as UserModel

    utilisateurs = session.exec(select(UserModel).where(UserModel.is_active == True).order_by(UserModel.full_name)).all()

    # Parser la date sélectionnée si fournie
    date_parsee = None
    if date_selected:
        try:
            date_parsee = datetime.strptime(date_selected, "%Y-%m-%d").date()
        except ValueError:
            pass

    context = get_template_context(
        request,
        date_selected=date_parsee,
        utilisateurs=utilisateurs,
        TypeEvenement=TypeEvenement,
        StatutEvenement=StatutEvenement,
        PrioriteEvenement=PrioriteEvenement,
        current_user=current_user,
    )

    return templates.TemplateResponse("pages/plannification_evenement_form.html", context)


@router.get("/evenements/{evenement_id}/edit", response_class=HTMLResponse, name="plannification_evenement_edit")
def plannification_evenement_edit(
    evenement_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Formulaire de modification d'un événement
    """
    if not current_user.can_access_module("plannification") and not current_user.is_guest:
        return RedirectResponse(
            url=request.url_for("access_denied").include_query_params(module="plannification"), status_code=302
        )

    evenement = session.get(EvenementPlannification, evenement_id)
    if not evenement:
        raise HTTPException(status_code=404, detail="Événement non trouvé")

    # Récupérer tous les utilisateurs pour le sélecteur de responsable
    from app.models.user import User as UserModel

    utilisateurs = session.exec(select(UserModel).where(UserModel.is_active == True).order_by(UserModel.full_name)).all()

    context = get_template_context(
        request,
        evenement=evenement,
        utilisateurs=utilisateurs,
        TypeEvenement=TypeEvenement,
        StatutEvenement=StatutEvenement,
        PrioriteEvenement=PrioriteEvenement,
        current_user=current_user,
    )

    return templates.TemplateResponse("pages/plannification_evenement_form.html", context)


# ============================================
# API ENDPOINTS
# ============================================


@router.post("/api/evenements", response_class=JSONResponse, name="api_create_evenement")
def api_create_evenement(
    request: Request,
    titre: str = Form(...),
    description: Optional[str] = Form(None),
    type_evenement: str = Form(...),
    statut: str = Form(...),
    priorite: str = Form(...),
    date_debut: str = Form(...),
    heure_debut: Optional[str] = Form(None),
    date_fin: Optional[str] = Form(None),
    heure_fin: Optional[str] = Form(None),
    journee_entiere: bool = Form(False),
    lieu: Optional[str] = Form(None),
    responsable_id: Optional[int] = Form(None),
    participants: Optional[str] = Form(None),
    rappel_actif: bool = Form(False),
    rappel_avant_jours: Optional[int] = Form(None),
    rappel_avant_heures: Optional[int] = Form(None),
    couleur: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    API: Créer un nouvel événement
    """
    if current_user.is_guest:
        raise HTTPException(status_code=403, detail="Les invités ne peuvent pas créer d'événements")

    try:
        # Parser les dates
        date_debut_parsed = datetime.strptime(date_debut, "%Y-%m-%d").date()
        date_fin_parsed = None
        if date_fin:
            date_fin_parsed = datetime.strptime(date_fin, "%Y-%m-%d").date()

        # Parser les heures
        heure_debut_parsed = None
        if heure_debut and not journee_entiere:
            heure_debut_parsed = datetime.strptime(heure_debut, "%H:%M").time()

        heure_fin_parsed = None
        if heure_fin and not journee_entiere:
            heure_fin_parsed = datetime.strptime(heure_fin, "%H:%M").time()

        evenement = EvenementPlannification(
            titre=titre,
            description=description,
            type_evenement=type_evenement,
            statut=statut,
            priorite=priorite,
            date_debut=date_debut_parsed,
            heure_debut=heure_debut_parsed,
            date_fin=date_fin_parsed,
            heure_fin=heure_fin_parsed,
            journee_entiere=journee_entiere,
            lieu=lieu,
            responsable_id=responsable_id,
            participants=participants,
            rappel_actif=rappel_actif,
            rappel_avant_jours=rappel_avant_jours,
            rappel_avant_heures=rappel_avant_heures,
            couleur=couleur,
            created_by_id=current_user.id,
            updated_by_id=current_user.id,
        )

        session.add(evenement)
        session.commit()
        session.refresh(evenement)

        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="create",
            target_type="evenement_plannification",
            target_id=evenement.id,
            description=f"Création de l'événement: {titre}",
            icon="📅",
        )

        return {"success": True, "message": "Événement créé avec succès", "id": evenement.id}

    except Exception as e:
        session.rollback()
        logger.error(f"Erreur lors de la création de l'événement: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création: {str(e)}")


@router.put("/api/evenements/{evenement_id}", response_class=JSONResponse, name="api_update_evenement")
def api_update_evenement(
    evenement_id: int,
    request: Request,
    titre: str = Form(...),
    description: Optional[str] = Form(None),
    type_evenement: str = Form(...),
    statut: str = Form(...),
    priorite: str = Form(...),
    date_debut: str = Form(...),
    heure_debut: Optional[str] = Form(None),
    date_fin: Optional[str] = Form(None),
    heure_fin: Optional[str] = Form(None),
    journee_entiere: bool = Form(False),
    lieu: Optional[str] = Form(None),
    responsable_id: Optional[int] = Form(None),
    participants: Optional[str] = Form(None),
    rappel_actif: bool = Form(False),
    rappel_avant_jours: Optional[int] = Form(None),
    rappel_avant_heures: Optional[int] = Form(None),
    couleur: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    API: Modifier un événement
    """
    if current_user.is_guest:
        raise HTTPException(status_code=403, detail="Les invités ne peuvent pas modifier d'événements")

    evenement = session.get(EvenementPlannification, evenement_id)
    if not evenement:
        raise HTTPException(status_code=404, detail="Événement non trouvé")

    try:
        # Parser les dates
        date_debut_parsed = datetime.strptime(date_debut, "%Y-%m-%d").date()
        date_fin_parsed = None
        if date_fin:
            date_fin_parsed = datetime.strptime(date_fin, "%Y-%m-%d").date()

        # Parser les heures
        heure_debut_parsed = None
        if heure_debut and not journee_entiere:
            heure_debut_parsed = datetime.strptime(heure_debut, "%H:%M").time()

        heure_fin_parsed = None
        if heure_fin and not journee_entiere:
            heure_fin_parsed = datetime.strptime(heure_fin, "%H:%M").time()

        evenement.titre = titre
        evenement.description = description
        evenement.type_evenement = type_evenement
        evenement.statut = statut
        evenement.priorite = priorite
        evenement.date_debut = date_debut_parsed
        evenement.heure_debut = heure_debut_parsed
        evenement.date_fin = date_fin_parsed
        evenement.heure_fin = heure_fin_parsed
        evenement.journee_entiere = journee_entiere
        evenement.lieu = lieu
        evenement.responsable_id = responsable_id
        evenement.participants = participants
        evenement.rappel_actif = rappel_actif
        evenement.rappel_avant_jours = rappel_avant_jours
        evenement.rappel_avant_heures = rappel_avant_heures
        evenement.couleur = couleur
        evenement.updated_at = datetime.utcnow()
        evenement.updated_by_id = current_user.id

        session.add(evenement)
        session.commit()

        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="update",
            target_type="evenement_plannification",
            target_id=evenement.id,
            description=f"Modification de l'événement: {titre}",
            icon="✏️",
        )

        return {"success": True, "message": "Événement modifié avec succès"}

    except Exception as e:
        session.rollback()
        logger.error(f"Erreur lors de la modification de l'événement: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la modification: {str(e)}")


@router.delete("/api/evenements/{evenement_id}", response_class=JSONResponse, name="api_delete_evenement")
def api_delete_evenement(
    evenement_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    API: Supprimer un événement
    """
    if current_user.is_guest:
        raise HTTPException(status_code=403, detail="Les invités ne peuvent pas supprimer d'événements")

    evenement = session.get(EvenementPlannification, evenement_id)
    if not evenement:
        raise HTTPException(status_code=404, detail="Événement non trouvé")

    try:
        titre = evenement.titre
        session.delete(evenement)
        session.commit()

        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="delete",
            target_type="evenement_plannification",
            target_id=evenement_id,
            description=f"Suppression de l'événement: {titre}",
            icon="🗑️",
        )

        return {"success": True, "message": "Événement supprimé avec succès"}

    except Exception as e:
        session.rollback()
        logger.error(f"Erreur lors de la suppression de l'événement: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression: {str(e)}")


@router.get("/api/evenements", response_class=JSONResponse, name="api_list_evenements")
def api_list_evenements(
    request: Request,
    date_debut: Optional[str] = Query(None),
    date_fin: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    API: Récupérer la liste des événements (pour le calendrier)
    """
    query = select(EvenementPlannification)

    if date_debut:
        date_debut_parsed = datetime.strptime(date_debut, "%Y-%m-%d").date()
        query = query.where(EvenementPlannification.date_debut >= date_debut_parsed)

    if date_fin:
        date_fin_parsed = datetime.strptime(date_fin, "%Y-%m-%d").date()
        query = query.where(EvenementPlannification.date_debut <= date_fin_parsed)

    evenements = session.exec(query.order_by(EvenementPlannification.date_debut, EvenementPlannification.heure_debut)).all()

    # Convertir en format JSON
    evenements_json = []
    for evt in evenements:
        evenements_json.append(
            {
                "id": evt.id,
                "titre": evt.titre,
                "description": evt.description,
                "type_evenement": evt.type_evenement,
                "statut": evt.statut,
                "priorite": evt.priorite,
                "date_debut": evt.date_debut.isoformat() if evt.date_debut else None,
                "heure_debut": evt.heure_debut.isoformat() if evt.heure_debut else None,
                "date_fin": evt.date_fin.isoformat() if evt.date_fin else None,
                "heure_fin": evt.heure_fin.isoformat() if evt.heure_fin else None,
                "journee_entiere": evt.journee_entiere,
                "lieu": evt.lieu,
                "couleur": evt.couleur,
            }
        )

    return {"success": True, "data": evenements_json}

