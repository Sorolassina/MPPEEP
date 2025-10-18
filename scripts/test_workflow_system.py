#!/usr/bin/env python3
"""
Script de test du système de workflows
Vérifie que tous les composants sont correctement installés
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test des imports"""
    print("🔍 Test des imports...")
    try:
        from app.services.hierarchy_service import HierarchyService
        print("  ✅ HierarchyService")
        
        from app.services.workflow_config_service import WorkflowConfigService
        print("  ✅ WorkflowConfigService")
        
        from app.models.workflow_config import (
            WorkflowTemplate,
            WorkflowTemplateStep,
            RequestTypeCustom,
            CustomRole
        )
        print("  ✅ Modèles workflow_config")
        
        from app.api.v1.endpoints.workflow_admin import router
        print("  ✅ API workflow_admin")
        
        return True
    except ImportError as e:
        print(f"  ❌ Erreur d'import: {e}")
        return False

def test_hierarchy_service():
    """Test du service de hiérarchie"""
    print("\n🔍 Test du HierarchyService...")
    try:
        from app.services.hierarchy_service import HierarchyService
        from app.db.session import get_session
        from app.models.personnel import AgentComplet
        
        with next(get_session()) as session:
            # Récupérer le premier agent pour test
            agent = session.query(AgentComplet).first()
            
            if agent:
                print(f"  ℹ️  Test avec l'agent: {agent.nom} {agent.prenom}")
                
                # Test de get_hierarchy
                hierarchy = HierarchyService.get_hierarchy(session, agent.id)
                print(f"  ✅ get_hierarchy() - Position: {hierarchy.get('position', 'N/A')}")
                
                # Test de get_daf
                daf = HierarchyService._get_daf(session)
                print(f"  ✅ _get_daf() - DAF: {daf.nom if daf else 'Non trouvé'}")
                
                # Test de get_rh
                rh = HierarchyService._get_rh(session)
                print(f"  ✅ _get_rh() - RH: {rh.nom if rh else 'Non trouvé'}")
                
                return True
            else:
                print("  ⚠️  Aucun agent en base pour tester")
                return True
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def test_workflow_config_service():
    """Test du service de configuration"""
    print("\n🔍 Test du WorkflowConfigService...")
    try:
        from app.services.workflow_config_service import WorkflowConfigService
        from app.db.session import get_session
        
        with next(get_session()) as session:
            # Test de get_active_request_types
            request_types = WorkflowConfigService.get_active_request_types(session)
            print(f"  ✅ get_active_request_types() - {len(request_types)} types trouvés")
            
            # Test de get_workflow_preview (si templates existent)
            from app.models.workflow_config import WorkflowTemplate
            template = session.query(WorkflowTemplate).first()
            
            if template:
                preview = WorkflowConfigService.get_workflow_preview(session, template.id)
                print(f"  ✅ get_workflow_preview() - Template: {preview.get('template', {}).get('nom', 'N/A')}")
            else:
                print("  ℹ️  Aucun template pour tester la prévisualisation")
            
            return True
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def test_rh_service_integration():
    """Test de l'intégration avec RHService"""
    print("\n🔍 Test de l'intégration RHService...")
    try:
        from app.services.rh import RHService
        
        # Vérifier que la méthode transition a le paramètre skip_hierarchy_check
        import inspect
        sig = inspect.signature(RHService.transition)
        params = list(sig.parameters.keys())
        
        if 'skip_hierarchy_check' in params:
            print("  ✅ RHService.transition() - Paramètre skip_hierarchy_check présent")
            return True
        else:
            print("  ❌ RHService.transition() - Paramètre skip_hierarchy_check manquant")
            return False
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def test_routes_integration():
    """Test de l'intégration des routes"""
    print("\n🔍 Test de l'intégration des routes...")
    try:
        from app.api.v1.router import api_router
        
        # Vérifier que workflow_admin est inclus
        routes = [route.path for route in api_router.routes]
        workflow_routes = [r for r in routes if 'workflow-config' in r]
        
        if workflow_routes:
            print(f"  ✅ Routes workflow intégrées - {len(workflow_routes)} routes trouvées")
            for route in workflow_routes[:3]:  # Afficher les 3 premières
                print(f"     - {route}")
            return True
        else:
            print("  ❌ Routes workflow non trouvées")
            return False
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def main():
    """Fonction principale"""
    print("="*60)
    print("🧪 TEST DU SYSTÈME DE WORKFLOWS")
    print("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("HierarchyService", test_hierarchy_service),
        ("WorkflowConfigService", test_workflow_config_service),
        ("Intégration RHService", test_rh_service_integration),
        ("Routes", test_routes_integration),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Erreur critique dans {name}: {e}")
            results.append((name, False))
    
    print("\n" + "="*60)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for _, r in results if r)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nRésultat: {passed}/{total} tests passés")
    
    if passed == total:
        print("\n🎉 Tous les tests sont passés ! Le système est prêt.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) échoué(s). Vérifiez l'installation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

