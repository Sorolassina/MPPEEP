#!/usr/bin/env python3
"""
Script de test rapide pour vérifier que tous les imports RH fonctionnent
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

print("🔍 Test des imports du système RH")
print("=" * 60)

try:
    print("1️⃣  Test import enums...")
    from app.core.enums import RequestType, WorkflowState
    print(f"   ✅ RequestType : {[t.value for t in RequestType]}")
    print(f"   ✅ WorkflowState : {[s.value for s in WorkflowState]}")
    
    print("\n2️⃣  Test import models...")
    from app.models.rh import (
        Grade, ServiceDept, Agent, HRRequest, 
        WorkflowStep, WorkflowHistory, HRRequestBase
    )
    print("   ✅ Tous les modèles importés correctement")
    
    print("\n3️⃣  Test import services...")
    from app.services.rh import RHService
    print("   ✅ RHService importé correctement")
    
    print("\n4️⃣  Test import workflow seed...")
    from app.core.logique_metier.rh_workflow import ensure_workflow_steps
    print("   ✅ ensure_workflow_steps importé correctement")
    
    print("\n5️⃣  Test import endpoints...")
    from app.api.v1.endpoints import rh
    print("   ✅ Endpoints RH importés correctement")
    
    print("\n6️⃣  Vérification des attributs du router...")
    print(f"   ✅ Nombre de routes : {len(rh.router.routes)}")
    
    # Lister toutes les routes
    print("\n📋 Routes RH disponibles :")
    for route in rh.router.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = ', '.join(route.methods)
            print(f"   • {methods:10} {route.path}")
    
    print("\n" + "=" * 60)
    print("✅ TOUS LES TESTS RÉUSSIS !")
    print("=" * 60)
    print("\n💡 Le système RH est prêt à l'emploi.")
    print("   Vous pouvez démarrer l'application avec :")
    print("   → uvicorn app.main:app --reload")
    
except ImportError as e:
    print("\n" + "=" * 60)
    print(f"❌ ERREUR D'IMPORT : {e}")
    print("=" * 60)
    import traceback
    traceback.print_exc()
    sys.exit(1)
    
except Exception as e:
    print("\n" + "=" * 60)
    print(f"❌ ERREUR : {e}")
    print("=" * 60)
    import traceback
    traceback.print_exc()
    sys.exit(1)

