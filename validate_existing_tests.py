#!/usr/bin/env python3
"""
Script de validation des tests pour les fonctionnalités existantes
"""

import subprocess
import sys
from pathlib import Path


def run_test_command(command: str, description: str) -> bool:
    """Exécute une commande de test et retourne True si succès"""
    print(f"\n🧪 {description}")
    print(f"Commande: {command}")
    print("-" * 50)
    
    try:
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("✅ Succès")
            return True
        else:
            print("❌ Échec")
            print(f"Erreur: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Timeout")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def main():
    """Fonction principale"""
    print("🚀 Validation des Tests - Fonctionnalités Existantes")
    print("=" * 60)
    
    # Changer vers le répertoire du projet
    project_dir = Path(__file__).parent
    print(f"📁 Répertoire: {project_dir}")
    
    # Tests pour les fonctionnalités existantes
    test_commands = [
        # Tests des endpoints existants
        ("pytest tests/integration/test_existing_endpoints.py -v", "Tests Endpoints Existants"),
        ("pytest tests/integration/test_existing_endpoints.py -m critical", "Tests Endpoints Critiques"),
        
        # Tests de validation existants
        ("pytest tests/unit/test_existing_validation.py -v", "Tests Validation Existants"),
        ("pytest tests/unit/test_existing_validation.py -m critical", "Tests Validation Critiques"),
        
        # Tests des services existants
        ("pytest tests/unit/test_existing_services.py -v", "Tests Services Existants"),
        ("pytest tests/unit/test_existing_services.py -m critical", "Tests Services Critiques"),
        
        # Tests de sécurité existants
        ("pytest tests/unit/test_security_advanced.py -v", "Tests Sécurité Avancés"),
        ("pytest tests/unit/test_security_advanced.py -m critical", "Tests Sécurité Critiques"),
        
        # Tests Docker PostgreSQL
        ("pytest tests/integration/test_docker_postgres.py -v", "Tests Docker PostgreSQL"),
        ("pytest tests/integration/test_docker_postgres.py -m critical", "Tests Docker Critiques"),
        
        # Tests par marqueurs
        ("pytest -m critical -v", "Tous les Tests Critiques"),
        ("pytest -m unit -v", "Tous les Tests Unitaires"),
        ("pytest -m integration -v", "Tous les Tests d'Intégration"),
        ("pytest -m security -v", "Tous les Tests de Sécurité"),
    ]
    
    success_count = 0
    total_count = len(test_commands)
    
    for command, description in test_commands:
        if run_test_command(command, description):
            success_count += 1
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ")
    print("=" * 60)
    print(f"✅ Tests réussis: {success_count}/{total_count}")
    print(f"❌ Tests échoués: {total_count - success_count}/{total_count}")
    
    success_rate = (success_count / total_count) * 100
    print(f"📈 Taux de réussite: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("🎉 Excellent! La plupart des tests passent!")
    elif success_rate >= 60:
        print("👍 Bien! Plusieurs tests passent.")
    else:
        print("⚠️  Attention! Beaucoup de tests échouent.")
    
    # Tests spécifiques recommandés
    print("\n🔍 TESTS SPÉCIFIQUES RECOMMANDÉS")
    print("-" * 40)
    
    specific_tests = [
        ("pytest tests/integration/test_existing_endpoints.py::test_health_endpoint -v", "Test Health Check"),
        ("pytest tests/integration/test_existing_endpoints.py::test_ping_endpoint -v", "Test Ping"),
        ("pytest tests/unit/test_existing_validation.py::test_user_create_validation -v", "Test Validation User"),
        ("pytest tests/unit/test_existing_services.py::test_user_service_get_by_email -v", "Test UserService"),
    ]
    
    for command, description in specific_tests:
        print(f"\n🎯 {description}")
        run_test_command(command, description)
    
    print("\n✨ Validation terminée!")
    return success_count == total_count


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
