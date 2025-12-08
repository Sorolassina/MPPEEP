# 📦 Création d'un Exécutable Windows - Guide Complet (MPPEEP Dashboard)

## 🎯 Description

Ce guide explique comment créer un exécutable Windows (`.exe`) de l'interface graphique MPPEEP Dashboard avec une icône personnalisée et un raccourci sur le bureau. Tous les fichiers de build sont regroupés dans le dossier `build_exe/` pour faciliter l'export d'un projet à un autre.

## 📁 Structure des Fichiers de Build

Tous les fichiers générés par PyInstaller sont regroupés dans le dossier `build_exe/` **à la racine du projet** (hors de `config_tkinter`) :

```
MPPEEP/                            ← Racine du projet
├── build_exe/                     ← Dossier de build (à la racine)
│   ├── dist/
│   │   └── MPPEEPDashboard.exe   ← L'exécutable final (à distribuer)
│   ├── build/                    ← Fichiers temporaires (peut être supprimé)
│   │   └── MPPEEPDashboard/
│   │       └── (fichiers temporaires)
│   └── MPPEEPDashboard.spec      ← Fichier de configuration PyInstaller
├── config_tkinter/
│   ├── make_gui.py               ← Interface graphique
│   ├── build_exe.py              ← Script de création
│   └── ... (autres fichiers)
└── ... (autres fichiers du projet)
```

**Avantages :**
- ✅ Tous les fichiers de build sont au même endroit à la racine
- ✅ Facile à exporter vers un autre projet (copier `build_exe/`)
- ✅ Facile à nettoyer (supprimer `build_exe/`)
- ✅ Séparé des fichiers de configuration de l'interface

## 🚀 Création de l'Exécutable

### Option 1 : Script Batch (Recommandé)

Double-cliquez sur :
```
creer_executable.bat
```

