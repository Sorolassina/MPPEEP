# app/api/v1/endpoints/referentiels.py
"""
Endpoints pour la gestion des référentiels RH/Personnel
(Programmes, Directions, Services, Grades)
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import Session, select
from datetime import datetime

from app.db.session import get_session
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.models.personnel import Programme, Direction, GradeComplet
from app.models.rh import ServiceDept
from app.core.enums import GradeCategory
from app.templates import templates, get_template_context
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


# ============================================
# PAGE PRINCIPALE RÉFÉRENTIELS
# ============================================

@router.get("/", response_class=HTMLResponse, name="referentiels_home")
def referentiels_home(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Page principale de gestion des référentiels
    """
    # Compter les référentiels
    programmes_raw = session.exec(select(Programme)).all()
    directions_raw = session.exec(select(Direction)).all()
    services_raw = session.exec(select(ServiceDept)).all()
    grades_raw = session.exec(select(GradeComplet)).all()
    
    # Créer les dictionnaires de référence
    programmes_dict = {p.id: p for p in programmes_raw}
    directions_dict = {d.id: d for d in directions_raw}
    
    # Enrichir les directions avec programme_libelle
    directions_enriched = []
    for d in directions_raw:
        direction_dict = {
            "id": d.id,
            "code": d.code,
            "libelle": d.libelle,
            "description": d.description or "",
            "actif": d.actif,
            "programme_id": d.programme_id,
            "programme_libelle": programmes_dict[d.programme_id].libelle if d.programme_id and d.programme_id in programmes_dict else ""
        }
        directions_enriched.append(direction_dict)
    
    # Enrichir les services avec direction_libelle
    services_enriched = []
    for s in services_raw:
        service_dict = {
            "id": s.id,
            "code": s.code,
            "libelle": s.libelle,
            "description": s.description or "",
            "actif": s.actif,
            "direction_id": s.direction_id,
            "direction_libelle": directions_dict[s.direction_id].libelle if s.direction_id and s.direction_id in directions_dict else ""
        }
        services_enriched.append(service_dict)
    
    return templates.TemplateResponse(
        "pages/referentiels.html",
        get_template_context(
            request,
            nb_programmes=len(programmes_raw),
            nb_directions=len(directions_raw),
            nb_services=len(services_raw),
            nb_grades=len(grades_raw),
            programmes=programmes_raw,
            directions=directions_enriched,  # ← Directions enrichies avec programme_libelle
            services=services_enriched,  # ← Services enrichis avec direction_libelle
            grades=grades_raw,
            current_user=current_user
        )
    )


# ============================================
# API - PROGRAMMES
# ============================================

@router.get("/api/programmes", name="api_list_programmes_ref")
def api_list_programmes_ref(session: Session = Depends(get_session)):
    """Liste tous les programmes"""
    programmes = session.exec(select(Programme).order_by(Programme.code)).all()
    return [
        {
            "id": p.id,
            "code": p.code,
            "libelle": p.libelle,
            "description": p.description,
            "actif": p.actif
        }
        for p in programmes
    ]


