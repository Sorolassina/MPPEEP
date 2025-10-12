#!/usr/bin/env python3
"""
Script pour créer les tables du module personnel
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import SQLModel
from app.db.session import engine
from app.models.personnel import (
    Programme, Direction, Service, GradeComplet, AgentComplet,
    DocumentAgent, HistoriqueCarriere, EvaluationAgent
)

print("=" * 70)
print("📊 Création des tables du module Personnel")
print("=" * 70)

try:
    # Créer toutes les tables
    SQLModel.metadata.create_all(engine)
    
    print("\n✅ Tables créées avec succès :")
    print("   - programme")
    print("   - direction")
    print("   - service")
    print("   - grade_complet")
    print("   - agent_complet")
    print("   - document_agent")
    print("   - historique_carriere")
    print("   - evaluation_agent")
    
    print("\n" + "=" * 70)
    print("✅ MIGRATION TERMINÉE AVEC SUCCÈS")
    print("=" * 70)
    print("\n💡 Prochaines étapes :")
    print("   1. Exécuter : python scripts/init_grades_fonction_publique.py")
    print("   2. Ajouter vos programmes, directions et services")
    print("   3. Créer vos premiers agents")
    
except Exception as e:
    print(f"\n❌ ERREUR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

