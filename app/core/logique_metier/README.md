# 🔧 Logique Métier d'Initialisation

Ce dossier contient les **initialisations automatiques** nécessaires au fonctionnement du système.

## 📋 Différence avec `/scripts/`

### **`/app/core/logique_metier/`** (Logique métier - Automatique)
✅ **Initialisations obligatoires** pour le fonctionnement du système
✅ Exécutées **automatiquement** au démarrage de l'application
✅ **Idempotentes** : peuvent être exécutées plusieurs fois sans problème
✅ **Ne créent PAS de données utilisateur**, seulement la structure logique

**Exemples :**
- `rh_workflow.py` : Circuit de validation des demandes RH (DRAFT → SUBMITTED → VALIDATION → etc.)
- Futures initialisations métier (workflows budgétaires, etc.)

### **`/scripts/`** (Scripts utilitaires - Manuel)
⚙️ **Scripts d'initialisation de données** (référentiels, utilisateurs, etc.)
⚙️ Exécutés **manuellement** par l'administrateur ou au setup initial
⚙️ Créent des **données de référence** que l'utilisateur peut modifier

**Exemples :**
- `init_db.py` : Initialisation complète de la base
- `init_structure_orga.py` : Création des Programmes/Directions/Services (DÉSACTIVÉ)
- `init_grades_fonction_publique.py` : Création des grades (DÉSACTIVÉ)
- `create_user.py` : Création manuelle d'utilisateurs

## 🔄 Fichiers dans ce dossier

### `rh_workflow.py`
**Fonction :** `ensure_workflow_steps(session: Session)`

**Initialise :** Les étapes de workflow pour les demandes RH
- CONGE (Congés)
- PERMISSION (Permissions)
- FORMATION (Formations)
- BESOIN_ACTE (Actes administratifs)

**Circuit :** DRAFT → SUBMITTED → N+1 → N+2 → DRH → DAF → ARCHIVED

**Appelé par :**
- `app.main:startup_event()` (au démarrage de l'app)
- `app.db.session:get_session()` (à chaque connexion DB)

## 📌 Principes

1. **Idempotence** : Les fonctions vérifient si les données existent avant de les créer
2. **Logging** : Toutes les opérations sont loggées
3. **Pas de données utilisateur** : Seulement la structure logique nécessaire
4. **Pas d'échec bloquant** : Les erreurs sont loggées mais n'empêchent pas le démarrage

## 🎯 Quand ajouter un fichier ici ?

Ajoutez un fichier dans `/app/core/logique_metier/` si :
- ✅ C'est une **logique métier** nécessaire au fonctionnement
- ✅ Ça doit être exécuté **automatiquement** au démarrage
- ✅ C'est **idempotent** (peut être exécuté plusieurs fois)
- ✅ Ça ne crée **PAS de données personnalisables** par l'utilisateur

**N'ajoutez PAS** ici si :
- ❌ Ce sont des données de référence modifiables (→ utiliser l'interface)
- ❌ C'est un script ponctuel/migration (→ `/scripts/`)
- ❌ C'est spécifique à un déploiement (→ `/deploy/`)

