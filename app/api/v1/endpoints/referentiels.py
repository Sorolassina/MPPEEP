# app/api/v1/endpoints/referentiels.py
"""
Endpoints pour la gestion des référentiels RH/Personnel
(Programmes, Directions, Services, Grades)
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import Session, select, func

from app.api.v1.endpoints.auth import get_current_user, require_roles
from app.core.enums import GradeCategory
from app.core.logging_config import get_logger
from app.db.session import get_session
from app.models.personnel import Cabinet, Direction, GradeComplet, Programme, Service, SousDirection
from app.models.stock import CategorieArticle
from app.models.user import User
from app.templates import get_template_context, templates

logger = get_logger(__name__)
router = APIRouter()


# ============================================
# PAGE PRINCIPALE RÉFÉRENTIELS
# ============================================
@router.get("/", response_class=HTMLResponse, name="referentiels_home")
def referentiels_home(
    request: Request, session: Session = Depends(get_session), current_user: User = Depends(require_roles("admin"))
):
    """
    Page principale de gestion des référentiels
    """
    # Compter les référentiels
    from sqlalchemy.exc import ProgrammingError, OperationalError
    
    # Gérer le cas où la table cabinet n'existe pas encore
    try:
        cabinets_raw = session.exec(select(Cabinet)).all()
    except (ProgrammingError, OperationalError):
        logger.warning("Table cabinet n'existe pas encore dans la base de données")
        cabinets_raw = []
    
    programmes_raw = session.exec(select(Programme)).all()
    directions_raw = session.exec(select(Direction)).all()
    
    # Gérer le cas où la table sous_direction n'existe pas encore
    try:
        sous_directions_raw = session.exec(select(SousDirection).order_by(SousDirection.code)).all()
    except (ProgrammingError, OperationalError):
        logger.warning("Table sous_direction n'existe pas encore dans la base de données")
        sous_directions_raw = []
    
    services_raw = session.exec(select(Service)).all()
    grades_raw = session.exec(select(GradeComplet)).all()
    categories_raw = session.exec(select(CategorieArticle)).all()

    # Créer les dictionnaires de référence
    cabinets_dict = {c.id: c for c in cabinets_raw}
    programmes_dict = {p.id: p for p in programmes_raw}
    directions_dict = {d.id: d for d in directions_raw}
    sous_directions_dict = {sd.id: sd for sd in sous_directions_raw}

    # Enrichir les directions avec programme_libelle ou cabinet_libelle
    directions_enriched = []
    for d in directions_raw:
        direction_dict = {
            "id": d.id,
            "code": d.code,
            "libelle": d.libelle,
            "description": d.description or "",
            "actif": d.actif,
            "programme_id": d.programme_id,
            "programme_libelle": programmes_dict[d.programme_id].libelle
            if d.programme_id and d.programme_id in programmes_dict
            else "",
            "cabinet_id": d.cabinet_id,
            "cabinet_libelle": cabinets_dict[d.cabinet_id].libelle
            if d.cabinet_id and d.cabinet_id in cabinets_dict
            else "",
        }
        directions_enriched.append(direction_dict)

    # Enrichir les sous-directions avec direction_libelle, programme_libelle ou cabinet_libelle
    sous_directions_enriched = []
    for sd in sous_directions_raw:
        parent_libelle = ""
        parent_type = ""
        if sd.direction_id and sd.direction_id in directions_dict:
            parent_libelle = directions_dict[sd.direction_id].libelle
            parent_type = "Direction"
        elif sd.programme_id and sd.programme_id in programmes_dict:
            parent_libelle = programmes_dict[sd.programme_id].libelle
            parent_type = "Programme"
        elif sd.cabinet_id and sd.cabinet_id in cabinets_dict:
            parent_libelle = cabinets_dict[sd.cabinet_id].libelle
            parent_type = "Cabinet"
        
        sous_direction_dict = {
            "id": sd.id,
            "code": sd.code,
            "libelle": sd.libelle,
            "description": sd.description or "",
            "actif": sd.actif,
            "direction_id": sd.direction_id,
            "direction_libelle": parent_libelle if parent_type == "Direction" else "",
            "programme_id": sd.programme_id,
            "programme_libelle": parent_libelle if parent_type == "Programme" else "",
            "cabinet_id": sd.cabinet_id,
            "cabinet_libelle": parent_libelle if parent_type == "Cabinet" else "",
            "parent_type": parent_type,
            "parent_libelle": parent_libelle,
        }
        sous_directions_enriched.append(sous_direction_dict)

    # Enrichir les services avec sous_direction_libelle, direction_libelle, programme_libelle ou cabinet_libelle
    services_enriched = []
    for s in services_raw:
        parent_libelle = ""
        parent_type = ""
        if s.sous_direction_id and s.sous_direction_id in sous_directions_dict:
            parent_libelle = sous_directions_dict[s.sous_direction_id].libelle
            parent_type = "Sous-direction"
        elif s.direction_id and s.direction_id in directions_dict:
            parent_libelle = directions_dict[s.direction_id].libelle
            parent_type = "Direction"
        elif s.programme_id and s.programme_id in programmes_dict:
            parent_libelle = programmes_dict[s.programme_id].libelle
            parent_type = "Programme"
        elif s.cabinet_id and s.cabinet_id in cabinets_dict:
            parent_libelle = cabinets_dict[s.cabinet_id].libelle
            parent_type = "Cabinet"
        
        service_dict = {
            "id": s.id,
            "code": s.code,
            "libelle": s.libelle,
            "description": s.description or "",
            "actif": s.actif,
            "sous_direction_id": s.sous_direction_id,
            "sous_direction_libelle": parent_libelle if parent_type == "Sous-direction" else "",
            "direction_id": s.direction_id,
            "direction_libelle": parent_libelle if parent_type == "Direction" else "",
            "programme_id": s.programme_id,
            "programme_libelle": parent_libelle if parent_type == "Programme" else "",
            "cabinet_id": s.cabinet_id,
            "cabinet_libelle": parent_libelle if parent_type == "Cabinet" else "",
            "parent_type": parent_type,
            "parent_libelle": parent_libelle,
        }
        services_enriched.append(service_dict)

    return templates.TemplateResponse(
        "pages/referentiels.html",
        get_template_context(
            request,
            nb_cabinets=len(cabinets_raw),
            nb_programmes=len(programmes_raw),
            nb_directions=len(directions_raw),
            nb_sous_directions=len(sous_directions_raw),
            nb_services=len(services_raw),
            nb_categories=len(categories_raw),
            nb_grades=len(grades_raw),
            cabinets=cabinets_raw,
            programmes=programmes_raw,
            directions=directions_enriched,  # ← Directions enrichies avec programme_libelle et cabinet_libelle
            sous_directions=sous_directions_enriched,  # ← Sous-directions enrichies avec direction_libelle
            services=services_enriched,  # ← Services enrichis avec sous_direction_libelle
            grades=grades_raw,
            categories=categories_raw,
            current_user=current_user,
        ),
    )


@router.get("/aide", response_class=HTMLResponse, name="aide_referentiels")
def aide_referentiels(request: Request):
    """Page d'aide pour les référentiels"""
    from app.templates import get_template_context, templates

    return templates.TemplateResponse("pages/aide_referentiels.html", get_template_context(request))


