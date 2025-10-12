#!/usr/bin/env python3
"""
Script pour initialiser la structure organisationnelle de base
(Programmes, Directions, Services)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import select
from app.db.session import get_session
from app.models.personnel import Programme, Direction, Service

print("=" * 70)
print("🏛️ Initialisation de la structure organisationnelle")
print("=" * 70)

session = next(get_session())

try:
    # ==========================
    # PROGRAMMES
    # ==========================
    programmes_data = [
        {
            "code": "P01",
            "libelle": "Administration générale",
            "description": "Pilotage et coordination de l'administration publique"
        },
        {
            "code": "P02",
            "libelle": "Gestion des établissements publics nationaux",
            "description": "Supervision et coordination des EPN"
        },
        {
            "code": "P03",
            "libelle": "Gestion du portefeuille de l'État",
            "description": "Gestion des participations de l'État"
        }
    ]
    
    programmes_created = {}
    print("\n📋 Création des Programmes...")
    for prog_data in programmes_data:
        existing = session.exec(
            select(Programme).where(Programme.code == prog_data["code"])
        ).first()
        
        if existing:
            print(f"   ⏭️  Programme {prog_data['code']} existe déjà")
            programmes_created[prog_data["code"]] = existing
        else:
            prog = Programme(**prog_data)
            session.add(prog)
            session.flush()  # Pour obtenir l'ID
            programmes_created[prog_data["code"]] = prog
            print(f"   ✅ Programme {prog_data['code']} créé")
    
    # ==========================
    # DIRECTIONS
    # ==========================
    directions_data = [
        {
            "code": "DMG",
            "libelle": "Direction des Moyens Généraux",
            "description": "Gestion des moyens matériels et logistiques",
            "programme_code": "P01"
        },
        {
            "code": "DRH",
            "libelle": "Direction des Ressources Humaines",
            "description": "Gestion du personnel et de la carrière",
            "programme_code": "P01"
        },
        {
            "code": "DB",
            "libelle": "Direction du Budget",
            "description": "Élaboration et suivi budgétaire",
            "programme_code": "P01"
        },
        {
            "code": "DEPN",
            "libelle": "Direction des Établissements Publics Nationaux",
            "description": "Supervision des EPN",
            "programme_code": "P02"
        },
        {
            "code": "DPE",
            "libelle": "Direction du Portefeuille de l'État",
            "description": "Gestion des participations",
            "programme_code": "P03"
        }
    ]
    
    directions_created = {}
    print("\n🏢 Création des Directions...")
    for dir_data in directions_data:
        existing = session.exec(
            select(Direction).where(Direction.code == dir_data["code"])
        ).first()
        
        if existing:
            print(f"   ⏭️  Direction {dir_data['code']} existe déjà")
            directions_created[dir_data["code"]] = existing
        else:
            prog_code = dir_data.pop("programme_code")
            dir_data["programme_id"] = programmes_created[prog_code].id
            direction = Direction(**dir_data)
            session.add(direction)
            session.flush()
            directions_created[dir_data["code"]] = direction
            print(f"   ✅ Direction {dir_data['code']} créée")
    
    # ==========================
    # SERVICES
    # ==========================
    services_data = [
        # Services DMG
        {
            "code": "S-LOG",
            "libelle": "Service Logistique",
            "description": "Gestion du parc automobile et des équipements",
            "direction_code": "DMG"
        },
        {
            "code": "S-MAT",
            "libelle": "Service du Matériel",
            "description": "Gestion des fournitures et matériels",
            "direction_code": "DMG"
        },
        # Services DRH
        {
            "code": "S-CARR",
            "libelle": "Service de la Carrière",
            "description": "Gestion de la carrière des agents",
            "direction_code": "DRH"
        },
        {
            "code": "S-FORM",
            "libelle": "Service de la Formation",
            "description": "Formation continue du personnel",
            "direction_code": "DRH"
        },
        {
            "code": "S-SOC",
            "libelle": "Service Social",
            "description": "Action sociale et œuvres sociales",
            "direction_code": "DRH"
        },
        # Services DB
        {
            "code": "S-PREP",
            "libelle": "Service de Préparation Budgétaire",
            "description": "Élaboration du budget",
            "direction_code": "DB"
        },
        {
            "code": "S-EXEC",
            "libelle": "Service d'Exécution Budgétaire",
            "description": "Suivi de l'exécution",
            "direction_code": "DB"
        },
        {
            "code": "S-COMPTA",
            "libelle": "Service Comptabilité",
            "description": "Comptabilité générale",
            "direction_code": "DB"
        }
    ]
    
    print("\n🏪 Création des Services...")
    services_count = 0
    for serv_data in services_data:
        existing = session.exec(
            select(Service).where(Service.code == serv_data["code"])
        ).first()
        
        if existing:
            print(f"   ⏭️  Service {serv_data['code']} existe déjà")
        else:
            dir_code = serv_data.pop("direction_code")
            serv_data["direction_id"] = directions_created[dir_code].id
            service = Service(**serv_data)
            session.add(service)
            services_count += 1
            print(f"   ✅ Service {serv_data['code']} créé")
    
    session.commit()
    
    print("\n" + "=" * 70)
    print("✅ INITIALISATION TERMINÉE AVEC SUCCÈS")
    print("=" * 70)
    print(f"   📊 {len(programmes_created)} programmes")
    print(f"   🏢 {len(directions_created)} directions")
    print(f"   🏪 {services_count} services créés")
    
except Exception as e:
    session.rollback()
    print(f"\n❌ ERREUR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    session.close()

