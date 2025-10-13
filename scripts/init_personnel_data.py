#!/usr/bin/env python3
"""
Script d'initialisation des données de référence du personnel
Crée les programmes, directions, services et grades de base
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from app.db.session import engine
from app.models.personnel import Programme, Direction, Service, GradeComplet
from app.core.enums import GradeCategory


def init_programmes(session: Session):
    """Initialiser les programmes budgétaires"""
    programmes_data = [
        {"code": "P01", "libelle": "Pilotage et Soutien Institutionnel", "description": "Programme de pilotage"},
        {"code": "P02", "libelle": "Gestion du Portefeuille de l'État", "description": "Gestion des participations"},
        {"code": "P03", "libelle": "Gestion du Patrimoine de l'État", "description": "Gestion du patrimoine"},
    ]
    
    for prog_data in programmes_data:
        # Vérifier si existe déjà
        existing = session.exec(
            select(Programme).where(Programme.code == prog_data["code"])
        ).first()
        
        if not existing:
            prog = Programme(**prog_data)
            session.add(prog)
            print(f"✅ Programme créé : {prog.code} - {prog.libelle}")
        else:
            print(f"⏭️  Programme existe déjà : {prog_data['code']}")
    
    session.commit()


def init_directions(session: Session):
    """Initialiser les directions"""
    # Récupérer les programmes
    programmes = {p.code: p for p in session.exec(select(Programme)).all()}
    
    directions_data = [
        {"code": "DG", "libelle": "Direction Générale", "programme_id": programmes.get("P01").id if programmes.get("P01") else None},
        {"code": "DAF", "libelle": "Direction Administrative et Financière", "programme_id": programmes.get("P01").id if programmes.get("P01") else None},
        {"code": "DRH", "libelle": "Direction des Ressources Humaines", "programme_id": programmes.get("P01").id if programmes.get("P01") else None},
        {"code": "DPE", "libelle": "Direction du Portefeuille de l'État", "programme_id": programmes.get("P02").id if programmes.get("P02") else None},
        {"code": "DPAT", "libelle": "Direction du Patrimoine de l'État", "programme_id": programmes.get("P03").id if programmes.get("P03") else None},
    ]
    
    for dir_data in directions_data:
        # Vérifier si existe déjà
        existing = session.exec(
            select(Direction).where(Direction.code == dir_data["code"])
        ).first()
        
        if not existing:
            direction = Direction(**dir_data)
            session.add(direction)
            print(f"✅ Direction créée : {direction.code} - {direction.libelle}")
        else:
            print(f"⏭️  Direction existe déjà : {dir_data['code']}")
    
    session.commit()


def init_services(session: Session):
    """Initialiser les services"""
    # Récupérer les directions
    directions = {d.code: d for d in session.exec(select(Direction)).all()}
    
    services_data = [
        # Services DAF
        {"code": "SCPT", "libelle": "Service Comptabilité", "direction_id": directions.get("DAF").id if directions.get("DAF") else None},
        {"code": "SBUD", "libelle": "Service Budget", "direction_id": directions.get("DAF").id if directions.get("DAF") else None},
        {"code": "SAPV", "libelle": "Service Approvisionnement", "direction_id": directions.get("DAF").id if directions.get("DAF") else None},
        
        # Services DRH
        {"code": "SCAR", "libelle": "Service Carrière", "direction_id": directions.get("DRH").id if directions.get("DRH") else None},
        {"code": "SPAY", "libelle": "Service Paie", "direction_id": directions.get("DRH").id if directions.get("DRH") else None},
        {"code": "SFOR", "libelle": "Service Formation", "direction_id": directions.get("DRH").id if directions.get("DRH") else None},
        
        # Services DPE
        {"code": "SPAR", "libelle": "Service Participations", "direction_id": directions.get("DPE").id if directions.get("DPE") else None},
        {"code": "SETU", "libelle": "Service Études", "direction_id": directions.get("DPE").id if directions.get("DPE") else None},
        
        # Services DPAT
        {"code": "SGIM", "libelle": "Service Gestion Immobilière", "direction_id": directions.get("DPAT").id if directions.get("DPAT") else None},
        {"code": "SINV", "libelle": "Service Inventaire", "direction_id": directions.get("DPAT").id if directions.get("DPAT") else None},
    ]
    
    for serv_data in services_data:
        # Vérifier si existe déjà
        existing = session.exec(
            select(Service).where(Service.code == serv_data["code"])
        ).first()
        
        if not existing:
            service = Service(**serv_data)
            session.add(service)
            print(f"✅ Service créé : {service.code} - {service.libelle}")
        else:
            print(f"⏭️  Service existe déjà : {serv_data['code']}")
    
    session.commit()


def init_grades(session: Session):
    """Initialiser les grades"""
    grades_data = [
        # Catégorie A
        {"code": "A1", "libelle": "Administrateur Civil", "categorie": GradeCategory.A, "echelon_min": 1, "echelon_max": 7},
        {"code": "A2", "libelle": "Attaché d'Administration", "categorie": GradeCategory.A, "echelon_min": 1, "echelon_max": 6},
        {"code": "A3", "libelle": "Secrétaire d'Administration", "categorie": GradeCategory.A, "echelon_min": 1, "echelon_max": 5},
        
        # Catégorie B
        {"code": "B1", "libelle": "Contrôleur des Services Administratifs", "categorie": GradeCategory.B, "echelon_min": 1, "echelon_max": 6},
        {"code": "B2", "libelle": "Contrôleur du Trésor", "categorie": GradeCategory.B, "echelon_min": 1, "echelon_max": 5},
        {"code": "B3", "libelle": "Secrétaire d'Administration", "categorie": GradeCategory.B, "echelon_min": 1, "echelon_max": 5},
        
        # Catégorie C
        {"code": "C1", "libelle": "Commis des Services Administratifs", "categorie": GradeCategory.C, "echelon_min": 1, "echelon_max": 5},
        {"code": "C2", "libelle": "Agent Administratif", "categorie": GradeCategory.C, "echelon_min": 1, "echelon_max": 4},
        {"code": "C3", "libelle": "Aide Administratif", "categorie": GradeCategory.C, "echelon_min": 1, "echelon_max": 3},
        
        # Catégorie D
        {"code": "D1", "libelle": "Agent de Bureau", "categorie": GradeCategory.D, "echelon_min": 1, "echelon_max": 4},
        {"code": "D2", "libelle": "Homme de Service", "categorie": GradeCategory.D, "echelon_min": 1, "echelon_max": 3},
    ]
    
    for grade_data in grades_data:
        # Vérifier si existe déjà
        existing = session.exec(
            select(GradeComplet).where(GradeComplet.code == grade_data["code"])
        ).first()
        
        if not existing:
            grade = GradeComplet(**grade_data)
            session.add(grade)
            print(f"✅ Grade créé : {grade.code} - {grade.libelle} ({grade.categorie.value})")
        else:
            print(f"⏭️  Grade existe déjà : {grade_data['code']}")
    
    session.commit()


def main():
    """Fonction principale"""
    print("\n" + "="*60)
    print("🚀 INITIALISATION DES DONNÉES DE RÉFÉRENCE DU PERSONNEL")
    print("="*60 + "\n")
    
    with Session(engine) as session:
        print("📋 Étape 1/4 : Création des Programmes...")
        init_programmes(session)
        
        print("\n📋 Étape 2/4 : Création des Directions...")
        init_directions(session)
        
        print("\n📋 Étape 3/4 : Création des Services...")
        init_services(session)
        
        print("\n📋 Étape 4/4 : Création des Grades...")
        init_grades(session)
    
    print("\n" + "="*60)
    print("✅ INITIALISATION TERMINÉE AVEC SUCCÈS !")
    print("="*60 + "\n")
    
    # Afficher un résumé
    with Session(engine) as session:
        nb_programmes = session.exec(select(Programme)).all()
        nb_directions = session.exec(select(Direction)).all()
        nb_services = session.exec(select(Service)).all()
        nb_grades = session.exec(select(GradeComplet)).all()
        
        print("📊 RÉSUMÉ :")
        print(f"  • Programmes : {len(nb_programmes)}")
        print(f"  • Directions : {len(nb_directions)}")
        print(f"  • Services : {len(nb_services)}")
        print(f"  • Grades : {len(nb_grades)}")
        print()


if __name__ == "__main__":
    main()