# ============================================
# API - CABINET
# ============================================


@router.get("/api/cabinets", name="api_list_cabinets_ref")
def api_list_cabinets_ref(session: Session = Depends(get_session)):
    """Liste tous les cabinets"""
    from app.models.personnel import AgentComplet
    from sqlalchemy.exc import ProgrammingError, OperationalError

    try:
        cabinets = session.exec(select(Cabinet).order_by(Cabinet.code)).all()
    except (ProgrammingError, OperationalError):
        logger.warning("Table cabinet n'existe pas encore dans la base de données")
        return []

    result = []
    for c in cabinets:
        responsable_nom = ""
        if c.responsable_id:
            responsable = session.get(AgentComplet, c.responsable_id)
            if responsable:
                responsable_nom = f"{responsable.nom} {responsable.prenom}"

        result.append(
            {
                "id": c.id,
                "code": c.code,
                "libelle": c.libelle,
                "description": c.description,
                "responsable_id": c.responsable_id,
                "responsable_nom": responsable_nom,
                "actif": c.actif,
            }
        )

    return result


@router.post("/api/cabinets", name="api_create_cabinet")
def api_create_cabinet(
    code: str = Form(...),
    libelle: str = Form(...),
    description: str | None = Form(None),
    responsable_id: int | None = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Créer un nouveau cabinet - UN SEUL CABINET ACTIF AUTORISÉ"""
    # Validation : un seul cabinet actif autorisé
    existing_active = session.exec(select(Cabinet).where(Cabinet.actif == True)).first()
    if existing_active:
        raise HTTPException(400, "Un cabinet actif existe déjà. Désactivez-le d'abord ou modifiez-le.")
    
    # Vérifier si le code existe déjà
    existing = session.exec(select(Cabinet).where(Cabinet.code == code)).first()
    if existing:
        raise HTTPException(400, f"Le code '{code}' existe déjà")

    cabinet = Cabinet(
        code=code,
        libelle=libelle,
        description=description,
        responsable_id=responsable_id if responsable_id else None,
        actif=True  # Le nouveau cabinet est toujours actif
    )
    session.add(cabinet)
    session.commit()
    session.refresh(cabinet)

    logger.info(f"✅ Cabinet créé : {code} - {libelle} par {current_user.email}")
    return {"ok": True, "id": cabinet.id, "message": "Cabinet créé avec succès"}


@router.put("/api/cabinets/{cabinet_id}", name="api_update_cabinet")
def api_update_cabinet(
    cabinet_id: int,
    code: str = Form(...),
    libelle: str = Form(...),
    description: str | None = Form(None),
    responsable_id: int | None = Form(None),
    actif: bool = Form(True),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Modifier un cabinet - UN SEUL CABINET ACTIF AUTORISÉ"""
    cabinet = session.get(Cabinet, cabinet_id)
    if not cabinet:
        raise HTTPException(404, "Cabinet non trouvé")

    # Validation : si on active ce cabinet, vérifier qu'aucun autre n'est actif
    if actif and not cabinet.actif:
        existing_active = session.exec(select(Cabinet).where(Cabinet.actif == True, Cabinet.id != cabinet_id)).first()
        if existing_active:
            raise HTTPException(400, f"Un autre cabinet actif existe déjà ({existing_active.code}). Désactivez-le d'abord.")

    # Vérifier si le nouveau code n'existe pas déjà (sauf pour lui-même)
    if code != cabinet.code:
        existing = session.exec(select(Cabinet).where(Cabinet.code == code)).first()
        if existing:
            raise HTTPException(400, f"Le code '{code}' existe déjà")

    cabinet.code = code
    cabinet.libelle = libelle
    cabinet.description = description
    cabinet.responsable_id = responsable_id if responsable_id else None
    cabinet.actif = actif
    cabinet.updated_at = datetime.utcnow()

    session.add(cabinet)
    session.commit()

    logger.info(f"✅ Cabinet modifié : {code} par {current_user.email}")
    return {"ok": True, "message": "Cabinet modifié avec succès"}


@router.post("/api/cabinets/{cabinet_id}/reactivate", name="api_reactivate_cabinet")
def api_reactivate_cabinet(
    cabinet_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)
):
    """Réactiver un cabinet désactivé - UN SEUL CABINET ACTIF AUTORISÉ"""
    cabinet = session.get(Cabinet, cabinet_id)
    if not cabinet:
        raise HTTPException(404, "Cabinet non trouvé")

    # Validation : vérifier qu'aucun autre cabinet n'est actif
    existing_active = session.exec(select(Cabinet).where(Cabinet.actif == True, Cabinet.id != cabinet_id)).first()
    if existing_active:
        raise HTTPException(400, f"Un autre cabinet actif existe déjà ({existing_active.code}). Désactivez-le d'abord.")

    cabinet.actif = True
    cabinet.updated_at = datetime.utcnow()
    session.add(cabinet)
    session.commit()

    logger.info(f"✅ Cabinet réactivé : {cabinet.code} par {current_user.email}")
    return {"ok": True, "message": "Cabinet réactivé avec succès"}


