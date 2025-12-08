# Interface Graphique MPPEEP Dashboard

## 🎯 Description

Interface graphique Tkinter permettant d'exécuter facilement toutes les commandes du script `make.ps1` sans avoir besoin de connaître PowerShell ou la ligne de commande.

## 🚀 Lancement

### Option 1 : Double-clic sur le fichier batch (Recommandé)
```
lancer_interface.bat
```
Le script détecte automatiquement Python via :
- `uv run python` (si uv est installé - recommandé)
- `python`
- `python3`
- `py` (Python Launcher Windows)

### Option 2 : Via uv (si uv est installé)
```
lancer_interface_uv.bat
```

### Option 3 : PowerShell
```powershell
.\lancer_interface.ps1
```

### Option 4 : Python directement
```powershell
python make_gui.py
# ou
uv run python make_gui.py
```

## ⚠️ Si Python n'est pas trouvé

Si vous obtenez l'erreur `'python' n'est pas reconnu` :

1. **Installer Python** : https://www.python.org/downloads/
   - ✅ Cocher "Add Python to PATH" lors de l'installation

2. **Ou utiliser uv** (recommandé pour ce projet) :
   ```powershell
   pip install uv
   ```
   Puis utilisez `lancer_interface_uv.bat`

3. **Ou utiliser le Python Launcher Windows** :
   - Télécharger depuis Microsoft Store
   - Utiliser `py make_gui.py` dans un terminal

## 📋 Fonctionnalités

L'interface est organisée en **8 onglets** :

### 🚀 Démarrage
- **Installation Complète** : Configure l'environnement (demande la version Python)
- **Démarrer** : Lance l'application
- **Arrêter** : Arrête l'application
- **Redémarrer** : Redémarre l'application

### ⚙️ Environnement
- **Installer Dépendances** : Installe les packages avec `uv`
- **Vérifier Environnement** : Vérifie la configuration
- **Infos Environnement** : Affiche les informations système
- **Synchroniser UV** : Synchronise les dépendances
- **Ajouter/Supprimer Package** : Gère les packages (demande le nom)
- **Lister Packages** : Liste les packages installés
- **Mettre à jour** : Met à jour les packages

### 💾 Base de Données
- **Initialiser DB** : Initialise la base de données (avec confirmation)
- **Réinitialiser DB** : Réinitialise la base (avec confirmation)
- **Sauvegarder DB** : Crée une sauvegarde
- **Créer Admin** : Crée un utilisateur administrateur

### 🐳 Docker
Organisé en 3 sections :

**Développement :**
- Démarrer/Arrêter/Redémarrer Dev
- Voir les logs Dev

**Production :**
- Démarrer/Arrêter/Redémarrer Prod
- Rebuild Prod (avec confirmation)
- Voir les logs Prod
- Statut des conteneurs

**Autres :**
- Exporter/Importer Image
- Package Docker
- Nettoyer (avec confirmation)

### 🧪 Tests
- **Tous les Tests** : Lance tous les tests
- **Tests Unitaires** : Tests unitaires uniquement
- **Couverture** : Tests avec couverture de code

### ✨ Qualité
- **Linter** : Vérifie le code
- **Corriger Lint** : Corrige automatiquement
- **Formater** : Formate le code
- **Nettoyer Code** : Nettoyage complet

### 📂 Git
- **Statut** : Affiche le statut Git
- **Log** : Historique des commits
- **Pré-commit** : Prépare un commit
- **Push** : Push vers origin

### 🔧 Maintenance
- **Logs** : Affiche les logs de l'application
- **Nettoyer** : Nettoie les fichiers temporaires
- **Nettoyer Tout** : Nettoyage complet (avec confirmation)

## 🎨 Caractéristiques

- **Interface moderne** : Design épuré et intuitif
- **Sortie en temps réel** : Affichage de la sortie des commandes en direct
- **Bouton Arrêter** : Permet d'interrompre une commande en cours
- **Bouton Effacer** : Nettoie la zone de sortie
- **Confirmations** : Demande confirmation pour les actions critiques
- **Tooltips** : Descriptions au survol des boutons
- **Statut** : Barre de statut en bas de l'interface

## ⚠️ Notes

- Les commandes s'exécutent dans un thread séparé pour ne pas bloquer l'interface
- Les commandes avec confirmation (comme `db-reset`, `docker-rebuild-prod`) demandent une confirmation avant exécution
- Certaines commandes nécessitent des paramètres (comme `setup` avec version Python, `uv-add` avec nom de package)
- L'interface affiche la sortie en temps réel avec coloration syntaxique
- Le fichier `make.ps1` doit être à la racine du projet (répertoire parent de `config_tkinter`)

## 🔧 Dépannage

Si l'interface ne se lance pas :
1. Vérifiez que Python est installé : `python --version`
2. Vérifiez que Tkinter est disponible (généralement inclus avec Python)
3. Sur Linux, installez `python3-tk` si nécessaire

Si une commande échoue :
- Consultez la zone de sortie pour voir les erreurs détaillées
- Vérifiez que le fichier `make.ps1` est présent à la racine du projet
- Vérifiez que PowerShell est disponible sur le système


