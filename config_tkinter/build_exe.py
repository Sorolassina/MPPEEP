












































































































































































































































































































































































































"""
Script pour créer un exécutable de l'interface graphique
Utilise PyInstaller pour créer un .exe autonome
"""
import PyInstaller.__main__
import sys
from pathlib import Path

# Chemin du script principal
script_path = Path(__file__).parent / "make_gui.py"

# Dossier de build personnalisé (à la racine du projet, hors de config_tkinter)
build_dir = Path(__file__).parent.parent / "build_exe"
dist_dir = build_dir / "dist"
work_dir = build_dir / "build"

# Créer les dossiers si nécessaire
dist_dir.mkdir(parents=True, exist_ok=True)
work_dir.mkdir(parents=True, exist_ok=True)

# Options PyInstaller
options = [
    str(script_path),
    '--name=MPPEEPDashboard',
    '--onefile',  # Un seul fichier exécutable
    '--windowed',  # Pas de console (interface graphique)
    '--clean',  # Nettoyer le cache avant de construire
    '--noconfirm',  # Ne pas demander de confirmation
    f'--distpath={dist_dir}',  # Dossier de sortie
    f'--workpath={work_dir}',  # Dossier de travail
    f'--specpath={build_dir}',  # Dossier pour le fichier .spec
]

# Ajouter une icône si elle existe
# Chercher dans plusieurs emplacements
base_dir = Path(__file__).parent
project_root = base_dir.parent  # Répertoire parent (racine du projet)
icon_paths = [
    base_dir / "icon.ico",  # Dans config_tkinter
    project_root / "icon.ico",  # À la racine du projet
    project_root / "app" / "static" / "images" / "logo.webp",  # Logo principal
    project_root / "app" / "static" / "images" / "logo_default.png",  # Logo par défaut
    project_root / "app" / "static" / "favicon.ico",  # Favicon du projet
]

icon_path = None
for path in icon_paths:
    if path.exists():
        # Si c'est un fichier .ico, utiliser directement
        if path.suffix.lower() == '.ico':
            icon_path = path
            break
        # Si c'est une image (webp, png, jpg), essayer de convertir en .ico
        elif path.suffix.lower() in ['.webp', '.png', '.jpg', '.jpeg']:
            try:
                from PIL import Image
                # Créer un fichier .ico temporaire dans build_exe
                ico_path = build_dir / "temp_icon.ico"
                img = Image.open(path)
                # Créer plusieurs tailles pour un .ico de qualité
                sizes = [(16, 16), (32, 32), (48, 48), (256, 256)]
                img.save(str(ico_path), format='ICO', sizes=sizes)
                icon_path = ico_path
                print(f"✅ Logo converti en .ico: {path} -> {icon_path}")
                break
            except ImportError:
                print(f"⚠️  PIL/Pillow non disponible, impossible de convertir {path} en .ico")
                print(f"   Installez Pillow: pip install pillow")
            except Exception as e:
                print(f"⚠️  Erreur lors de la conversion: {e}")
        else:
            icon_path = path
            break

if icon_path:
    options.append(f'--icon={icon_path}')
    print(f"✅ Icône trouvée: {icon_path}")
else:
    print("⚠️  Aucune icône trouvée. L'exécutable utilisera l'icône par défaut.")
    print("   Pour ajouter une icône, placez un fichier 'icon.ico' dans le répertoire du projet.")
    print("   Ou placez logo.webp ou logo.png dans app/static/images/")

# Ajouter les fichiers de données si nécessaire
# options.append('--add-data=make.ps1;.')

print("="*60)
print("Création de l'exécutable MPPEEPDashboard.exe")
print("="*60)
print()
print("Note: Les fichiers de build précédents sont conservés.")
print("      Utilisez nettoyer_build.bat si vous voulez les supprimer.")
print()