@router.delete("/api/cabinets/{cabinet_id}", name="api_delete_cabinet")
def api_delete_cabinet(
    cabinet_id: int,
    hard_delete: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Supprimer un cabinet (soft delete par défaut)"""
    cabinet = session.get(Cabinet, cabinet_id)
    if not cabinet:
        raise HTTPException(404, "Cabinet non trouvé")

    if hard_delete:
        # Vérifier qu'aucune direction n'est rattachée
        directions_count = session.exec(select(func.count(Direction.id)).where(Direction.cabinet_id == cabinet_id)).first()
        if directions_count and directions_count > 0:
            raise HTTPException(400, f"Impossible de supprimer le cabinet : {directions_count} direction(s) y sont rattachée(s)")
        
        session.delete(cabinet)
        logger.info(f"🗑️ Cabinet supprimé définitivement : {cabinet.code} par {current_user.email}")
    else:
        cabinet.actif = False
        cabinet.updated_at = datetime.utcnow()
        session.add(cabinet)
        logger.info(f"✅ Cabinet désactivé : {cabinet.code} par {current_user.email}")

    session.commit()
    return {"ok": True, "message": "Cabinet supprimé avec succès" if hard_delete else "Cabinet désactivé avec succès"}


# ============================================
# API - PROGRAMMES
# ============================================


@router.get("/api/programmes", name="api_list_programmes_ref")
def api_list_programmes_ref(session: Session = Depends(get_session)):
    """Liste tous les programmes"""
    from app.models.personnel import AgentComplet

    programmes = session.exec(select(Programme).order_by(Programme.code)).all()

    result = []
    for p in programmes:
        responsable_nom = ""
        if p.responsable_id:
            responsable = session.get(AgentComplet, p.responsable_id)
            if responsable:
                responsable_nom = f"{responsable.nom} {responsable.prenom}"

        result.append(
            {
                "id": p.id,
                "code": p.code,
                "libelle": p.libelle,
                "description": p.description,
                "missions": p.missions,  # JSON string
                "responsable_id": p.responsable_id,
                "responsable_nom": responsable_nom,
                "actif": p.actif,
            }
        )

    return result


@router.get("/api/programmes/{programme_id}", name="api_get_programme")
def api_get_programme(programme_id: int, session: Session = Depends(get_session)):
    """Récupère les détails d'un programme avec son responsable"""
    from app.models.personnel import AgentComplet
    
    programme = session.get(Programme, programme_id)
    if not programme:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Programme non trouvé")
    
    responsable_nom_complet = ""
    if programme.responsable_id:
        responsable = session.get(AgentComplet, programme.responsable_id)
        if responsable:
            # Déterminer la civilité selon le sexe
            # Le modèle AgentComplet n'a pas de champ civilite, on le détermine à partir du sexe
            civilité = "Monsieur"  # Par défaut
            if responsable.sexe:
                sexe_upper = responsable.sexe.upper().strip()
                if sexe_upper == "F" or sexe_upper == "FÉMININ" or sexe_upper == "FEMME":
                    civilité = "Madame"
                elif sexe_upper == "M" or sexe_upper == "MASCULIN" or sexe_upper == "HOMME":
                    civilité = "Monsieur"
            
            # Construire le nom complet avec civilité
            responsable_nom_complet = f"{civilité} {responsable.prenom} {responsable.nom}".strip()
    
    return {
        "id": programme.id,
        "code": programme.code,
        "libelle": programme.libelle,
        "description": programme.description,
        "missions": programme.missions,
        "responsable_id": programme.responsable_id,
        "responsable_nom_complet": responsable_nom_complet,
        "actif": programme.actif,
    }


@router.post("/api/programmes", name="api_create_programme")
def api_create_programme(
    code: str = Form(...),
    libelle: str = Form(...),
    description: str | None = Form(None),
    missions: str | None = Form(None),
    responsable_id: int | None = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Créer un nouveau programme"""
    import json
    
    # Vérifier si le code existe déjà
    existing = session.exec(select(Programme).where(Programme.code == code)).first()
    if existing:
        raise HTTPException(400, f"Le code '{code}' existe déjà")

    # Convertir les missions (une par ligne) en JSON
    missions_json = None
    if missions and missions.strip():
        missions_list = [m.strip() for m in missions.split('\n') if m.strip()]
        if missions_list:
            missions_json = json.dumps(missions_list, ensure_ascii=False)

    programme = Programme(
        code=code,
        libelle=libelle,
        description=description,
        missions=missions_json,
        responsable_id=responsable_id if responsable_id else None
    )
    session.add(programme)
    session.commit()
    session.refresh(programme)

    logger.info(f"✅ Programme créé : {code} - {libelle} par {current_user.email}")
    return {"ok": True, "id": programme.id, "message": "Programme créé avec succès"}


@router.put("/api/programmes/{programme_id}", name="api_update_programme")
def api_update_programme(
    programme_id: int,
    code: str = Form(...),
    libelle: str = Form(...),
    description: str | None = Form(None),
    missions: str | None = Form(None),
    responsable_id: int | None = Form(None),
    actif: bool = Form(True),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Modifier un programme"""
    import json
    
    programme = session.get(Programme, programme_id)
    if not programme:
        raise HTTPException(404, "Programme non trouvé")

    # Vérifier si le nouveau code n'existe pas déjà (sauf pour lui-même)
    if code != programme.code:
        existing = session.exec(select(Programme).where(Programme.code == code)).first()
        if existing:
            raise HTTPException(400, f"Le code '{code}' existe déjà")

    # Convertir les missions (une par ligne) en JSON
    missions_json = None
    if missions and missions.strip():
        missions_list = [m.strip() for m in missions.split('\n') if m.strip()]
        if missions_list:
            missions_json = json.dumps(missions_list, ensure_ascii=False)

    programme.code = code
    programme.libelle = libelle
    programme.description = description
    programme.missions = missions_json
    programme.responsable_id = responsable_id if responsable_id else None
    programme.actif = actif
    programme.updated_at = datetime.utcnow()

    session.add(programme)
    session.commit()

    logger.info(f"✅ Programme modifié : {code} par {current_user.email}")
    return {"ok": True, "message": "Programme modifié avec succès"}


@router.post("/api/programmes/{programme_id}/reactivate", name="api_reactivate_programme")
def api_reactivate_programme(
    programme_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)
):
    """Réactiver un programme désactivé"""
    programme = session.get(Programme, programme_id)
    if not programme:
        raise HTTPException(404, "Programme non trouvé")

    programme.actif = True
    programme.updated_at = datetime.utcnow()
    session.add(programme)
    session.commit()

    logger.info(f"✅ Programme réactivé : {programme.code} par {current_user.email}")
    return {"ok": True, "message": "Programme réactivé avec succès"}


@router.delete("/api/programmes/{programme_id}", name="api_delete_programme")
def api_delete_programme(
    programme_id: int,
    hard_delete: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Supprimer un programme (soft delete par défaut, hard delete si hard_delete=true)"""
    programme = session.get(Programme, programme_id)
    if not programme:
        raise HTTPException(404, "Programme non trouvé")

    if hard_delete:
        # Hard delete - Suppression définitive
        session.delete(programme)
        session.commit()
        logger.warning(f"🗑️ Programme SUPPRIMÉ DÉFINITIVEMENT : {programme.code} par {current_user.email}")
        return {"ok": True, "message": "Programme supprimé définitivement"}
    else:
        # Soft delete - Désactivation
        programme.actif = False
        programme.updated_at = datetime.utcnow()
        session.add(programme)
        session.commit()
        logger.info(f"✅ Programme désactivé : {programme.code} par {current_user.email}")
        return {"ok": True, "message": "Programme désactivé avec succès"}


# ============================================
# API - DIRECTIONS
# ============================================


@router.get("/api/directions", name="api_list_directions_ref")
def api_list_directions_ref(session: Session = Depends(get_session)):
    """Liste toutes les directions"""
    from app.models.personnel import AgentComplet

    directions = session.exec(select(Direction).order_by(Direction.code)).all()
    programmes = {p.id: p for p in session.exec(select(Programme)).all()}

    result = []
    for d in directions:
        programme_libelle = ""  # Chaîne vide au lieu de None
        if d.programme_id and d.programme_id in programmes:
            programme_libelle = programmes[d.programme_id].libelle

        directeur_nom = ""
        if d.directeur_id:
            directeur = session.get(AgentComplet, d.directeur_id)
            if directeur:
                directeur_nom = f"{directeur.nom} {directeur.prenom}"

        result.append(
            {
                "id": d.id,
                "code": d.code,
                "libelle": d.libelle,
                "description": d.description or "",
                "actif": d.actif,
                "programme_id": d.programme_id,
                "programme_libelle": programme_libelle,
                "directeur_id": d.directeur_id,
                "directeur_nom": directeur_nom,
                "type": d.type or "",  # Type de direction (CENTRALE, GENERALE, etc.)
            }
        )

    return JSONResponse(
        content=result,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"},
    )


@router.post("/api/directions", name="api_create_direction")
def api_create_direction(
    code: str = Form(...),
    libelle: str = Form(...),
    description: str | None = Form(None),
    programme_id: int | None = Form(None),
    directeur_id: int | None = Form(None),
    type: str | None = Form(None),  # Type de direction: "CENTRALE", "GENERALE", etc.
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Créer une nouvelle direction"""
    # Si aucun programme n'est sélectionné, rattacher automatiquement au cabinet actif
    cabinet_id = None
    if not programme_id:
        active_cabinet = session.exec(select(Cabinet).where(Cabinet.actif == True)).first()
        if active_cabinet:
            cabinet_id = active_cabinet.id
        else:
            raise HTTPException(400, "Aucun cabinet actif trouvé. Veuillez créer un cabinet actif d'abord.")
    
    existing = session.exec(select(Direction).where(Direction.code == code)).first()
    if existing:
        raise HTTPException(400, f"Le code '{code}' existe déjà")

    direction = Direction(
        code=code,
        libelle=libelle,
        description=description,
        programme_id=programme_id if programme_id else None,
        cabinet_id=cabinet_id,
        directeur_id=directeur_id if directeur_id else None,
        type=type if type else None,
    )
    session.add(direction)
    session.commit()
    session.refresh(direction)

    logger.info(f"✅ Direction créée : {code} - {libelle} par {current_user.email}")
    return {"ok": True, "id": direction.id, "message": "Direction créée avec succès"}


@router.put("/api/directions/{direction_id}", name="api_update_direction")
def api_update_direction(
    direction_id: int,
    code: str = Form(...),
    libelle: str = Form(...),
    description: str | None = Form(None),
    programme_id: int | None = Form(None),
    directeur_id: int | None = Form(None),
    actif: bool = Form(True),
    type: str | None = Form(None),  # Type de direction: "CENTRALE", "GENERALE", etc.
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Modifier une direction"""
    # Si aucun programme n'est sélectionné, rattacher automatiquement au cabinet actif
    cabinet_id = None
    if not programme_id:
        active_cabinet = session.exec(select(Cabinet).where(Cabinet.actif == True)).first()
        if active_cabinet:
            cabinet_id = active_cabinet.id
        else:
            raise HTTPException(400, "Aucun cabinet actif trouvé. Veuillez créer un cabinet actif d'abord.")
    
    direction = session.get(Direction, direction_id)
    if not direction:
        raise HTTPException(404, "Direction non trouvée")

    if code != direction.code:
        existing = session.exec(select(Direction).where(Direction.code == code)).first()
        if existing:
            raise HTTPException(400, f"Le code '{code}' existe déjà")

    direction.code = code
    direction.type = type if type else None
    direction.libelle = libelle
    direction.description = description
    direction.programme_id = programme_id if programme_id else None
    direction.cabinet_id = cabinet_id
    direction.directeur_id = directeur_id if directeur_id else None
    direction.actif = actif
    direction.updated_at = datetime.utcnow()

    session.add(direction)
    session.commit()

    logger.info(f"✅ Direction modifiée : {code} par {current_user.email}")
    return {"ok": True, "message": "Direction modifiée avec succès"}


@router.post("/api/directions/{direction_id}/reactivate", name="api_reactivate_direction")
def api_reactivate_direction(
    direction_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)
):
    """Réactiver une direction désactivée"""
    direction = session.get(Direction, direction_id)
    if not direction:
        raise HTTPException(404, "Direction non trouvée")

    direction.actif = True
    direction.updated_at = datetime.utcnow()
    session.add(direction)
    session.commit()

    logger.info(f"✅ Direction réactivée : {direction.code} par {current_user.email}")
    return {"ok": True, "message": "Direction réactivée avec succès"}


@router.delete("/api/directions/{direction_id}", name="api_delete_direction")
def api_delete_direction(
    direction_id: int,
    hard_delete: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Supprimer une direction (soft delete par défaut, hard delete si hard_delete=true)"""
    direction = session.get(Direction, direction_id)
    if not direction:
        raise HTTPException(404, "Direction non trouvée")

    if hard_delete:
        session.delete(direction)
        session.commit()
        logger.warning(f"🗑️ Direction SUPPRIMÉE DÉFINITIVEMENT : {direction.code} par {current_user.email}")
        return {"ok": True, "message": "Direction supprimée définitivement"}
    else:
        direction.actif = False
        direction.updated_at = datetime.utcnow()
        session.add(direction)
        session.commit()
        logger.info(f"✅ Direction désactivée : {direction.code} par {current_user.email}")
        return {"ok": True, "message": "Direction désactivée avec succès"}


# ============================================
# API - SOUS-DIRECTIONS
# ============================================


@router.get("/api/sous-directions", name="api_list_sous_directions_ref")
def api_list_sous_directions_ref(session: Session = Depends(get_session)):
    """Liste toutes les sous-directions avec leurs directions, programmes ou cabinets"""
    from app.models.personnel import AgentComplet
    from sqlalchemy.exc import ProgrammingError, OperationalError

    try:
        sous_directions = session.exec(select(SousDirection).order_by(SousDirection.code)).all()
        directions = {d.id: d for d in session.exec(select(Direction)).all()}
        programmes = {p.id: p for p in session.exec(select(Programme)).all()}
        
        # Récupérer les cabinets si la table existe
        try:
            cabinets = {c.id: c for c in session.exec(select(Cabinet)).all()}
        except (ProgrammingError, OperationalError):
            logger.warning("Table cabinet n'existe pas encore dans la base de données")
            cabinets = {}

        result = []
        for sd in sous_directions:
            direction_libelle = ""
            if sd.direction_id and sd.direction_id in directions:
                direction_libelle = directions[sd.direction_id].libelle

            programme_libelle = ""
            if sd.programme_id and sd.programme_id in programmes:
                programme_libelle = programmes[sd.programme_id].libelle

            cabinet_libelle = ""
            if sd.cabinet_id and sd.cabinet_id in cabinets:
                cabinet_libelle = cabinets[sd.cabinet_id].libelle

            chef_sous_direction_nom = ""
            if sd.chef_sous_direction_id:
                chef = session.get(AgentComplet, sd.chef_sous_direction_id)
                if chef:
                    chef_sous_direction_nom = f"{chef.nom} {chef.prenom}"

            result.append(
                {
                    "id": sd.id,
                    "code": sd.code,
                    "libelle": sd.libelle,
                    "description": sd.description or "",
                    "actif": sd.actif,
                    "direction_id": sd.direction_id,
                    "direction_libelle": direction_libelle,
                    "programme_id": sd.programme_id,
                    "programme_libelle": programme_libelle,
                    "cabinet_id": sd.cabinet_id,
                    "cabinet_libelle": cabinet_libelle,
                    "chef_sous_direction_id": sd.chef_sous_direction_id,
                    "chef_sous_direction_nom": chef_sous_direction_nom,
                }
            )

        return JSONResponse(
            content=result,
            headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"},
        )
    except (ProgrammingError, OperationalError) as e:
        # Table n'existe pas encore - retourner un tableau vide
        logger.warning(f"Table sous_direction n'existe pas encore: {e}")
        return JSONResponse(
            content=[],
            headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"},
        )


@router.post("/api/sous-directions", name="api_create_sous_direction")
def api_create_sous_direction(
    code: str = Form(...),
    libelle: str = Form(...),
    description: str | None = Form(None),
    direction_id: int | None = Form(None),
    programme_id: int | None = Form(None),
    cabinet_id: int | None = Form(None),
    chef_sous_direction_id: int | None = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Créer une nouvelle sous-direction"""
    existing = session.exec(select(SousDirection).where(SousDirection.code == code)).first()
    if existing:
        raise HTTPException(400, f"Le code '{code}' existe déjà")

    # Validation : un seul parent doit être sélectionné
    parents = [p for p in [direction_id, programme_id, cabinet_id] if p is not None]
    if len(parents) > 1:
        raise HTTPException(400, "Une sous-direction ne peut être rattachée qu'à un seul parent (Direction, Programme ou Cabinet)")
    if len(parents) == 0:
        raise HTTPException(400, "Une sous-direction doit être rattachée à une Direction, un Programme ou un Cabinet")

    sous_direction = SousDirection(
        code=code,
        libelle=libelle,
        description=description,
        direction_id=direction_id,
        programme_id=programme_id,
        cabinet_id=cabinet_id,
        chef_sous_direction_id=chef_sous_direction_id if chef_sous_direction_id else None,
    )
    session.add(sous_direction)
    session.commit()
    session.refresh(sous_direction)

    logger.info(f"✅ Sous-direction créée : {code} - {libelle} par {current_user.email}")
    return {"ok": True, "id": sous_direction.id, "message": "Sous-direction créée avec succès"}


@router.put("/api/sous-directions/{sous_direction_id}", name="api_update_sous_direction")
def api_update_sous_direction(
    sous_direction_id: int,
    code: str = Form(...),
    libelle: str = Form(...),
    description: str | None = Form(None),
    direction_id: int | None = Form(None),
    programme_id: int | None = Form(None),
    cabinet_id: int | None = Form(None),
    chef_sous_direction_id: int | None = Form(None),
    actif: bool = Form(True),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Modifier une sous-direction"""
    sous_direction = session.get(SousDirection, sous_direction_id)
    if not sous_direction:
        raise HTTPException(404, "Sous-direction non trouvée")

    if code != sous_direction.code:
        existing = session.exec(select(SousDirection).where(SousDirection.code == code)).first()
        if existing:
            raise HTTPException(400, f"Le code '{code}' existe déjà")

    # Validation : un seul parent doit être sélectionné
    parents = [p for p in [direction_id, programme_id, cabinet_id] if p is not None]
    if len(parents) > 1:
        raise HTTPException(400, "Une sous-direction ne peut être rattachée qu'à un seul parent (Direction, Programme ou Cabinet)")
    if len(parents) == 0:
        raise HTTPException(400, "Une sous-direction doit être rattachée à une Direction, un Programme ou un Cabinet")

    sous_direction.code = code
    sous_direction.libelle = libelle
    sous_direction.description = description
    sous_direction.direction_id = direction_id
    sous_direction.programme_id = programme_id
    sous_direction.cabinet_id = cabinet_id
    sous_direction.chef_sous_direction_id = chef_sous_direction_id if chef_sous_direction_id else None
    sous_direction.actif = actif
    sous_direction.updated_at = datetime.utcnow()

    session.add(sous_direction)
    session.commit()

    logger.info(f"✅ Sous-direction modifiée : {code} par {current_user.email}")
    return {"ok": True, "message": "Sous-direction modifiée avec succès"}


@router.post("/api/sous-directions/{sous_direction_id}/reactivate", name="api_reactivate_sous_direction")
def api_reactivate_sous_direction(
    sous_direction_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)
):
    """Réactiver une sous-direction désactivée"""
    sous_direction = session.get(SousDirection, sous_direction_id)
    if not sous_direction:
        raise HTTPException(404, "Sous-direction non trouvée")

    sous_direction.actif = True
    sous_direction.updated_at = datetime.utcnow()
    session.add(sous_direction)
    session.commit()

    logger.info(f"✅ Sous-direction réactivée : {sous_direction.code} par {current_user.email}")
    return {"ok": True, "message": "Sous-direction réactivée avec succès"}


@router.delete("/api/sous-directions/{sous_direction_id}", name="api_delete_sous_direction")
def api_delete_sous_direction(
    sous_direction_id: int,
    hard_delete: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Supprimer une sous-direction (soft delete par défaut, hard delete si hard_delete=true)"""
    sous_direction = session.get(SousDirection, sous_direction_id)
    if not sous_direction:
        raise HTTPException(404, "Sous-direction non trouvée")

    if hard_delete:
        session.delete(sous_direction)
        session.commit()
        logger.warning(f"🗑️ Sous-direction SUPPRIMÉE DÉFINITIVEMENT : {sous_direction.code} par {current_user.email}")
        return {"ok": True, "message": "Sous-direction supprimée définitivement"}
    else:
        sous_direction.actif = False
        sous_direction.updated_at = datetime.utcnow()
        session.add(sous_direction)
        session.commit()
        logger.info(f"✅ Sous-direction désactivée : {sous_direction.code} par {current_user.email}")
        return {"ok": True, "message": "Sous-direction désactivée avec succès"}


# ============================================
# API - SERVICES
# ============================================


@router.get("/api/services", name="api_list_services_ref")
def api_list_services_ref(session: Session = Depends(get_session)):
    """Liste tous les services avec leurs directions et sous-directions"""
    from app.models.personnel import AgentComplet, Service
    from sqlalchemy.exc import ProgrammingError, OperationalError

    # Utiliser Service au lieu de ServiceDept pour avoir accès à chef_service_id
    services = session.exec(select(Service).order_by(Service.code)).all()
    directions = {d.id: d for d in session.exec(select(Direction)).all()}
    programmes = {p.id: p for p in session.exec(select(Programme)).all()}
    
    # Récupérer les cabinets si la table existe
    try:
        cabinets = {c.id: c for c in session.exec(select(Cabinet)).all()}
    except (ProgrammingError, OperationalError):
        logger.warning("Table cabinet n'existe pas encore dans la base de données")
        cabinets = {}
    
    # Récupérer les sous-directions si la table existe
    try:
        sous_directions = {sd.id: sd for sd in session.exec(select(SousDirection)).all()}
    except (ProgrammingError, OperationalError):
        logger.warning("Table sous_direction n'existe pas encore dans la base de données")
        sous_directions = {}

    result = []
    for s in services:
        direction_libelle = ""  # Chaîne vide au lieu de None pour forcer l'inclusion dans le JSON
        if s.direction_id and s.direction_id in directions:
            direction_libelle = directions[s.direction_id].libelle

        sous_direction_libelle = ""
        if s.sous_direction_id and s.sous_direction_id in sous_directions:
            sous_direction_libelle = sous_directions[s.sous_direction_id].libelle

        programme_libelle = ""
        if s.programme_id and s.programme_id in programmes:
            programme_libelle = programmes[s.programme_id].libelle

        cabinet_libelle = ""
        if s.cabinet_id and s.cabinet_id in cabinets:
            cabinet_libelle = cabinets[s.cabinet_id].libelle

        chef_service_nom = ""
        if s.chef_service_id:
            chef = session.get(AgentComplet, s.chef_service_id)
            if chef:
                chef_service_nom = f"{chef.nom} {chef.prenom}"

        result.append(
            {
                "id": s.id,
                "code": s.code,
                "libelle": s.libelle,
                "description": s.description or "",
                "actif": s.actif,
                "sous_direction_id": s.sous_direction_id,
                "sous_direction_libelle": sous_direction_libelle,
                "direction_id": s.direction_id,
                "direction_libelle": direction_libelle,
                "programme_id": s.programme_id,
                "programme_libelle": programme_libelle,
                "cabinet_id": s.cabinet_id,
                "cabinet_libelle": cabinet_libelle,
                "chef_service_id": s.chef_service_id,
                "chef_service_nom": chef_service_nom,
            }
        )

    # Retourner avec headers no-cache pour forcer le rafraîchissement
    return JSONResponse(
        content=result,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"},
    )


@router.post("/api/services", name="api_create_service")
def api_create_service(
    code: str = Form(...),
    libelle: str = Form(...),
    description: str | None = Form(None),
    sous_direction_id: str | None = Form(None),
    direction_id: str | None = Form(None),
    programme_id: str | None = Form(None),
    cabinet_id: str | None = Form(None),
    chef_service_id: str | None = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Créer un nouveau service"""
    # Convertir les IDs de string à int, ou None si vide/None
    def parse_id(value: str | None) -> int | None:
        if value is None or value == '' or value == 'null' or value == 'undefined':
            return None
        try:
            parsed = int(value)
            return parsed if parsed > 0 else None
        except (ValueError, TypeError):
            return None
    
    sous_direction_id_int = parse_id(sous_direction_id)
    direction_id_int = parse_id(direction_id)
    programme_id_int = parse_id(programme_id)
    cabinet_id_int = parse_id(cabinet_id)
    chef_service_id_int = parse_id(chef_service_id)
    
    # Validation : un seul parent doit être sélectionné
    parents = [p for p in [sous_direction_id_int, direction_id_int, programme_id_int, cabinet_id_int] if p is not None]
    if len(parents) > 1:
        raise HTTPException(400, "Un service ne peut être rattaché qu'à un seul parent (Sous-direction, Direction, Programme ou Cabinet)")
    if len(parents) == 0:
        raise HTTPException(400, "Un service doit être rattaché à une Sous-direction, une Direction, un Programme ou un Cabinet")
    
    existing = session.exec(select(Service).where(Service.code == code)).first()
    if existing:
        raise HTTPException(400, f"Le code '{code}' existe déjà")
    
    service = Service(
        code=code,
        libelle=libelle,
        description=description,
        sous_direction_id=sous_direction_id_int,
        direction_id=direction_id_int,
        programme_id=programme_id_int,
        cabinet_id=cabinet_id_int,
        chef_service_id=chef_service_id_int,
        actif=True,
    )
    
    session.add(service)
    session.commit()
    session.refresh(service)

    logger.info(f"✅ Service créé : {code} - {libelle} par {current_user.email}")
    return {"ok": True, "id": service.id, "message": "Service créé avec succès"}


@router.put("/api/services/{service_id}", name="api_update_service")
def api_update_service(
    service_id: int,
    code: str = Form(...),
    libelle: str = Form(...),
    description: str | None = Form(None),
    sous_direction_id: str | None = Form(None),
    direction_id: str | None = Form(None),
    programme_id: str | None = Form(None),
    cabinet_id: str | None = Form(None),
    chef_service_id: str | None = Form(None),
    actif: bool = Form(True),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Modifier un service"""
    # Convertir les IDs de string à int, ou None si vide/None
    def parse_id(value: str | None) -> int | None:
        if value is None or value == '' or value == 'null' or value == 'undefined':
            return None
        try:
            parsed = int(value)
            return parsed if parsed > 0 else None
        except (ValueError, TypeError):
            return None
    
    sous_direction_id_int = parse_id(sous_direction_id)
    direction_id_int = parse_id(direction_id)
    programme_id_int = parse_id(programme_id)
    cabinet_id_int = parse_id(cabinet_id)
    chef_service_id_int = parse_id(chef_service_id)
    
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(404, "Service non trouvé")

    # Validation : un seul parent doit être sélectionné
    parents = [p for p in [sous_direction_id_int, direction_id_int, programme_id_int, cabinet_id_int] if p is not None]
    if len(parents) > 1:
        raise HTTPException(400, "Un service ne peut être rattaché qu'à un seul parent (Sous-direction, Direction, Programme ou Cabinet)")
    if len(parents) == 0:
        raise HTTPException(400, "Un service doit être rattaché à une Sous-direction, une Direction, un Programme ou un Cabinet")

    if code != service.code:
        existing = session.exec(select(Service).where(Service.code == code)).first()
        if existing:
            raise HTTPException(400, f"Le code '{code}' existe déjà")

    service.code = code
    service.libelle = libelle
    service.description = description
    service.sous_direction_id = sous_direction_id_int
    service.direction_id = direction_id_int
    service.programme_id = programme_id_int
    service.cabinet_id = cabinet_id_int
    service.chef_service_id = chef_service_id_int
    service.actif = actif

    session.add(service)
    session.commit()

    logger.info(f"✅ Service modifié : {code} par {current_user.email}")
    return {"ok": True, "message": "Service modifié avec succès"}


@router.post("/api/services/{service_id}/reactivate", name="api_reactivate_service")
def api_reactivate_service(
    service_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)
):
    """Réactiver un service désactivé"""
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(404, "Service non trouvé")

    service.actif = True
    session.add(service)
    session.commit()

    logger.info(f"✅ Service réactivé : {service.code} par {current_user.email}")
    return {"ok": True, "message": "Service réactivé avec succès"}


@router.delete("/api/services/{service_id}", name="api_delete_service")
def api_delete_service(
    service_id: int,
    hard_delete: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Supprimer un service (soft delete par défaut, hard delete si hard_delete=true)"""
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(404, "Service non trouvé")

    if hard_delete:
        session.delete(service)
        session.commit()
        logger.warning(f"🗑️ Service SUPPRIMÉ DÉFINITIVEMENT : {service.code} par {current_user.email}")
        return {"ok": True, "message": "Service supprimé définitivement"}
    else:
        service.actif = False
        session.add(service)
        session.commit()
        logger.info(f"✅ Service désactivé : {service.code} par {current_user.email}")
        return {"ok": True, "message": "Service désactivé avec succès"}


# ============================================
# API - GRADES
# ============================================


@router.get("/api/grades", name="api_list_grades_ref")
def api_list_grades_ref(session: Session = Depends(get_session)):
    """Liste tous les grades"""
    grades = session.exec(select(GradeComplet).order_by(GradeComplet.code)).all()

    return [
        {
            "id": g.id,
            "code": g.code,
            "libelle": g.libelle,
            "categorie": str(g.categorie),  # Convertir en string
            "echelon_min": g.echelon_min,
            "echelon_max": g.echelon_max,
            "actif": g.actif,
        }
        for g in grades
    ]


@router.post("/api/grades", name="api_create_grade")
def api_create_grade(
    code: str = Form(...),
    libelle: str = Form(...),
    categorie: str = Form(...),
    echelon_min: int = Form(1),
    echelon_max: int = Form(5),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Créer un nouveau grade"""
    existing = session.exec(select(GradeComplet).where(GradeComplet.code == code)).first()
    if existing:
        raise HTTPException(400, f"Le code '{code}' existe déjà")

    # Convertir la catégorie (ex: "A" → GradeCategory.A) et récupérer sa valeur string
    try:
        categorie_enum = getattr(GradeCategory, categorie)
        categorie_value = categorie_enum.value  # Extraire la valeur string
    except AttributeError:
        raise HTTPException(400, f"Catégorie invalide: {categorie}")

    grade = GradeComplet(
        code=code, libelle=libelle, categorie=categorie_value, echelon_min=echelon_min, echelon_max=echelon_max
    )
    session.add(grade)
    session.commit()
    session.refresh(grade)

    logger.info(f"✅ Grade créé : {code} - {libelle} par {current_user.email}")
    return {"ok": True, "id": grade.id, "message": "Grade créé avec succès"}


@router.put("/api/grades/{grade_id}", name="api_update_grade")
def api_update_grade(
    grade_id: int,
    code: str = Form(...),
    libelle: str = Form(...),
    categorie: str = Form(...),
    echelon_min: int = Form(1),
    echelon_max: int = Form(5),
    actif: bool = Form(True),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Modifier un grade"""
    grade = session.get(GradeComplet, grade_id)
    if not grade:
        raise HTTPException(404, "Grade non trouvé")

    if code != grade.code:
        existing = session.exec(select(GradeComplet).where(GradeComplet.code == code)).first()
        if existing:
            raise HTTPException(400, f"Le code '{code}' existe déjà")

    # Convertir la catégorie (ex: "A" → GradeCategory.A) et récupérer sa valeur string
    try:
        categorie_enum = getattr(GradeCategory, categorie)
        categorie_value = categorie_enum.value  # Extraire la valeur string
    except AttributeError:
        raise HTTPException(400, f"Catégorie invalide: {categorie}")

    grade.code = code
    grade.libelle = libelle
    grade.categorie = categorie_value
    grade.echelon_min = echelon_min
    grade.echelon_max = echelon_max
    grade.actif = actif
    grade.updated_at = datetime.utcnow()

    session.add(grade)
    session.commit()

    logger.info(f"✅ Grade modifié : {code} par {current_user.email}")
    return {"ok": True, "message": "Grade modifié avec succès"}


@router.post("/api/grades/{grade_id}/reactivate", name="api_reactivate_grade")
def api_reactivate_grade(
    grade_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)
):
    """Réactiver un grade désactivé"""
    grade = session.get(GradeComplet, grade_id)
    if not grade:
        raise HTTPException(404, "Grade non trouvé")

    grade.actif = True
    grade.updated_at = datetime.utcnow()
    session.add(grade)
    session.commit()

    logger.info(f"✅ Grade réactivé : {grade.code} par {current_user.email}")
    return {"ok": True, "message": "Grade réactivé avec succès"}


@router.delete("/api/grades/{grade_id}", name="api_delete_grade")
def api_delete_grade(
    grade_id: int,
    hard_delete: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Supprimer un grade (soft delete par défaut, hard delete si hard_delete=true)"""
    grade = session.get(GradeComplet, grade_id)
    if not grade:
        raise HTTPException(404, "Grade non trouvé")

    if hard_delete:
        session.delete(grade)
        session.commit()
        logger.warning(f"🗑️ Grade SUPPRIMÉ DÉFINITIVEMENT : {grade.code} par {current_user.email}")
        return {"ok": True, "message": "Grade supprimé définitivement"}
    else:
        grade.actif = False
        grade.updated_at = datetime.utcnow()
        session.add(grade)
        session.commit()
        logger.info(f"✅ Grade désactivé : {grade.code} par {current_user.email}")
        return {"ok": True, "message": "Grade désactivé avec succès"}


# ============================================
# API - CATÉGORIES D'ARTICLES (STOCK)
# ============================================


@router.get("/api/categories", name="api_list_categories_ref")
def api_list_categories_ref(session: Session = Depends(get_session)):
    """Liste toutes les catégories d'articles"""
    categories = session.exec(select(CategorieArticle).order_by(CategorieArticle.code)).all()
    
    return [
        {
            "id": c.id,
            "code": c.code,
            "libelle": c.libelle,
            "description": c.description or "",
        }
        for c in categories
    ]


@router.post("/api/categories", name="api_create_categorie")
def api_create_categorie(
    code: str = Form(...),
    libelle: str = Form(...),
    description: str | None = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Créer une nouvelle catégorie d'article"""
    existing = session.exec(select(CategorieArticle).where(CategorieArticle.code == code)).first()
    if existing:
        raise HTTPException(400, f"Le code '{code}' existe déjà")

    categorie = CategorieArticle(code=code, libelle=libelle, description=description)
    session.add(categorie)
    session.commit()
    session.refresh(categorie)

    logger.info(f"✅ Catégorie d'article créée : {code} - {libelle} par {current_user.email}")
    return {"ok": True, "id": categorie.id, "message": "Catégorie créée avec succès"}


@router.put("/api/categories/{categorie_id}", name="api_update_categorie")
def api_update_categorie(
    categorie_id: int,
    code: str = Form(...),
    libelle: str = Form(...),
    description: str | None = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Modifier une catégorie d'article"""
    categorie = session.get(CategorieArticle, categorie_id)
    if not categorie:
        raise HTTPException(404, "Catégorie non trouvée")

    if code != categorie.code:
        existing = session.exec(select(CategorieArticle).where(CategorieArticle.code == code)).first()
        if existing:
            raise HTTPException(400, f"Le code '{code}' existe déjà")

    categorie.code = code
    categorie.libelle = libelle
    categorie.description = description

    session.add(categorie)
    session.commit()

    logger.info(f"✅ Catégorie modifiée : {code} par {current_user.email}")
    return {"ok": True, "message": "Catégorie modifiée avec succès"}


@router.delete("/api/categories/{categorie_id}", name="api_delete_categorie")
def api_delete_categorie(
    categorie_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Supprimer une catégorie d'article (suppression définitive uniquement)"""
    categorie = session.get(CategorieArticle, categorie_id)
    if not categorie:
        raise HTTPException(404, "Catégorie non trouvée")

    session.delete(categorie)
    session.commit()
    logger.warning(f"🗑️ Catégorie SUPPRIMÉE : {categorie.code} par {current_user.email}")
    return {"ok": True, "message": "Catégorie supprimée avec succès"}
