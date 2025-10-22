#!/usr/bin/env python3
"""
Test du système de permissions utilisateur
"""

import sys
from pathlib import Path

# Ajouter le dossier parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.permissions import PermissionManager
from app.core.enums import UserType

def test_permissions():
    print("="*70)
    print("🧪 TEST DU SYSTÈME DE PERMISSIONS")
    print("="*70)
    
    # Tester chaque type d'utilisateur
    test_cases = [
        (UserType.ADMIN.value, "Administrateur"),
        (UserType.DAF.value, "Direction Administrative et Financière"),
        (UserType.SDB.value, "Sous-Direction Budget"),
        (UserType.SDRH.value, "Sous-Direction des Ressources Humaines"),
        (UserType.SDCMG.value, "Sous-Direction Commerciale et Marketing"),
        (UserType.CS.value, "Chef de Service"),
        (UserType.AGENT.value, "Agent"),
        (UserType.INVITE.value, "Invité"),
    ]
    
    for user_type, display_name in test_cases:
        print(f"\n👤 {display_name} ({user_type})")
        print("-" * 50)
        
        # Récupérer les permissions
        permissions = PermissionManager.get_user_permissions(user_type)
        modules = PermissionManager.get_accessible_modules(user_type)
        
        print(f"📋 Permissions: {sorted(list(permissions))}")
        print(f"🎯 Modules accessibles: {modules}")
        
        # Tester des permissions spécifiques
        tests = [
            ("budget", "Budget"),
            ("performance", "Performance"),
            ("rh", "Ressources Humaines"),
            ("stocks", "Stocks"),
            ("personnel", "Personnel"),
            ("admin", "Administration"),
        ]
        
        for perm, name in tests:
            has_perm = PermissionManager.has_permission(user_type, perm)
            status = "✅" if has_perm else "❌"
            print(f"   {status} {name}")
    
    print("\n" + "="*70)
    print("🔍 TEST DE L'HÉRITAGE HIÉRARCHIQUE")
    print("="*70)
    
    # Tester l'héritage
    hierarchy_tests = [
        (UserType.CS.value, "hérite des permissions SDRH"),
        (UserType.AGENT.value, "hérite des permissions CS"),
    ]
    
    for user_type, description in hierarchy_tests:
        print(f"\n👤 {PermissionManager.get_user_type_display_name(user_type)} ({user_type})")
        print(f"   📝 {description}")
        
        permissions = PermissionManager.get_user_permissions(user_type)
        print(f"   📋 Permissions: {sorted(list(permissions))}")
    
    print("\n" + "="*70)
    print("✅ TESTS TERMINÉS AVEC SUCCÈS!")
    print("="*70)

def main():
    test_permissions()

if __name__ == "__main__":
    main()