@router.post("/api/programmes", name="api_create_programme")
def api_create_programme(
    code: str = Form(...),
    libelle: str = Form(...),
    description: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Créer un nouveau programme"""
    # Vérifier si le code existe déjà
    existing = session.exec(select(Programme).where(Programme.code == code)).first()
    if existing:
        raise HTTPException(400, f"Le code '{code}' existe déjà")
    
    programme = Programme(code=code, libelle=libelle, description=description)
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
    description: Optional[str] = Form(None),
    actif: bool = Form(True),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Modifier un programme"""
    programme = session.get(Programme, programme_id)
    if not programme:
        raise HTTPException(404, "Programme non trouvé")
    
    # Vérifier si le nouveau code n'existe pas déjà (sauf pour lui-même)
    if code != programme.code:
        existing = session.exec(select(Programme).where(Programme.code == code)).first()
        if existing:
            raise HTTPException(400, f"Le code '{code}' existe déjà")
    
    programme.code = code
    programme.libelle = libelle
    programme.description = description
    programme.actif = actif
    programme.updated_at = datetime.utcnow()
    
    session.add(programme)
    session.commit()
    
    logger.info(f"✅ Programme modifié : {code} par {current_user.email}")
    return {"ok": True, "message": "Programme modifié avec succès"}


@router.post("/api/programmes/{programme_id}/reactivate", name="api_reactivate_programme")
def api_reactivate_programme(
    programme_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
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
    directions = session.exec(select(Direction).order_by(Direction.code)).all()
    programmes = {p.id: p for p in session.exec(select(Programme)).all()}
    
    result = []
    for d in directions:
        programme_libelle = ""  # Chaîne vide au lieu de None
        if d.programme_id and d.programme_id in programmes:
            programme_libelle = programmes[d.programme_id].libelle
        
        result.append({
            "id": d.id,
            "code": d.code,
            "libelle": d.libelle,
            "description": d.description or "",
            "actif": d.actif,
            "programme_id": d.programme_id,
            "programme_libelle": programme_libelle
        })
    
    return JSONResponse(
        content=result,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@router.post("/api/directions", name="api_create_direction")
def api_create_direction(
    code: str = Form(...),
    libelle: str = Form(...),
    description: Optional[str] = Form(None),
    programme_id: Optional[int] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Créer une nouvelle direction"""
    existing = session.exec(select(Direction).where(Direction.code == code)).first()
    if existing:
        raise HTTPException(400, f"Le code '{code}' existe déjà")
    
    direction = Direction(code=code, libelle=libelle, description=description, programme_id=programme_id)
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
    description: Optional[str] = Form(None),
    programme_id: Optional[int] = Form(None),
    actif: bool = Form(True),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Modifier une direction"""
    direction = session.get(Direction, direction_id)
    if not direction:
        raise HTTPException(404, "Direction non trouvée")
    
    if code != direction.code:
        existing = session.exec(select(Direction).where(Direction.code == code)).first()
        if existing:
            raise HTTPException(400, f"Le code '{code}' existe déjà")
    
    direction.code = code
    direction.libelle = libelle
    direction.description = description
    direction.programme_id = programme_id
    direction.actif = actif
    direction.updated_at = datetime.utcnow()
    
    session.add(direction)
    session.commit()
    
    logger.info(f"✅ Direction modifiée : {code} par {current_user.email}")
    return {"ok": True, "message": "Direction modifiée avec succès"}


@router.post("/api/directions/{direction_id}/reactivate", name="api_reactivate_direction")
def api_reactivate_direction(
    direction_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
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
# API - SERVICES
# ============================================

@router.get("/api/services", name="api_list_services_ref")
def api_list_services_ref(session: Session = Depends(get_session)):
    """Liste tous les services avec leurs directions"""
    services = session.exec(select(ServiceDept).order_by(ServiceDept.code)).all()
    directions = {d.id: d for d in session.exec(select(Direction)).all()}
    
    result = []
    for s in services:
        direction_libelle = ""  # Chaîne vide au lieu de None pour forcer l'inclusion dans le JSON
        if s.direction_id and s.direction_id in directions:
            direction_libelle = directions[s.direction_id].libelle
        
        result.append({
            "id": s.id,
            "code": s.code,
            "libelle": s.libelle,
            "description": s.description or "",
            "actif": s.actif,
            "direction_id": s.direction_id,
            "direction_libelle": direction_libelle
        })
    
    # Retourner avec headers no-cache pour forcer le rafraîchissement
    return JSONResponse(
        content=result,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@router.post("/api/services", name="api_create_service")
def api_create_service(
    code: str = Form(...),
    libelle: str = Form(...),
    description: Optional[str] = Form(None),
    direction_id: Optional[int] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Créer un nouveau service"""
    existing = session.exec(select(ServiceDept).where(ServiceDept.code == code)).first()
    if existing:
        raise HTTPException(400, f"Le code '{code}' existe déjà")
    
    service = ServiceDept(
        code=code, 
        libelle=libelle, 
        description=description, 
        direction_id=direction_id,
        actif=True
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
    description: Optional[str] = Form(None),
    direction_id: Optional[int] = Form(None),
    actif: bool = Form(True),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Modifier un service"""
    service = session.get(ServiceDept, service_id)
    if not service:
        raise HTTPException(404, "Service non trouvé")
    
    if code != service.code:
        existing = session.exec(select(ServiceDept).where(ServiceDept.code == code)).first()
        if existing:
            raise HTTPException(400, f"Le code '{code}' existe déjà")
    
    service.code = code
    service.libelle = libelle
    service.description = description
    service.direction_id = direction_id
    service.actif = actif
    
    session.add(service)
    session.commit()
    
    logger.info(f"✅ Service modifié : {code} par {current_user.email}")
    return {"ok": True, "message": "Service modifié avec succès"}


@router.post("/api/services/{service_id}/reactivate", name="api_reactivate_service")
def api_reactivate_service(
    service_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Réactiver un service désactivé"""
    service = session.get(ServiceDept, service_id)
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
    current_user: User = Depends(get_current_user)
):
    """Supprimer un service (soft delete par défaut, hard delete si hard_delete=true)"""
    service = session.get(ServiceDept, service_id)
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
            "actif": g.actif
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
    current_user: User = Depends(get_current_user)
):
    """Créer un nouveau grade"""
    existing = session.exec(select(GradeComplet).where(GradeComplet.code == code)).first()
    if existing:
        raise HTTPException(400, f"Le code '{code}' existe déjà")
    
    # Convertir la catégorie (ex: "A" → GradeCategory.A)
    try:
        categorie_enum = getattr(GradeCategory, categorie)
    except AttributeError:
        raise HTTPException(400, f"Catégorie invalide: {categorie}")
    
    grade = GradeComplet(
        code=code,
        libelle=libelle,
        categorie=categorie_enum,
        echelon_min=echelon_min,
        echelon_max=echelon_max
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
    current_user: User = Depends(get_current_user)
):
    """Modifier un grade"""
    grade = session.get(GradeComplet, grade_id)
    if not grade:
        raise HTTPException(404, "Grade non trouvé")
    
    if code != grade.code:
        existing = session.exec(select(GradeComplet).where(GradeComplet.code == code)).first()
        if existing:
            raise HTTPException(400, f"Le code '{code}' existe déjà")
    
    # Convertir la catégorie (ex: "A" → GradeCategory.A)
    try:
        categorie_enum = getattr(GradeCategory, categorie)
    except AttributeError:
        raise HTTPException(400, f"Catégorie invalide: {categorie}")
    
    grade.code = code
    grade.libelle = libelle
    grade.categorie = categorie_enum
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
    grade_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
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

