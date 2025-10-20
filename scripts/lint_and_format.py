#!/usr/bin/env python3
"""
Script pour linter et formater le code avec Ruff
"""
import subprocess
import sys
from pathlib import Path

# Couleurs pour le terminal
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def run_command(cmd, description):
    """Exécute une commande et affiche le résultat"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{description}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    result = subprocess.run(cmd, shell=True, capture_output=False, text=True)
    
    if result.returncode == 0:
        print(f"\n{GREEN}✅ {description} - Succès{RESET}")
        return True
    else:
        print(f"\n{RED}❌ {description} - Erreur{RESET}")
        return False

def main():
    """Fonction principale"""
    print(f"\n{BLUE}🧹 Nettoyage et Formatage du Code MPPEEP Dashboard{RESET}\n")
    
    # Vérifier que ruff est installé
    try:
        subprocess.run(["ruff", "--version"], check=True, capture_output=True)
    except FileNotFoundError:
        print(f"{RED}❌ Ruff n'est pas installé{RESET}")
        print(f"{YELLOW}Installation : pip install ruff{RESET}")
        sys.exit(1)
    
    results = []
    
    # 1. Formater le code (comme black)
    results.append(run_command(
        "ruff format app/ tests/",
        "1️⃣ Formatage du code (style black)"
    ))
    
    # 2. Trier les imports
    results.append(run_command(
        "ruff check --select I --fix app/ tests/",
        "2️⃣ Tri des imports (style isort)"
    ))
    
    # 3. Corrections automatiques
    results.append(run_command(
        "ruff check --fix app/ tests/",
        "3️⃣ Corrections automatiques"
    ))
    
    # 4. Vérification finale
    results.append(run_command(
        "ruff check app/ tests/",
        "4️⃣ Vérification finale (sans fix)"
    ))
    
    # Résumé
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}📊 RÉSUMÉ{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Réussis : {passed}/{total}")
    print(f"❌ Échecs  : {total - passed}/{total}")
    
    if all(results):
        print(f"\n{GREEN}🎉 Code nettoyé avec succès !{RESET}\n")
        sys.exit(0)
    else:
        print(f"\n{YELLOW}⚠️ Certaines vérifications ont échoué{RESET}")
        print(f"{YELLOW}Consultez les messages ci-dessus pour corriger{RESET}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()

