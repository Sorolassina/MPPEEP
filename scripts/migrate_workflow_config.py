#!/usr/bin/env python3
"""
Migration pour créer les tables de configuration des workflows
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import SQLModel
from app.db.session import engine
from app.models.workflow_config import (
    WorkflowTemplate,
    WorkflowTemplateStep,
    RequestTypeCustom,
    CustomRole,
    CustomRoleAssignment,
    WorkflowConfigHistory
)

def create_workflow_tables():
    """Crée les tables de configuration des workflows"""
    print("🔄 Création des tables de configuration des workflows...")
    
    try:
        # Créer toutes les tables définies dans workflow_config
        SQLModel.metadata.create_all(engine, checkfirst=True)
        
        print("✅ Tables créées avec succès:")
        print("   - workflow_template")
        print("   - workflow_template_step")
        print("   - request_type_custom")
        print("   - custom_role")
        print("   - custom_role_assignment")
        print("   - workflow_config_history")
        
    except Exception as e:
        print(f"❌ Erreur lors de la création des tables: {e}")
        raise

if __name__ == "__main__":
    create_workflow_tables()
    print("\n🎉 Migration terminée avec succès!")

