# Résumé des Modifications : Nouvelles Colonnes en Base de Données

## ✅ Modifications Complétées

### 1. Table `system_settings` - Nouvelles colonnes ajoutées

#### Informations du ministre
- ✅ `minister_nomination_date: str | None` - Date de nomination (ex: "17 octobre 2023")
- ✅ `decret_attribution_numero: str | None` - Numéro du décret d'attribution (ex: "n° 2023-820")
- ✅ `decret_attribution_date: str | None` - Date du décret d'attribution (ex: "25 octobre 2023")

#### Structure organisationnelle
- ✅ `structure_cabinet: str | None` - Nom du cabinet (ex: "Cabinet du Ministre")
- ✅ `nb_directions_centrales: int | None` - Nombre de directions centrales
- ✅ `nb_services: int | None` - Nombre de services
- ✅ `nb_directions_generales: int | None` - Nombre de directions générales
- ✅ `decret_organisation_numero: str | None` - Numéro du décret d'organisation (ex: "n° 2023-963")
- ✅ `decret_organisation_date: str | None` - Date du décret d'organisation (ex: "6 décembre 2023")

#### Contexte et structure du rapport
- ✅ `contexte_texte: str | None` - Texte de contexte pour l'introduction générale
- ✅ `rapport_structure_premiere_partie: str | None` - Structure première partie (JSON)
- ✅ `rapport_structure_seconde_partie: str | None` - Structure seconde partie (JSON)

#### Informations pays/devise
- ✅ `pays: str | None` - Nom du pays (ex: "République de Côte d'Ivoire")
- ✅ `devise: str | None` - Devise nationale (ex: "Union – Discipline – Travail")
- ✅ `section: str | None` - Section administrative (ex: "SECTION 376")

### 2. Table `direction` - Nouvelle colonne

- ✅ `type: str | None` - Type de direction (ex: "CENTRALE", "GENERALE")
  - Index ajouté pour faciliter les requêtes par type

## 🔧 Modifications des Fichiers

### Modèles (`app/models/`)
1. **`system_settings.py`** : Ajout de toutes les nouvelles colonnes dans le modèle
2. **`personnel.py`** : Ajout de la colonne `type` dans le modèle `Direction`

### Services (`app/services/`)
1. **`system_settings_service.py`** : Mise à jour de `ensure_schema()` pour ajouter automatiquement toutes les nouvelles colonnes de `system_settings`

### API (`app/api/v1/endpoints/`)
1. **`referentiels.py`** : 
   - Ajout du paramètre `type` dans `api_create_direction`
   - Ajout du paramètre `type` dans `api_update_direction`
   - Ajout du champ `type` dans la réponse de `api_list_directions_ref`

## 🔄 Migration Automatique

### SystemSettings
- Les colonnes seront ajoutées automatiquement au démarrage via `SystemSettingsService.ensure_schema()`
- Chaque colonne est ajoutée individuellement avec gestion d'erreur (rollback si échec)

### Direction
- La colonne `type` sera détectée et ajoutée automatiquement par le script `scripts/migrate_schema.py` au démarrage
- Le script compare le schéma attendu (depuis les modèles SQLModel) avec le schéma actuel et applique les différences

## 📝 Prochaines Étapes

1. **Mettre à jour le service de rapport** : Modifier `rapport_annuel_performance_service_simpledoc.py` pour charger ces nouvelles colonnes depuis la DB dans `load_system_settings_data()`

2. **Interface utilisateur** : Créer/modifier les formulaires pour permettre la saisie de ces informations dans les paramètres système

3. **Migration des données** : Optionnel - Migrer les valeurs par défaut actuelles vers la base de données

## 🎯 Utilisation

Toutes ces colonnes sont optionnelles (`None` par défaut), permettant une migration progressive :
- Si une valeur est présente en DB → Utilisée (stylée en bleu dans le rapport)
- Si aucune valeur en DB → Valeur par défaut utilisée (stylée en rouge dans le rapport)
- Si valeur fournie par l'utilisateur via modal → Valeur utilisée (stylée en vert dans le rapport)

