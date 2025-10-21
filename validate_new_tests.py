#!/usr/bin/env python3
"""
Script de validation des nouveaux tests
Usage: python validate_new_tests.py
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Exécute une commande et affiche le résultat"""
    print(f"\n🧪 {description}")
    print(f"Commande: {cmd}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Succès")
            if result.stdout:
                print(result.stdout)
        else:
            print("❌ Échec")
            if result.stderr:
                print(result.stderr)
            if result.stdout:
                print(result.stdout)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def main():
    """Fonction principale"""
    print("🚀 Validation des Nouveaux Tests MPPEEP")
    print("=" * 50)
    
    # Vérifier que nous sommes dans le bon répertoire
    if not os.path.exists("tests"):
        print("❌ Erreur: Répertoire 'tests' non trouvé")
        print("Assurez-vous d'être dans le répertoire racine du projet")
        sys.exit(1)
    
    # Tests à valider
    tests_to_run = [
        # Tests critiques
        ("pytest tests/integration/test_api_endpoints.py -m critical", "Tests API Endpoints Critiques"),
        ("pytest tests/unit/test_validation.py -m critical", "Tests Validation Critiques"),
        ("pytest tests/integration/test_docker_postgres.py -m critical", "Tests Docker PostgreSQL Critiques"),
        ("pytest tests/unit/test_services.py -m critical", "Tests Services Critiques"),
        ("pytest tests/unit/test_security_advanced.py -m critical", "Tests Sécurité Critiques"),
        
        # Tests par catégorie
        ("pytest tests/unit/test_validation.py -m unit", "Tests Unitaires Validation"),
        ("pytest tests/integration/test_api_endpoints.py -m integration", "Tests Intégration API"),
        ("pytest tests/unit/test_security_advanced.py -m security", "Tests Sécurité"),
        ("pytest tests/integration/test_docker_postgres.py -m docker", "Tests Docker"),
        
        # Tests complets
        ("pytest tests/ -m critical", "Tous les Tests Critiques"),
        ("pytest tests/ --cov=app --cov-report=term-missing", "Tests avec Couverture"),
    ]
    
    # Exécuter les tests
    success_count = 0
    total_count = len(tests_to_run)
    
    for cmd, description in tests_to_run:
        if run_command(cmd, description):
            success_count += 1
    
    # Résumé
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ")
    print("=" * 50)
    print(f"Tests réussis: {success_count}/{total_count}")
    print(f"Taux de réussite: {success_count/total_count*100:.1f}%")
    
    if success_count == total_count:
        print("🎉 Tous les tests sont validés !")
        print("✅ Vos nouveaux tests sont prêts pour la production")
    elif success_count >= total_count * 0.8:
        print("⚠️  La plupart des tests passent")
        print("🔧 Quelques ajustements peuvent être nécessaires")
    else:
        print("❌ Plusieurs tests échouent")
        print("🔧 Vérifiez la configuration et les dépendances")
    
    # Recommandations
    print("\n💡 RECOMMANDATIONS")
    print("-" * 30)
    print("1. Exécutez régulièrement: pytest -m critical")
    print("2. Avant commit: pytest --cov=app --cov-fail-under=80")
    print("3. Tests Docker: pytest -m docker")
    print("4. Tests Sécurité: pytest -m security")
    
    return success_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
