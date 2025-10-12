#!/usr/bin/env python3
"""
Script pour initialiser les grades de la fonction publique sénégalaise
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import select
from app.db.session import get_session
from app.models.personnel import GradeComplet
from app.core.enums import GradeCategory

print("=" * 70)
print("📋 Initialisation des grades de la fonction publique")
print("=" * 70)

session = next(get_session())

# Grades de la fonction publique sénégalaise
grades_data = [
    # CATÉGORIE A - Cadres supérieurs
    {"code": "A4", "libelle": "Administrateur civil principal", "categorie": GradeCategory.A, "indice_min": 1200, "indice_max": 1400},
    {"code": "A3", "libelle": "Administrateur civil", "categorie": GradeCategory.A, "indice_min": 1000, "indice_max": 1199},
    {"code": "A2", "libelle": "Attaché d'administration principal", "categorie": GradeCategory.A, "indice_min": 800, "indice_max": 999},
    {"code": "A1", "libelle": "Attaché d'administration", "categorie": GradeCategory.A, "indice_min": 600, "indice_max": 799},
    
    # CATÉGORIE B - Cadres moyens
    {"code": "B4", "libelle": "Secrétaire d'administration principal", "categorie": GradeCategory.B, "indice_min": 550, "indice_max": 650},
    {"code": "B3", "libelle": "Secrétaire d'administration", "categorie": GradeCategory.B, "indice_min": 480, "indice_max": 549},
    {"code": "B2", "libelle": "Contrôleur principal", "categorie": GradeCategory.B, "indice_min": 420, "indice_max": 479},
    {"code": "B1", "libelle": "Contrôleur", "categorie": GradeCategory.B, "indice_min": 360, "indice_max": 419},
    
    # CATÉGORIE C - Agents d'exécution
    {"code": "C4", "libelle": "Agent administratif principal", "categorie": GradeCategory.C, "indice_min": 330, "indice_max": 380},
    {"code": "C3", "libelle": "Agent administratif", "categorie": GradeCategory.C, "indice_min": 290, "indice_max": 329},
    {"code": "C2", "libelle": "Commis principal", "categorie": GradeCategory.C, "indice_min": 250, "indice_max": 289},
    {"code": "C1", "libelle": "Commis", "categorie": GradeCategory.C, "indice_min": 210, "indice_max": 249},
    
    # CATÉGORIE D - Personnel de soutien
    {"code": "D4", "libelle": "Agent de bureau principal", "categorie": GradeCategory.D, "indice_min": 190, "indice_max": 220},
    {"code": "D3", "libelle": "Agent de bureau", "categorie": GradeCategory.D, "indice_min": 170, "indice_max": 189},
    {"code": "D2", "libelle": "Huissier principal", "categorie": GradeCategory.D, "indice_min": 150, "indice_max": 169},
    {"code": "D1", "libelle": "Huissier", "categorie": GradeCategory.D, "indice_min": 130, "indice_max": 149},
]

try:
    created_count = 0
    existing_count = 0
    
    for grade_data in grades_data:
        # Vérifier si le grade existe déjà
        existing = session.exec(
            select(GradeComplet).where(GradeComplet.code == grade_data["code"])
        ).first()
        
        if existing:
            print(f"   ⏭️  Grade {grade_data['code']} ({grade_data['libelle']}) existe déjà")
            existing_count += 1
        else:
            grade = GradeComplet(**grade_data)
            session.add(grade)
            print(f"   ✅ Grade {grade_data['code']} ({grade_data['libelle']}) créé")
            created_count += 1
    
    session.commit()
    
    print("\n" + "=" * 70)
    print(f"✅ INITIALISATION TERMINÉE")
    print("=" * 70)
    print(f"   📊 {created_count} grades créés")
    print(f"   📋 {existing_count} grades existants")
    print(f"   🎯 Total: {len(grades_data)} grades")
    
except Exception as e:
    session.rollback()
    print(f"\n❌ ERREUR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    session.close()

