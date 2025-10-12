#!/usr/bin/env python3
"""
Script pour réinitialiser les workflow steps RH
Supprime les anciennes étapes et recrée les nouvelles avec N2 obligatoire
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import select
from app.db.session import get_session
from app.models.rh import WorkflowStep
from app.core.rh_workflow_seed import ensure_workflow_steps

print("=" * 60)
print("🔄 Réinitialisation des Workflow Steps RH")
print("=" * 60)

session = next(get_session())

try:
    # Supprimer tous les workflow steps existants
    print("\n📋 Suppression des anciens workflow steps...")
    old_steps = session.exec(select(WorkflowStep)).all()
    print(f"   → {len(old_steps)} étapes trouvées")
    
    for step in old_steps:
        session.delete(step)
    
    session.commit()
    print("   ✅ Anciens workflow steps supprimés")
    
    # Recréer les workflow steps avec le nouveau circuit (incluant N2)
    print("\n🔨 Création des nouveaux workflow steps (avec N2)...")
    ensure_workflow_steps(session)
    print("   ✅ Nouveaux workflow steps créés")
    
    # Afficher le nouveau circuit
    print("\n📊 Nouveau circuit configuré :")
    print("   DRAFT → SUBMITTED → VALIDATION_N1 → VALIDATION_N2 → VALIDATION_DRH → SIGNATURE_DG → SIGNATURE_DAF/ARCHIVED")
    
    # Compter les nouvelles étapes
    new_steps = session.exec(select(WorkflowStep)).all()
    print(f"\n   📈 Total: {len(new_steps)} étapes de workflow créées")
    
    print("\n" + "=" * 60)
    print("✅ RÉINITIALISATION TERMINÉE AVEC SUCCÈS")
    print("=" * 60)
    print("\n💡 N2 (Chef de direction) est maintenant une étape obligatoire du circuit.")
    
except Exception as e:
    session.rollback()
    print(f"\n❌ ERREUR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    session.close()