Le script va :
1. ✅ Détecter automatiquement Python (`uv`, `python`, `python3`, ou `py`)
2. ✅ Vérifier si PyInstaller est installé (l'installer si nécessaire)
3. ✅ Conserver les fichiers de build précédents (pas de suppression automatique)
4. ✅ Créer l'exécutable `MPPEEPDashboard.exe` dans `build_exe/dist/` (à la racine du projet)
5. ✅ Proposer de créer un raccourci sur le bureau

### Option 2 : Via uv

Si vous utilisez `uv` :
```
creer_executable_uv.bat
```

### Option 3 : Manuellement

```powershell
# Installer PyInstaller
pip install pyinstaller
# ou avec uv
uv pip install pyinstaller

# Créer l'exécutable
python build_exe.py
```

## 📋 Prérequis

- **Python** installé et dans le PATH (ou `uv` installé)
- **PyInstaller** (installé automatiquement par le script)
- **Tkinter** (généralement inclus avec Python)

### Détection Automatique de Python

Les scripts détectent automatiquement Python dans cet ordre :
1. `uv run python` (si `uv` est installé - recommandé pour ce projet)
2. `python`
3. `python3`
4. `py` (Python Launcher Windows)

## 🎨 Icône

L'exécutable utilisera automatiquement :
1. `icon.ico` dans `config_tkinter/` (si présent)
2. `icon.ico` à la racine du projet (si présent)
3. `app/static/favicon.ico` (icône du projet)
4. Icône par défaut de Windows (si aucune icône trouvée)

### Ajouter une Icône Personnalisée

1. Créez ou téléchargez un fichier `.ico`
2. Placez-le à la racine du projet sous le nom `icon.ico`
3. Relancez `creer_executable.bat`

**Conseil :** Utilisez un outil comme [ICO Convert](https://icoconvert.com/) pour convertir une image PNG en ICO. Les tailles recommandées sont : 16x16, 32x32, 48x48, 256x256.

## 🖥️ Raccourci sur le Bureau

### Création Automatique

Le script `creer_executable.bat` propose automatiquement de créer un raccourci après la création de l'exécutable.

### Création Manuelle

Double-cliquez sur :
```
creer_raccourci.bat
```

Le raccourci sera créé sur votre bureau avec :
- ✅ Nom : `MPPEEP Dashboard`
- ✅ Icône personnalisée (si disponible)
- ✅ Description : "MPPEEP Dashboard - Interface de configuration"
- ✅ Répertoire de travail : `build_exe/dist/`

## ⚙️ Options PyInstaller

Le script `build_exe.py` utilise les options suivantes :

- `--onefile` : Crée un seul fichier exécutable (plus facile à distribuer)
- `--windowed` : Pas de console (interface graphique uniquement)
- `--clean` : Nettoie le cache avant de construire
- `--noconfirm` : Ne pas demander de confirmation
- `--distpath=../build_exe/dist` : Dossier de sortie personnalisé (à la racine du projet)
- `--workpath=../build_exe/build` : Dossier de travail personnalisé (à la racine du projet)
- `--specpath=../build_exe` : Dossier pour le fichier `.spec` (à la racine du projet)
- `--icon` : Utilise l'icône spécifiée

## 🔧 Personnalisation

### Modifier le Nom de l'Exécutable

Éditez `build_exe.py` et changez :
```python
'--name=MPPEEPDashboard',  # Changez ici
```

### Ajouter des Fichiers de Données

Si vous devez inclure des fichiers supplémentaires (comme `make.ps1`), ajoutez dans `build_exe.py` :
```python
options.append('--add-data=make.ps1;.')
```

### Changer le Dossier de Build

Modifiez dans `build_exe.py` :
```python
build_dir = Path(__file__).parent.parent / "build_exe"  # À la racine du projet
```

## 🧹 Nettoyage

### Nettoyer les Fichiers Temporaires

Double-cliquez sur :
```
nettoyer_build.bat
```

Ce script supprime **UNIQUEMENT** (à la racine du projet) :
- ✅ `build_exe/build/` (fichiers temporaires)
- ✅ `build_exe/MPPEEPDashboard.spec` (fichier de configuration)

**Sécurité :**
- ✅ Le dossier `build_exe/dist/` (contenant l'exécutable) est préservé
- ✅ Le dossier `config_tkinter/` n'est **JAMAIS** modifié ou supprimé
- ✅ Seul le dossier `build_exe/` à la racine est nettoyé

### Nettoyage Manuel

Supprimez simplement le dossier `build_exe/` à la racine du projet :
```batch
rmdir /s /q build_exe
```

## 🐛 Dépannage

### Erreur : "PyInstaller n'est pas reconnu"

```powershell
pip install pyinstaller
# ou avec uv
uv pip install pyinstaller
```

### Erreur : "Tkinter n'est pas disponible"

Sur Linux, installez :
```bash
sudo apt-get install python3-tk
```

### Erreur : "[WinError 5] Accès refusé"

Cette erreur indique que des fichiers sont verrouillés (souvent par OneDrive).

**Solutions :**

1. **Nettoyer manuellement :**
   ```batch
   nettoyer_build.bat
   ```

2. **Pauser OneDrive temporairement :**
   - Cliquez sur l'icône OneDrive dans la barre des tâches
   - Pausez la synchronisation
   - Relancez `creer_executable.bat`
   - Réactivez OneDrive après

3. **Fermer les programmes :**
   - Fermez tous les programmes qui pourraient utiliser ces fichiers
   - Relancez `creer_executable.bat`

4. **Supprimer manuellement :**
   - Supprimez le dossier `build_exe/` à la racine du projet dans l'explorateur Windows
   - Relancez `creer_executable.bat`

### L'exécutable est trop volumineux

PyInstaller inclut Python et toutes les dépendances. C'est normal pour un exécutable autonome (généralement 50-100 MB).

Pour réduire la taille :
- Utilisez `--exclude-module` pour exclure des modules non utilisés
- Utilisez `--onedir` au lieu de `--onefile` (mais nécessite un dossier complet)

### L'icône ne s'affiche pas

1. Vérifiez que le fichier `.ico` est valide
2. Utilisez un outil pour convertir votre image en ICO (16x16, 32x32, 48x48, 256x256)
3. Vérifiez que le chemin vers l'icône est correct dans `build_exe.py`

### Le raccourci n'est pas créé

1. Vérifiez les permissions d'écriture sur le bureau
2. Exécutez `creer_raccourci.bat` manuellement pour voir les erreurs
3. Vérifiez que l'exécutable existe : `../build_exe/dist/MPPEEPDashboard.exe` (à la racine du projet)

## 📦 Distribution

### Option Simple : Exécutable Seul

Partagez uniquement :
```
build_exe/dist/MPPEEPDashboard.exe  (à la racine du projet)
```

L'utilisateur peut le placer n'importe où et double-cliquer pour lancer.

**Note :** L'exécutable doit être dans le même répertoire que `make.ps1` pour fonctionner correctement, ou `make_gui.py` cherche automatiquement `make.ps1` dans le répertoire parent.

### Option Complète : Package avec Fichiers

Créez un package avec :
```
MPPEEP Dashboard/
├── MPPEEPDashboard.exe   (depuis build_exe/dist/ à la racine du projet)
├── make.ps1              (nécessaire pour exécuter les commandes)
└── README.txt            (instructions d'utilisation)
```

### Export vers un Autre Projet

Pour exporter la configuration de build vers un autre projet :

1. **Copier le dossier de build :**
   ```batch
   xcopy /E /I build_exe C:\NouveauProjet\build_exe
   ```

2. **Copier les fichiers nécessaires :**
   - `config_tkinter/build_exe.py`
   - `config_tkinter/creer_executable.bat`
   - `config_tkinter/creer_raccourci.bat`
   - `config_tkinter/make_gui.py`
   - `icon.ico` (si présent)

3. **Adapter les chemins :**
   - Vérifiez que `make_gui.py` trouve `make.ps1` (cherche dans le répertoire parent)
   - Vérifiez que les chemins d'icônes sont corrects

## 🎯 Utilisation

Une fois l'exécutable créé :

1. Double-cliquez sur `build_exe/dist/MPPEEPDashboard.exe`
2. L'interface graphique s'ouvre
3. Utilisez les onglets pour exécuter les commandes

**Important :** 
- Assurez-vous que `make.ps1` est à la racine du projet (répertoire parent de `config_tkinter`).
- L'exécutable cherche automatiquement `make.ps1` dans plusieurs emplacements.

## 📝 Fichiers du Projet

### Fichiers Principaux

- **`make_gui.py`** : Interface graphique Tkinter
- **`build_exe.py`** : Script de création de l'exécutable
- **`creer_executable.bat`** : Script batch pour créer l'exécutable
- **`creer_executable_uv.bat`** : Version utilisant `uv`
- **`creer_raccourci.bat`** : Script pour créer un raccourci sur le bureau
- **`nettoyer_build.bat`** : Script pour nettoyer les fichiers temporaires
- **`lancer_interface.bat`** : Script pour lancer l'interface
- **`lancer_interface_uv.bat`** : Version utilisant `uv`
- **`lancer_interface.ps1`** : Version PowerShell

### Dossier de Build

- **`build_exe/`** (à la racine du projet) : Tous les fichiers de build
  - **`dist/`** : Exécutable final
  - **`build/`** : Fichiers temporaires (peut être supprimé)
  - **`MPPEEPDashboard.spec`** : Configuration PyInstaller

## 🔄 Mise à Jour de l'Exécutable

Pour mettre à jour l'exécutable après des modifications :

1. Modifiez `make_gui.py` si nécessaire
2. Exécutez `creer_executable.bat`
3. Le nouvel exécutable remplacera l'ancien dans `build_exe/dist/` (à la racine du projet)

**Astuce :** Si vous avez des problèmes, nettoyez d'abord avec `nettoyer_build.bat`.

## 📚 Ressources

- [PyInstaller Documentation](https://pyinstaller.org/)
- [Tkinter Documentation](https://docs.python.org/3/library/tkinter.html)
- [ICO Convert](https://icoconvert.com/) - Convertir des images en ICO

## ✅ Checklist de Création

- [ ] Python ou `uv` installé
- [ ] PyInstaller installé (automatique)
- [ ] Icône personnalisée ajoutée (optionnel)
- [ ] Exécutable créé dans `build_exe/dist/` (à la racine du projet)
- [ ] Raccourci créé sur le bureau (optionnel)
- [ ] Test de l'exécutable effectué
- [ ] Documentation lue

---

**Note :** Ce guide est spécifique à Windows. Pour Linux ou macOS, adaptez les chemins et commandes en conséquence.