# Vérifier si on est dans OneDrive et avertir
import os
cwd = Path.cwd()
if "OneDrive" in str(cwd):
    print("⚠️  ATTENTION: Le projet est dans OneDrive.")
    print("   Les erreurs 'Accès refusé' peuvent survenir si OneDrive verrouille les fichiers.")
    print("   Si vous rencontrez des erreurs, essayez de:")
    print("   1. Pauser temporairement la synchronisation OneDrive")
    print("   2. Ou déplacer le projet hors de OneDrive")
    print()

print()

# Vérifier que .venv n'est pas verrouillé avant de commencer
venv_path = Path.cwd() / ".venv"
if venv_path.exists() and "OneDrive" in str(Path.cwd()):
    print("🔍 Vérification de l'environnement virtuel...")
    try:
        # Tester l'accès en lecture/écriture sur .venv
        test_file = venv_path / ".test_access"
        try:
            test_file.touch()
            test_file.unlink()
        except (PermissionError, OSError) as e:
            print(f"⚠️  ATTENTION: Accès limité à .venv: {e}")
            print("   OneDrive peut verrouiller les fichiers.")
            print("   Il est fortement recommandé de pauser OneDrive avant de continuer.")
            print()
            response = input("Voulez-vous continuer quand même ? (O/N): ")
            if response.upper() != 'O':
                print("Opération annulée.")
                sys.exit(0)
    except Exception:
        pass  # Ignorer les erreurs de test

print()

try:
    PyInstaller.__main__.run(options)
    print()
    print("="*60)
    print("✅ Exécutable créé avec succès !")
    print("="*60)
    print()
    print(f"📁 Fichier: {dist_dir / 'MPPEEPDashboard.exe'}")
    print()
except Exception as e:
    print()
    print("="*60)
    print("❌ Erreur lors de la création de l'exécutable")
    print("="*60)
    print(f"Erreur: {e}")
    print()
    
    # Détecter les erreurs d'accès refusé
    error_str = str(e).lower()
    error_output = str(e)
    
    # Vérifier si l'erreur vient de uv ou PyInstaller
    is_uv_error = ".venv" in error_output or "site-packages" in error_output
    is_onedrive = "OneDrive" in str(Path.cwd())
    
    if "accès refusé" in error_str or "access denied" in error_str or "winerror 5" in error_str:
        print("🔍 Détection: Erreur d'accès refusé (fichiers verrouillés)")
        print()
        
        if is_uv_error:
            print("⚠️  L'erreur semble provenir de l'environnement virtuel (.venv)")
            print("   Cela peut arriver si uv ou un autre processus modifie .venv")
            print("   pendant que PyInstaller l'analyse.")
            print()
            print("Solutions spécifiques:")
            print("  1. ⭐ PAUSEZ la synchronisation OneDrive (recommandé)")
            print("     - Cliquez sur l'icône OneDrive dans la barre des tâches")
            print("     - Sélectionnez 'Pause la synchronisation' > '2 heures'")
            print("     - Relancez creer_executable.bat")
            print()
            print("  2. Attendez quelques secondes et réessayez")
            print("     (laissez le temps à OneDrive de libérer les fichiers)")
            print()
            print("  3. Fermez tous les programmes qui utilisent .venv")
            print("     (éditeurs de code, terminaux, etc.)")
            print()
        else:
            print("Causes possibles:")
            print("  - Fichiers temporaires verrouillés par OneDrive")
            print("  - Fichiers utilisés par un autre processus")
            print("  - Permissions insuffisantes")
            print()
            print("Solutions:")
            print("  1. Exécutez nettoyer_build.bat pour nettoyer les fichiers temporaires")
            print("  2. Pausez temporairement la synchronisation OneDrive")
            print("  3. Fermez tous les programmes qui utilisent ces fichiers")
            print("  4. Réessayez après quelques secondes")
            print()
        
        if is_onedrive:
            print("💡 Astuce: Pour éviter ces problèmes à l'avenir, considérez")
            print("           de déplacer le projet hors de OneDrive ou d'exclure")
            print("           le dossier .venv de la synchronisation OneDrive.")
            print()
    
    sys.exit(1)


