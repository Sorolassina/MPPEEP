#!/usr/bin/env python3
"""
Test de charge simple pour vérifier les connexions simultanées
Usage: python test_concurrent_users.py
"""

import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor
import requests

# Configuration
BASE_URL = "http://localhost:9000/mppeep"
TEST_USERS = 20  # Nombre d'utilisateurs simultanés à tester
TEST_DURATION = 30  # Durée du test en secondes

def test_login_request(user_id: int):
    """Simule une connexion utilisateur"""
    try:
        start_time = time.time()
        
        # Test de la page de login
        response = requests.get(f"{BASE_URL}/api/v1/login", timeout=10)
        
        end_time = time.time()
        
        return {
            "user_id": user_id,
            "status_code": response.status_code,
            "response_time": end_time - start_time,
            "success": response.status_code == 200
        }
    except Exception as e:
        return {
            "user_id": user_id,
            "status_code": 0,
            "response_time": 0,
            "success": False,
            "error": str(e)
        }

def test_health_endpoint(user_id: int):
    """Test l'endpoint de santé"""
    try:
        start_time = time.time()
        
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=10)
        
        end_time = time.time()
        
        return {
            "user_id": user_id,
            "status_code": response.status_code,
            "response_time": end_time - start_time,
            "success": response.status_code == 200
        }
    except Exception as e:
        return {
            "user_id": user_id,
            "status_code": 0,
            "response_time": 0,
            "success": False,
            "error": str(e)
        }

def run_concurrent_test():
    """Lance le test de charge"""
    print(f"🧪 Test de charge : {TEST_USERS} utilisateurs simultanés")
    print(f"⏱️  Durée : {TEST_DURATION} secondes")
    print(f"🌐 URL : {BASE_URL}")
    print("-" * 50)
    
    start_time = time.time()
    results = []
    
    # Test 1: Connexions simultanées à la page de login
    print("📋 Test 1: Page de login simultanée")
    with ThreadPoolExecutor(max_workers=TEST_USERS) as executor:
        futures = [executor.submit(test_login_request, i) for i in range(TEST_USERS)]
        login_results = [future.result() for future in futures]
    
    # Test 2: Endpoints de santé simultanés
    print("🏥 Test 2: Endpoints de santé simultanés")
    with ThreadPoolExecutor(max_workers=TEST_USERS) as executor:
        futures = [executor.submit(test_health_endpoint, i) for i in range(TEST_USERS)]
        health_results = [future.result() for future in futures]
    
    end_time = time.time()
    
    # Analyse des résultats
    print("\n📊 RÉSULTATS")
    print("=" * 50)
    
    # Login results
    login_success = sum(1 for r in login_results if r["success"])
    login_avg_time = sum(r["response_time"] for r in login_results) / len(login_results)
    
    print(f"🔐 Page de login :")
    print(f"   ✅ Succès : {login_success}/{TEST_USERS} ({login_success/TEST_USERS*100:.1f}%)")
    print(f"   ⏱️  Temps moyen : {login_avg_time:.3f}s")
    
    # Health results
    health_success = sum(1 for r in health_results if r["success"])
    health_avg_time = sum(r["response_time"] for r in health_results) / len(health_results)
    
    print(f"🏥 Endpoint santé :")
    print(f"   ✅ Succès : {health_success}/{TEST_USERS} ({health_success/TEST_USERS*100:.1f}%)")
    print(f"   ⏱️  Temps moyen : {health_avg_time:.3f}s")
    
    # Temps total
    total_time = end_time - start_time
    print(f"⏱️  Temps total : {total_time:.3f}s")
    
    # Recommandations
    print("\n💡 RECOMMANDATIONS")
    print("=" * 50)
    
    if login_success == TEST_USERS and health_success == TEST_USERS:
        print("✅ EXCELLENT : Toutes les connexions ont réussi")
        print("✅ Votre application peut gérer plusieurs utilisateurs simultanés")
    elif login_success >= TEST_USERS * 0.9:
        print("✅ BON : 90%+ des connexions ont réussi")
        print("✅ Votre application gère bien les connexions simultanées")
    elif login_success >= TEST_USERS * 0.7:
        print("⚠️  MOYEN : 70%+ des connexions ont réussi")
        print("⚠️  Considérez optimiser le pool de connexions")
    else:
        print("❌ PROBLÈME : Moins de 70% des connexions ont réussi")
        print("❌ Optimisation nécessaire pour les connexions simultanées")
    
    # Détails des erreurs
    errors = [r for r in login_results + health_results if not r["success"]]
    if errors:
        print(f"\n❌ Erreurs détectées : {len(errors)}")
        for error in errors[:5]:  # Afficher les 5 premières erreurs
            print(f"   - User {error['user_id']}: {error.get('error', 'Unknown error')}")

if __name__ == "__main__":
    run_concurrent_test()
