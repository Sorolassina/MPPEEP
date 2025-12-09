"""
Script de test pour la fonction generate_sigle_from_ministere
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.rapport_annuel_performance_generator_modular import RAPStylingManager

# Test avec le nom complet du ministère
test_cases = [
    "MINISTERE DU PATRIMOINE, DU PORTEFEUILLE DE L'ÉTAT ET DES ENTREPRISES PUBLIQUES",
    "Ministère du Patrimoine, du Portefeuille de l'État et des Entreprises Publiques",
    "MINISTERE DU PATRIMOINE DU PORTEFEUILLE DE L'ETAT ET DES ENTREPRISES PUBLIQUES",
]

print("=" * 80)
print("TEST DE GÉNÉRATION DE SIGLE")
print("=" * 80)

for i, test_input in enumerate(test_cases, 1):
    result = RAPStylingManager.generate_sigle_from_ministere(test_input)
    expected = "MPPEEP"
    match = "✓" if result == expected else "✗"
    
    print(f"\nTest {i}:")
    print(f"  Input:    {test_input}")
    print(f"  Output:   {result}")
    print(f"  Expected: {expected}")
    print(f"  Status:   {match} {'CORRECT' if result == expected else 'INCORRECT'}")

print("\n" + "=" * 80)

