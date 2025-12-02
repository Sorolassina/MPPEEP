# Documentation : Génération du Rapport Annuel de Performance (RAP)

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture du système](#architecture-du-système)
3. [Flux de génération étape par étape](#flux-de-génération-étape-par-étape)
4. [Fonctions principales](#fonctions-principales)
5. [Tables de base de données](#tables-de-base-de-données)
6. [Formatage et styles](#formatage-et-styles)
7. [Guide de modification](#guide-de-modification)

---

## Vue d'ensemble

Le service `RapportAnnuelPerformanceGeneratorSimpleDoc` génère un PDF de rapport annuel de performance en format paysage (Landscape A4). Il utilise deux approches combinées :

- **Canvas** (`reportlab.pdfgen.canvas`) : Pour les pages fixes (couverture, sommaire, listes, introduction)
- **SimpleDocTemplate** (`reportlab.platypus.SimpleDocTemplate`) : Pour les sections avec tableaux longs qui nécessitent un découpage automatique sur plusieurs pages

### Mode de fonctionnement

- **Mode "brouillon"** : Génère des données factices si la base est vide, formatées en violet italique
- **Mode "final"** : Utilise uniquement les données de la base de données, sans formatage de couleur

### Structure du rapport

1. **Couverture** (Canvas)
2. **Sommaire** (Canvas)
3. **Liste des tableaux** (Canvas)
4. **Liste des graphiques** (Canvas)
5. **Sigles et abréviations** (Canvas)
6. **Introduction générale** (Canvas)
7. **PARTIE I : Le Ministère** (Canvas)
8. **PARTIE II : Programmes** (SimpleDocTemplate) - Une partie par programme
9. **Conclusion générale** (SimpleDocTemplate)

---

## Architecture du système

### Classes et variables de classe

```python
class RapportAnnuelPerformanceGeneratorSimpleDoc:
    data: dict[str, Any]  # Données globales du rapport (DB + formulaire)
    _db_session: Session  # Session de base de données
    _db_data_keys: set    # Clés identifiant les données provenant de la DB
```

### Variables importantes

- `cls.data` : Dictionnaire contenant toutes les données du rapport (fusion de DB + données formulaire)
- `cls._db_data_keys` : Set contenant les clés des données provenant de la base (pour le formatage)
- `mode` : "brouillon" ou "final" (détermine si on génère des données factices)

---

## Flux de génération étape par étape

### Étape 1 : Initialisation (`generate_pdf`)

**Ligne** : `11073`

1. Initialise `cls._db_session` et `cls._db_data_keys`
2. Charge les données depuis la base via `load_system_settings_data()`
3. Fusionne les données DB avec les données du formulaire (priorité aux données DB)
4. Détermine l'année (utilise l'année en cours si non fournie)
5. Charge les données budgétaires via `load_budget_data()`

**Tables utilisées** :
- `system_settings`
- `rap_data`
- Tables référentielles (pour calculer nb_directions, nb_services)

### Étape 2 : Génération de la couverture (`_draw_cover_block`)

**Ligne** : `603`

**Éléments générés** :
- Titre du rapport + nom du ministère
- Titre de l'année
- Date de publication
- Logo du ministère

**Données utilisées** :
- `cls.data["titre_rapport"]` (RapData)
- `cls.data["ministere"]` (SystemSettings)
- `cls.data["titre_annee"]` (RapData)
- `cls.data["date_publication"]` (RapData, converti de ISO à français)
- `cls.data["logo_path"]` (SystemSettings)

**Méthode** : Canvas direct (page fixe)

### Étape 3 : Génération des pages préliminaires

Toutes ces pages utilisent **Canvas** :

#### 3.1. Table des matières (`_draw_table_of_contents`)
**Ligne** : `806`

Génère automatiquement le sommaire en parcourant la structure du rapport.

**Données utilisées** :
- `cls.data["rapport_structure_premiere_partie"]` (RapData, JSON)
- `cls.data["rapport_structure_seconde_partie"]` (RapData, JSON)
- Numéros de pages calculés dynamiquement

#### 3.2. Liste des tableaux (`_draw_liste_tableaux`)
**Ligne** : `1057`

Liste tous les tableaux du rapport avec leurs numéros de pages.

**Données utilisées** :
- Liste statique des tableaux (`TABLEAUX_LIST`) définie dans le code
- Numéros de pages calculés

#### 3.3. Liste des graphiques (`_draw_liste_graphiques`)
**Ligne** : `1284`

Liste tous les graphiques du rapport.

**Données utilisées** :
- Liste statique des graphiques (`GRAPHiques_LIST`) définie dans le code
- Numéros de pages calculés

#### 3.4. Sigles et abréviations (`_draw_liste_sigles_abreviations`)
**Ligne** : `1511`

Affiche les sigles et leurs définitions.

**Données utilisées** :
- Liste statique (`SIGLES_ABREVIATIONS`) dans le code
- Sigle du ministère (calculé automatiquement depuis le nom)

### Étape 4 : Introduction générale (`_draw_introduction_generale`)

**Ligne** : `1895`

**Éléments générés** :
- Contexte du rapport
- Informations sur le ministre (nom, date de nomination, décrets)
- Mission du ministère
- Structure organisationnelle
- Architecture programmatique (nb programmes, activités)

**Données utilisées** :
- `cls.data["introduction"]["contexte_texte"]` (RapData)
- `cls.data["introduction"]["ministre_nom"]` (SystemSettings)
- `cls.data["introduction"]["ministre_date_nomination"]` (SystemSettings)
- `cls.data["introduction"]["decret_attribution_numero"]` (SystemSettings)
- `cls.data["introduction"]["decret_attribution_date"]` (SystemSettings)
- `cls.data["introduction"]["mission_ministere"]` (SystemSettings)
- `cls.data["introduction"]["structure_cabinet"]` (SystemSettings)
- `cls.data["introduction"]["structure_directions_centrales"]` (calculé depuis référentiels)
- `cls.data["introduction"]["structure_services"]` (calculé depuis référentiels)
- `cls.data["introduction"]["structure_directions_generales"]` (calculé depuis référentiels)
- `cls.data["partie_ministere"]["total_programmes"]` (calculé depuis DB)
- `cls.data["partie_ministere"]["total_activites"]` (calculé depuis DB)

**Méthode** : Canvas direct

### Étape 5 : PARTIE I - Le Ministère (`_draw_partie_i_ministere`)

**Ligne** : `2242`

**Sections générées** :

#### I.1. Architecture programmatique
- Nombre de programmes
- Nombre total d'activités
- Répartition par programme (graphique camembert)

**Données utilisées** :
- `cls.data["partie_ministere"]["total_programmes"]` (DB : comptage depuis sigobe_execution)
- `cls.data["partie_ministere"]["total_activites"]` (DB : comptage depuis sigobe_execution)
- `cls.data["partie_ministere"]["programme_details"]` (DB : liste des programmes avec leurs stats)

#### I.2. Performance générale du Ministère
- Nombre d'indicateurs de performance
- Taux de réalisation (calculé depuis indicateurs)

**Données utilisées** :
- Hiérarchie de performance (Orientations stratégiques → Résultats stratégiques → Objectifs → Indicateurs)
- Tables : `orientation_strategique`, `resultat_strategique`, `objectif_performance`, `indicateur_performance`

#### I.3. Financement global du Ministère
- Tableau récapitulatif des dépenses par nature
- Graphique camembert de répartition
- Taux d'exécution global
- Analyse textuelle personnalisée

**Données utilisées** :
- `cls.data["financement_interpretations"]` (RapData, JSON) :
  - `taux_execution_global`
  - `raisons_augmentation` (liste)
  - `note_comparaison`
  - `analyse_personnel`, `analyse_biens`, `analyse_transferts`, `analyse_investissements`
- Données d'exécution depuis `sigobe_execution` (par nature de dépense)

**Tables** :
- `sigobe_execution` : Dépenses réelles par nature
- `sigobe_chargement` : Métadonnées des chargements

**Méthode** : Canvas direct

### Étape 6 : PARTIE II - Programmes (`_draw_partie_programme_simpledoc`)

**Ligne** : `6526`

**Méthode** : SimpleDocTemplate (découpage automatique des tableaux longs)

**Généré pour CHAQUE programme** :

#### II.1. Présentation du programme
- Numéro et titre du programme
- Missions du programme
- Structure du programme

**Données utilisées** :
- `programme["numero"]` et `programme["titre"]` (DB ou factice)
- Missions depuis la hiérarchie de performance ou données factices

#### II.1.1. Évolution des taux d'exécution par action
- Tableau récapitulatif des actions
- Graphique en barres d'évolution

**Données utilisées** :
- Actions depuis `sigobe_execution` (groupées par action)
- Taux d'exécution calculés : `budget_execute / budget_initial * 100`

**Tables** :
- `sigobe_execution` : Données d'exécution par action

**Fonctions utilitaires** :
- `_create_bar_chart_execution_rates()` (ligne `4890`) : Génère le graphique en barres

#### II.1.2. Suivi des investissements
- Tableau des projets d'investissement
- Analyse textuelle

**Données utilisées** :
- `_get_investissement_data()` (ligne `5098`) : Récupère depuis `sigobe_execution` où `type_depense` contient "INVESTISSEMENT"
- En mode brouillon : génère 3 projets factices avec taux d'exécution variés

**Tables** :
- `sigobe_execution` : Projets d'investissement

**Fonctions utilitaires** :
- `_create_investissement_table()` (ligne `5242`) : Crée le tableau

#### II.2. Évolution des effectifs
- Tableau par catégorie
- Graphique en barres
- Analyse textuelle

**Données utilisées** :
- `_get_effectifs_data()` (ligne `6091`) : Depuis `agent_complet` (joint avec `grade_complet`)
- En mode brouillon : génère 5 catégories factices

**Tables** :
- `agent_complet` : Effectifs
- `grade_complet` : Grades des agents

**Fonctions utilitaires** :
- `_create_effectifs_table()` (ligne `6203`) : Crée le tableau
- `_create_bar_chart_effectifs()` (ligne `6430`) : Génère le graphique

#### II.3. Bilan des activités en rapport avec les axes stratégiques
- Liste des activités majeures (triées par taux d'exécution décroissant)

**Données utilisées** :
- `_get_activites_majeures()` (ligne `5508`) : Depuis `activite_budgetaire`
- En mode brouillon : génère des activités factices

**Tables** :
- `activite_budgetaire` : Activités budgétaires

#### III. Performance du programme

##### III.1. Présentation de l'évolution des indicateurs de performance
- Tableau détaillé des indicateurs
- Graphiques d'évolution pour chaque indicateur
- Analyse textuelle pour chaque indicateur

**Données utilisées** :
- `_get_indicateurs_performance_data()` (ligne `5572`) : Depuis `indicateur_performance` avec jointure sur `objectif_performance`
- Structure hiérarchique : Objectif Spécifique → Indicateurs
- En mode brouillon : génère 3 OS avec 2, 3 et 2 indicateurs respectivement

**Tables** :
- `indicateur_performance` : Indicateurs avec réalisations par année
- `objectif_performance` : Objectifs spécifiques (type OPERATIONNEL)
- `resultat_strategique` : Résultats stratégiques
- `orientation_strategique` : Orientations stratégiques

**Structure des données d'indicateurs** :
```python
{
    "objectif_titre": "Objectif Spécifique 1: ...",
    "indicateur_nom": "Nom de l'indicateur",
    "unite": "%",
    "realisation_2022": 95.0,
    "realisation_2023": 93.0,
    "realisation_2024": 89.0,
    "prevision_2025": 100.0,
    "realisation_2025": 96.0,
    "_source": "default" ou "db"  # Pour le formatage
}
```

**Fonctions utilitaires** :
- `_create_indicateurs_table()` (ligne `5855`) : Crée le tableau avec regroupement par OS
- `_create_indicateur_evolution_chart()` (ligne `4993`) : Génère le graphique en ligne (échelle fixe 0-100%)

#### IV. Points positifs, Difficultés, Recommandations et Conclusion
- Points positifs (liste à puces)
- Difficultés rencontrées
- Recommandations
- Conclusion

**Données utilisées** :
- `cls.data["conclusion_interpretations"][code_programme]` (RapData, JSON) :
  - `points_positifs` (liste)
  - `difficultes` (texte)
  - `recommandations` (texte)
  - `conclusion` (texte)
- En mode brouillon : génère des données factices si la DB est vide

**Tables** :
- `rap_data.conclusion_interpretations` : JSON structuré par code_programme

### Étape 7 : Conclusion générale (`_draw_conclusion_generale`)

**Ligne** : `10311`

**Méthode** : SimpleDocTemplate

**Éléments générés** :
- Introduction (bilan de l'année)
- Performance des indicateurs
- Exécution budgétaire
- Avancées principales
- Limites et recommandations
- Perspectives d'avenir
- Signature du ministre

**Données utilisées** :
- `cls.data["conclusion_generale"]` (RapData, JSON) :
  - `intro`
  - `performance_indicators`
  - `budget_execution`
  - `avancees`
  - `limites`
  - `perspectives`
- En mode brouillon : génère des données factices avec statistiques calculées

**Tables** :
- `rap_data.conclusion_generale` : JSON avec les paragraphes

**Données calculées automatiquement** :
- Nombre de programmes (depuis `cls.data["programmes"]`)
- Nombre d'indicateurs (depuis `indicateur_performance`)
- Taux d'exécution global (depuis `financement_interpretations`)

---

## Fonctions principales

### Fonction d'entrée

#### `generate_pdf(cls, data: dict[str, Any], session=None) -> BytesIO`
**Ligne** : `11073`

**Rôle** : Point d'entrée principal pour la génération du PDF

**Paramètres** :
- `data` : Données du formulaire (priorité inférieure aux données DB)
- `session` : Session SQLAlchemy/SQLModel

**Processus** :
1. Initialise les variables de classe
2. Charge les données DB via `load_system_settings_data()`
3. Fusionne DB + données formulaire
4. Charge les données budgétaires via `load_budget_data()`
5. Génère la couverture (Canvas)
6. Génère les pages préliminaires (Canvas)
7. Génère les parties programmes (SimpleDocTemplate)
8. Génère la conclusion générale (SimpleDocTemplate)
9. Fusionne tous les PDFs avec PyPDF2
10. Retourne le buffer final

**Retour** : `BytesIO` contenant le PDF complet

---

### Fonctions de chargement de données

#### `load_system_settings_data(cls, session: Session | None) -> dict[str, Any]`
**Ligne** : `9854`

**Rôle** : Charge toutes les données depuis `SystemSettings` et `RapData`

**Tables utilisées** :
- `system_settings` : Informations générales du ministère
- `rap_data` : Données spécifiques au RAP
- Tables référentielles : Pour calculer la structure organisationnelle

**Données chargées** :

| Clé | Source | Description |
|-----|--------|-------------|
| `ministere` | `system_settings.minister_role` ou `company_name` | Nom du ministère |
| `logo_path` | `system_settings.logo_path` | Chemin du logo |
| `introduction.ministre_nom` | `system_settings.minister_civility` + `minister_name` | Nom complet du ministre |
| `introduction.ministre_date_nomination` | `system_settings.minister_nomination_date` | Date de nomination |
| `introduction.decret_attribution_numero` | `system_settings.decret_attribution_numero` | Numéro du décret |
| `introduction.decret_attribution_date` | `system_settings.decret_attribution_date` | Date du décret |
| `introduction.mission_ministere` | `system_settings.ministry_mission` | Mission du ministère |
| `introduction.structure_cabinet` | `system_settings.structure_cabinet` | Structure du cabinet |
| `introduction.structure_directions_centrales` | Calculé depuis `direction` | Nombre de directions |
| `introduction.structure_services` | Calculé depuis `service` | Nombre de services |
| `introduction.structure_directions_generales` | Calculé depuis référentiels | Nombre de DG |
| `introduction.contexte_texte` | `rap_data.contexte_texte` | Texte de contexte |
| `introduction.rapport_structure_premiere_partie` | `rap_data.rapport_structure_premiere_partie` | Structure (JSON) |
| `introduction.rapport_structure_seconde_partie` | `rap_data.rapport_structure_seconde_partie` | Structure (JSON) |
| `titre_rapport` | `rap_data.titre_rapport` | Titre du rapport |
| `titre_annee` | `rap_data.titre_annee` | Titre de l'année |
| `annee` | `rap_data.annee` | Année de référence |
| `date_publication` | `rap_data.date_publication` | Date (convertie ISO → français) |
| `financement_interpretations` | `rap_data.financement_interpretations` | Interprétations (JSON) |
| `conclusion_interpretations` | `rap_data.conclusion_interpretations` | Interprétations (JSON) |
| `conclusion_generale` | `rap_data.conclusion_generale` | Conclusion (JSON) |
| `orientations_strategiques` | `rap_data.orientations_strategiques` | Orientations (JSON) |

**Marquage DB** : Toutes les clés chargées sont ajoutées à `cls._db_data_keys` pour le formatage

#### `load_budget_data(cls, session: Session | None, annee: int) -> dict[str, Any]`
**Ligne** : `10681`

**Rôle** : Charge les données budgétaires et de programmes

**Tables utilisées** :
- `sigobe_execution` : Données d'exécution budgétaire (PRIORITÉ)
- `sigobe_chargement` : Métadonnées des chargements SIGOBE
- `programme` : Programmes
- `action_budgetaire` : Actions budgétaires
- `activite_budgetaire` : Activités budgétaires
- `nature_depense` : Natures de dépense

**Données chargées** :

| Clé | Source | Description |
|-----|--------|-------------|
| `programmes[]` | `sigobe_execution` (groupé par programme) | Liste des programmes avec stats |
| `total_programmes` | Comptage depuis `sigobe_execution` | Nombre total de programmes |
| `total_actions` | Comptage depuis `action_budgetaire` | Nombre total d'actions |
| `total_activites` | Comptage depuis `activite_budgetaire` | Nombre total d'activités |
| `execution` | Agrégation depuis `sigobe_execution` | Stats globales d'exécution |
| `financement_par_nature` | `sigobe_execution` (groupé par nature) | Dépenses par nature |

**Structure d'un programme** :
```python
{
    "numero": 1,
    "code": "P1",
    "titre": "ADMINISTRATION GÉNÉRALE",
    "nb_actions": 5,
    "nb_activites": 15
}
```

#### `_load_performance_hierarchy_from_db(cls, session: Session | None) -> list[dict[str, Any]] | None`
**Ligne** : `10170`

**Rôle** : Charge la hiérarchie complète de performance

**Tables utilisées** :
- `orientation_strategique`
- `resultat_strategique`
- `objectif_performance` (type STRATEGIQUE et OPERATIONNEL)
- `indicateur_performance`

**Structure hiérarchique** :
```
Orientations stratégiques
  └── Résultats stratégiques
      └── Objectifs globaux (type STRATEGIQUE)
          └── Objectifs spécifiques (type OPERATIONNEL)
              └── Indicateurs de performance
```

**Retour** : Liste de dictionnaires représentant la hiérarchie complète

---

### Fonctions de génération Canvas

Toutes ces fonctions utilisent `canvas.Canvas` pour générer des pages fixes :

#### `_draw_background_shapes(pdf, width, height)`
**Ligne** : `4475`

**Rôle** : Dessine les formes de fond (lignes décoratives)

#### `_draw_header(pdf, width, height)`
**Ligne** : `448`

**Rôle** : Dessine l'en-tête (logo, sigle) sur chaque page

**Données** :
- `cls.data["logo_path"]`
- `cls._get_sigle_ministere()`

#### `_draw_footer(pdf, width, height)`
**Ligne** : `397`

**Rôle** : Dessine le pied de page (date dynamique dans la petite carte orange)

**Données** :
- Date actuelle (mois/année) formatée

#### `_draw_cover_block(pdf, width, height)`
**Ligne** : `603`

**Rôle** : Génère la page de couverture complète

**Éléments** :
- Titre du rapport + nom du ministère
- Titre de l'année
- Date de publication
- Logo

#### `_draw_table_of_contents(pdf, width, height) -> int`
**Ligne** : `806`

**Rôle** : Génère la table des matières automatique

**Processus** :
1. Parse les structures première et seconde partie
2. Parcourt récursivement la hiérarchie
3. Dessine chaque entrée avec sa pagination

**Retour** : Numéro de page final

#### `_draw_liste_tableaux(pdf, width, height, start_page) -> int`
**Ligne** : `1057`

**Rôle** : Liste tous les tableaux du rapport

**Données** : Liste statique `TABLEAUX_LIST`

#### `_draw_liste_graphiques(pdf, width, height, start_page) -> int`
**Ligne** : `1284`

**Rôle** : Liste tous les graphiques du rapport

**Données** : Liste statique `GRAPHiques_LIST`

#### `_draw_liste_sigles_abreviations(pdf, width, height, start_page) -> int`
**Ligne** : `1511`

**Rôle** : Affiche les sigles et leurs définitions

**Données** : Liste statique `SIGLES_ABREVIATIONS` + sigle du ministère calculé

#### `_draw_introduction_generale(pdf, width, height, start_page) -> int`
**Ligne** : `1895`

**Rôle** : Génère l'introduction générale complète

**Sections** :
- Contexte
- Présentation du ministre
- Mission du ministère
- Structure organisationnelle
- Architecture programmatique

#### `_draw_partie_i_ministere(pdf, width, height, start_page) -> int`
**Ligne** : `2242`

**Rôle** : Génère la PARTIE I complète

**Sections** :
- I.1. Architecture programmatique
- I.2. Performance générale du Ministère
- I.3. Financement global du Ministère

---

### Fonctions de génération SimpleDocTemplate

#### `_draw_partie_programme_simpledoc(programme, start_page, session) -> tuple[BytesIO, int]`
**Ligne** : `6526`

**Rôle** : Génère une partie programme complète avec SimpleDocTemplate

**Paramètres** :
- `programme` : Dictionnaire contenant numero, titre, code
- `start_page` : Numéro de page de départ
- `session` : Session de base de données

**Processus** :
1. Crée un `SimpleDocTemplate` temporaire
2. Construit une `story` avec tous les éléments (Paragraphs, Tables, Images, Spacers)
3. Utilise `LongTable` pour les tableaux qui peuvent se découper
4. Génère un PDF temporaire
5. Retourne le buffer et le numéro de page final

**Sections générées** :
- Présentation du programme
- Évolution des taux d'exécution par action
- Suivi des investissements
- Évolution des effectifs
- Bilan des activités majeures
- Performance du programme (indicateurs)
- Points positifs, Difficultés, Recommandations, Conclusion

**Retour** : `(BytesIO buffer, numéro_page_final)`

#### `_draw_conclusion_generale(start_page, session) -> tuple[BytesIO, int]`
**Ligne** : `10311`

**Rôle** : Génère la conclusion générale avec signature

**Retour** : `(BytesIO buffer, numéro_page_final)`

---

### Fonctions de récupération de données

#### `_get_investissement_data(numero, titre, annee, session) -> list[dict]`
**Ligne** : `5098`

**Rôle** : Récupère les projets d'investissement pour un programme

**Tables** : `sigobe_execution`

**Filtres** :
- `annee == annee`
- `programmes.ilike(f"%{titre}%")`
- `type_depense.ilike("%INVESTISSEMENT%")`

**En mode brouillon** : Génère 3 projets factices avec montants et taux variables

**Retour** : Liste de dictionnaires avec :
```python
{
    "nom": "Nom du projet",
    "annee_debut": 2023,
    "annee_fin": 2025,
    "budget_total": 100000000.0,
    "_taux_execution": 0.65,  # Flag pour détecter données factices
    "_is_fake": True  # Flag explicite
}
```

#### `_get_effectifs_data(numero, titre, annee, session) -> list[dict]`
**Ligne** : `6091`

**Rôle** : Récupère les effectifs par catégorie pour un programme

**Tables** :
- `agent_complet` : Agents avec leurs affectations
- `grade_complet` : Grades

**Jointures** : Agent → Grade → Catégorie

**En mode brouillon** : Génère 5 catégories factices (A, B, C, D, Non Fonctionnaires)

**Retour** : Liste avec :
```python
{
    "categorie": "Catégorie A",
    "effectif_2024": 25,  # Année dynamique
    "besoins_exprimes": 5,
    "previsions": 5,
    "besoins_satisfaits": 4,
    "sorties": 2,
    "_is_fake": True
}
```

#### `_get_activites_majeures(numero, titre, annee, session) -> list[dict]`
**Ligne** : `5508`

**Rôle** : Récupère les activités majeures (triées par taux d'exécution décroissant)

**Tables** : `activite_budgetaire`

**Critère** : Taux d'exécution le plus élevé

**En mode brouillon** : Génère des activités factices

#### `_get_indicateurs_performance_data(numero, titre, annee, session) -> list[dict]`
**Ligne** : `5572`

**Rôle** : Récupère les indicateurs de performance pour un programme

**Tables** :
- `indicateur_performance` : Indicateurs avec réalisations par année
- `objectif_performance` : Objectifs spécifiques (type OPERATIONNEL)

**Jointures** : Indicateur → Objectif Spécifique → Programme

**Filtres** :
- `objectif_performance.type == "OPERATIONNEL"`
- `programme.numero == numero`
- Années : N-3, N-2, N-1, N

**Structure retournée** :
```python
[
    {
        "objectif_titre": "Objectif Spécifique 1: ...",
        "indicateur_nom": "Nom de l'indicateur",
        "unite": "%",
        "realisation_2022": 95.0,
        "realisation_2023": 93.0,
        "realisation_2024": 89.0,
        "prevision_2025": 100.0,
        "realisation_2025": 96.0,
        "_source": "db"  # ou "default" pour factice
    },
    ...
]
```

**En mode brouillon** : Génère 3 Objectifs Spécifiques avec 2, 3, 2 indicateurs respectivement

---

### Fonctions de création de tableaux

#### `_create_indicateurs_table(indicateurs_data, available_width, annee, format_programme_value) -> LongTable`
**Ligne** : `5855`

**Rôle** : Crée le tableau des indicateurs de performance avec regroupement par OS

**Caractéristiques** :
- En-têtes multi-niveaux avec années dynamiques (N-3, N-2, N-1, N)
- Regroupement : Un titre d'OS affiché une fois, suivi de tous ses indicateurs
- Formatage selon la source (DB = rouge, factice = violet italique)

**Colonnes** :
1. Indicateurs de performance (40%)
2. Unité (8%)
3. Réalisation N-3 (10%)
4. Réalisation N-2 (10%)
5. Réalisation N-1 (10%)
6. Prévision N (11%)
7. Réalisation N (11%)

#### `_create_effectifs_table(effectifs_data, available_width, annee, is_fake, format_programme_value) -> LongTable`
**Ligne** : `6203`

**Rôle** : Crée le tableau des effectifs par catégorie

**Colonnes** :
1. Catégorie
2. Effectif N-1
3. Besoins exprimés
4. Prévisions
5. Besoins satisfaits
6. Sorties
7. Effectif fin d'année

#### `_create_investissement_table(projects, available_width, format_fcfa, annee, is_fake, format_programme_value) -> LongTable`
**Ligne** : `5242`

**Rôle** : Crée le tableau des projets d'investissement

**Colonnes** :
1. Projet
2. Année début
3. Année fin
4. Budget total

---

### Fonctions de création de graphiques

#### `_create_indicateur_evolution_chart(indicateur_nom, annee, valeurs) -> BytesIO | None`
**Ligne** : `4993`

**Rôle** : Génère un graphique en ligne pour l'évolution d'un indicateur

**Caractéristiques** :
- **Échelle fixe** : 0 à 100%
- Ticks toutes les 10%
- 4 points (N-3, N-2, N-1, N)
- Fond blanc, grille horizontale visible

**Bibliothèque** : Matplotlib

**Retour** : Buffer PNG ou None (si mode final sans données)

#### `_create_bar_chart_execution_rates(actions_rates, annee_precedente, annee, numero_programme, titre_programme) -> BytesIO | None`
**Ligne** : `4890`

**Rôle** : Génère un graphique en barres pour les taux d'exécution par action

**Caractéristiques** :
- Barres pour N-1 et N
- Couleurs : `#5b9bd5` et `#ed7d31`
- Fond blanc, grille horizontale
- Échelle Y : +10 points au-dessus du maximum

#### `_create_bar_chart_effectifs(effectifs_data, annee_precedente, annee, numero_programme, titre_programme) -> BytesIO | None`
**Ligne** : `6430`

**Rôle** : Génère un graphique en barres pour les effectifs par catégorie

**Caractéristiques** :
- Barres groupées par catégorie
- Comparaison N-1 vs N

#### `_create_pie_chart_budget(data, labels, title, colors_list) -> BytesIO | None`
**Ligne** : `4224`

**Rôle** : Génère un graphique en camembert pour la répartition budgétaire

**Utilisé pour** :
- Répartition par programme (PARTIE I)
- Répartition par nature de dépense (PARTIE I)

---

### Fonctions de formatage

#### `_format_db_data(cls, text: str) -> str`
**Ligne** : `1831`

**Rôle** : Formate un texte provenant de la base de données

**Mode brouillon** : `<font color="#FF0000">texte</font>` (rouge)
**Mode final** : Texte normal (sans couleur)

#### `_format_fake_data(cls, text: str) -> str`
**Ligne** : `1857`

**Rôle** : Formate un texte factice/généré

**Mode brouillon** : `<font color="#800080"><i>texte</i></font>` (violet italique)
**Mode final** : Chaîne vide (pas affiché)

#### `format_programme_value(value, is_fake) -> str`
**Ligne** : `6823` (définie localement dans `_draw_partie_programme_simpledoc`)

**Rôle** : Formate une valeur selon sa source (DB ou factice)

**Utilisation** : Utilisée partout dans la partie programme pour formater chaque valeur individuellement

**Logique** :
- Si `is_fake == True` → `_format_fake_data()`
- Sinon → `_format_db_data()`

#### `_get_sigle_ministere(cls) -> str`
**Ligne** : `297`

**Rôle** : Calcule le sigle du ministère depuis son nom

**Processus** :
1. Extrait les premières lettres de chaque mot
2. Retire les accents
3. Retourne le sigle en majuscules

**Exemple** : "MINISTÈRE DU PATRIMOINE" → "MPPEEP"

---

## Tables de base de données

### Table `system_settings`

**Rôle** : Configuration générale du système et informations du ministère

**Colonnes utilisées** :
- `minister_role` : Rôle/titre du ministre (utilisé pour extraire le nom du ministère)
- `company_name` : Nom de l'entreprise/ministère
- `logo_path` : Chemin du logo
- `minister_civility` : Civilité du ministre (Monsieur, Madame)
- `minister_name` : Nom du ministre
- `minister_nomination_date` : Date de nomination
- `decret_attribution_numero` : Numéro du décret d'attribution
- `decret_attribution_date` : Date du décret d'attribution
- `ministry_mission` : Mission du ministère
- `structure_cabinet` : Structure du cabinet
- `decret_organisation_numero` : Numéro du décret d'organisation
- `decret_organisation_date` : Date du décret d'organisation

**Utilisation** : Chargée dans `load_system_settings_data()`

---

### Table `rap_data`

**Rôle** : Données spécifiques au Rapport Annuel de Performance (singleton, ID=1)

**Colonnes utilisées** :

#### Champs texte
- `contexte_texte` : Texte de contexte pour l'introduction
- `rapport_structure_premiere_partie` : Structure première partie (JSON array → string)
- `rapport_structure_seconde_partie` : Structure seconde partie (JSON array → string)

#### Informations générales
- `titre_rapport` : Titre complet du rapport
- `titre_annee` : Titre de l'année (ex: "AU TITRE DE L'ANNÉE")
- `annee` : Année de référence (int)
- `date_publication` : Date de publication (format ISO "YYYY-MM" → convertie en français)

#### Données structurées (JSON)
- `orientations_strategiques` : Orientations stratégiques (JSON)
- `financement_interpretations` : Interprétations du financement (JSON)
- `conclusion_interpretations` : Points positifs, difficultés, recommandations par programme (JSON)
- `conclusion_generale` : Conclusion générale du rapport (JSON)

**Structure JSON `financement_interpretations`** :
```json
{
    "taux_execution_global": 94.74,
    "raisons_augmentation": [
        "Raison 1",
        "Raison 2"
    ],
    "note_comparaison": "Texte de comparaison",
    "analyse_personnel": "Analyse des dépenses de personnel",
    "analyse_biens": "Analyse des biens et services",
    "analyse_transferts": "Analyse des transferts",
    "analyse_investissements": "Analyse des investissements"
}
```

**Structure JSON `conclusion_interpretations`** :
```json
{
    "P1": {
        "points_positifs": [
            "Point 1",
            "Point 2"
        ],
        "difficultes": "Texte des difficultés",
        "recommandations": "Texte des recommandations",
        "conclusion": "Texte de conclusion"
    },
    "P2": { ... }
}
```

**Structure JSON `conclusion_generale`** :
```json
{
    "intro": "Texte d'introduction...",
    "performance_indicators": "Texte sur les indicateurs...",
    "budget_execution": "Texte sur l'exécution budgétaire...",
    "avancees": "Texte sur les avancées...",
    "limites": "Texte sur les limites...",
    "perspectives": "Texte sur les perspectives..."
}
```

---

### Table `sigobe_execution`

**Rôle** : Données d'exécution budgétaire (source principale pour les données financières)

**Colonnes utilisées** :
- `annee` : Année de référence
- `programmes` : Nom du programme (text)
- `actions` : Nom de l'action
- `activites` : Nom de l'activité
- `type_depense` : Type de dépense (INVESTISSEMENT, PERSONNEL, etc.)
- `nature_depense` : Nature de la dépense
- `budget_initial` : Budget initial
- `budget_execute` : Budget exécuté
- `montant_engage` : Montant engagé
- `montant_liquide` : Montant liquidé

**Utilisations** :
1. **Programmes** : Groupement par `programmes` pour identifier les programmes
2. **Actions** : Groupement par `actions` pour les taux d'exécution par action
3. **Investissements** : Filtre `type_depense LIKE '%INVESTISSEMENT%'`
4. **Financement global** : Agrégation par `nature_depense`

**Jointure** : Avec `sigobe_chargement` pour récupérer le dernier chargement de l'année

---

### Table `sigobe_chargement`

**Rôle** : Métadonnées des chargements SIGOBE

**Colonnes utilisées** :
- `annee` : Année
- `date_chargement` : Date du chargement

**Utilisation** : Pour récupérer le dernier chargement d'une année

---

### Table `programme`

**Rôle** : Programmes budgétaires

**Colonnes utilisées** :
- `code` : Code du programme (ex: "P1", "P2")
- `numero` : Numéro du programme
- `libelle` : Libellé/nom du programme

**Utilisation** : Joint avec `objectif_performance` pour récupérer les indicateurs par programme

---

### Table `orientation_strategique`

**Rôle** : Orientations stratégiques du ministère

**Colonnes utilisées** :
- `id`
- `libelle` : Libellé de l'orientation

**Hiérarchie** : Niveau 1 (le plus haut)

---

### Table `resultat_strategique`

**Rôle** : Résultats stratégiques

**Colonnes utilisées** :
- `id`
- `orientation_strategique_id` : FK vers orientation
- `libelle` : Libellé du résultat

**Hiérarchie** : Niveau 2

---

### Table `objectif_performance`

**Rôle** : Objectifs de performance (globaux et spécifiques)

**Colonnes utilisées** :
- `id`
- `resultat_strategique_id` : FK vers résultat stratégique
- `programme_id` : FK vers programme
- `type` : "STRATEGIQUE" (objectif global) ou "OPERATIONNEL" (objectif spécifique)
- `libelle` : Libellé de l'objectif

**Hiérarchie** :
- Niveau 3 (objectifs globaux, type STRATEGIQUE)
- Niveau 4 (objectifs spécifiques, type OPERATIONNEL)

**Filtre important** : Pour les indicateurs du rapport, on utilise uniquement `type == "OPERATIONNEL"`

---

### Table `indicateur_performance`

**Rôle** : Indicateurs de performance avec leurs réalisations par année

**Colonnes utilisées** :
- `id`
- `objectif_performance_id` : FK vers objectif spécifique
- `libelle` : Nom de l'indicateur
- `unite` : Unité de mesure (%%, nombre, etc.)
- `annee` : Année de référence
- `realisation` : Valeur réalisée pour cette année
- `prevision` : Valeur prévue pour cette année

**Structure importante** : Les réalisations sont stockées par année dans des lignes séparées (pas de colonnes par année)

**Exemple** :
```
id | objectif_performance_id | libelle | annee | realisation | prevision
1  | 10                      | Taux... | 2022  | 95.0        | 100.0
1  | 10                      | Taux... | 2023  | 93.0        | 100.0
1  | 10                      | Taux... | 2024  | 89.0        | 100.0
1  | 10                      | Taux... | 2025  | 96.0        | 100.0
```

**Utilisation** : Dans `_get_indicateurs_performance_data()`, les données sont transformées en dictionnaire avec clés dynamiques :
```python
{
    "realisation_2022": 95.0,
    "realisation_2023": 93.0,
    "realisation_2024": 89.0,
    "prevision_2025": 100.0,
    "realisation_2025": 96.0
}
```

---

### Table `action_budgetaire`

**Rôle** : Actions budgétaires

**Colonnes utilisées** :
- `programme_id` : FK vers programme
- `libelle` : Nom de l'action

**Utilisation** : Pour compter le nombre total d'actions

---

### Table `activite_budgetaire`

**Rôle** : Activités budgétaires

**Colonnes utilisées** :
- `programme_id` : FK vers programme
- `libelle` : Nom de l'activité
- Taux d'exécution (calculé) : Pour déterminer les activités majeures

**Utilisation** :
- Comptage du nombre total d'activités
- Récupération des activités majeures (triées par taux d'exécution)

---

### Table `agent_complet`

**Rôle** : Agents avec leurs informations complètes

**Colonnes utilisées** :
- `affectation` : Programme/Structure d'affectation
- Autres informations de l'agent

**Jointure** : Avec `grade_complet` pour déterminer la catégorie

**Utilisation** : Dans `_get_effectifs_data()` pour compter les effectifs par catégorie

---

### Table `grade_complet`

**Rôle** : Grades des agents

**Colonnes utilisées** :
- `categorie` : Catégorie du grade (A, B, C, D, etc.)

**Jointure** : Avec `agent_complet` pour grouper par catégorie

---

### Tables référentielles

#### `direction`
**Utilisation** : Pour calculer `nb_directions_centrales` et `nb_directions_generales`

#### `service`
**Utilisation** : Pour calculer `nb_services`

**Calcul automatique** : Dans `RapDataService.calculate_organization_structure(session)`

---

## Formatage et styles

### Système de formatage selon la source

Le rapport utilise un système de formatage conditionnel basé sur la source des données :

#### Mode "brouillon"
- **Données DB** : Rouge (`#FF0000`)
- **Données factices** : Violet italique (`#800080`, `<i>`)

#### Mode "final"
- **Données DB** : Texte normal (pas de couleur)
- **Données factices** : Non affichées (chaîne vide)

### Détection de la source des données

#### Au niveau programme
```python
is_programme_fake = programme.get("_is_fake", False)
```
- Défini dans `generate_pdf()` : Si programmes viennent de `DEFAULT_DATA`, `_is_fake = True`

#### Au niveau des données spécifiques
- **Investissements** : Détection via `_taux_execution` flag ou noms de projets factices
- **Effectifs** : Flag `_is_fake` ajouté dans `_get_effectifs_data()`
- **Indicateurs** : Flag `_source: "default"` pour factices, `"db"` pour DB

### Fonction `format_programme_value`

**Définie localement** dans `_draw_partie_programme_simpledoc()` (ligne `6823`)

**Usage** :
```python
def format_programme_value(value: Any, is_fake: bool = False) -> str:
    if is_fake:
        return cls._format_fake_data(str(value))
    else:
        return cls._format_db_data(str(value))
```

**Exemples d'utilisation** :
```python
# Année (toujours DB)
formatted_annee = format_programme_value(str(annee), False)

# Titre du programme (peut être factice)
formatted_titre = format_programme_value(titre, is_programme_fake)

# Valeur d'un indicateur (vérifie la source de CET indicateur)
is_this_indicateur_fake = (indicateur.get("_source", "default") == "default")
formatted_valeur = format_programme_value(str(valeur), is_this_indicateur_fake)
```

---

## Guide de modification

### Modifier une section existante

#### Exemple : Modifier la section "I.3. Financement global"

1. **Localiser la fonction** : `_draw_partie_i_ministere()` (ligne `2242`)
2. **Trouver la section** : Rechercher "I.3." ou "FINANCEMENT"
3. **Identifier les données** : Vérifier `cls.data["financement_interpretations"]`
4. **Modifier le code** : Ajuster le texte, les tableaux, ou les graphiques

#### Exemple : Modifier un tableau d'indicateurs

1. **Fonction de création** : `_create_indicateurs_table()` (ligne `5855`)
2. **Modifier les colonnes** : Ajuster `header` et `col_widths`
3. **Modifier le formatage** : Ajuster l'appel à `format_programme_value()`

### Ajouter une nouvelle section

#### Dans une partie Canvas

1. Ajouter le code dans la fonction `_draw_*` appropriée
2. Utiliser `pdf.drawString()` ou `pdf.drawText()` pour le texte
3. Gérer la pagination manuellement si nécessaire

#### Dans une partie SimpleDocTemplate

1. Ajouter des éléments à la `story` :
   ```python
   story.append(Paragraph("Titre", style))
   story.append(Spacer(1, 0.3 * cm))
   story.append(Table(data, colWidths=[...]))
   ```
2. La pagination est automatique

### Modifier le formatage des données

#### Changer la couleur des données DB

**Fichier** : `rapport_annuel_performance_service_simpledoc.py`
**Fonction** : `_format_db_data()` (ligne `1831`)

```python
# Actuel (rouge)
return f'<font color="#FF0000">{text}</font>'

# Modifier en bleu par exemple
return f'<font color="#0000FF">{text}</font>'
```

#### Changer la couleur des données factices

**Fonction** : `_format_fake_data()` (ligne `1857`)

```python
# Actuel (violet italique)
return f'<font color="#800080"><i>{text}</i></font>'
```

### Modifier les données factices

#### Changer les programmes factices

**Constante** : `DEFAULT_DATA["programmes"]` (ligne `~100`)

#### Changer les indicateurs factices

**Fonction** : `_get_indicateurs_performance_data()` (ligne `5572`)
**Variable** : `default_indicateurs` (ligne `~5680`)

Modifier la liste pour ajouter/modifier/supprimer des OS et indicateurs.

### Modifier les styles de texte

#### Styles ParagraphStyle

Les styles sont définis dans chaque fonction qui utilise SimpleDocTemplate :

```python
body_style = ParagraphStyle(
    "Body",
    fontName="Helvetica",
    fontSize=11,
    leading=14,
    alignment=4,  # Justify
)
```

**Propriétés importantes** :
- `fontSize` : Taille de la police
- `leading` : Interligne
- `alignment` : 0=Left, 1=Center, 2=Right, 4=Justify
- `leftIndent`, `rightIndent` : Indentations
- `spaceBefore`, `spaceAfter` : Espacements

### Modifier les dimensions de page

**Format actuel** : Landscape A4
**Définition** : `page_width, page_height = landscape(A4)`

Pour changer en portrait :
```python
from reportlab.lib.pagesizes import A4
page_width, page_height = A4  # Portrait
```

### Ajouter une nouvelle table de données

1. **Créer une fonction de récupération** :
   ```python
   @staticmethod
   def _get_ma_nouvelle_data(numero, titre, annee, session):
       # Requête DB
       # Retourner liste de dict
   ```
2. **L'appeler dans `_draw_partie_programme_simpledoc`**
3. **Créer une fonction de création de tableau/graphique si nécessaire**
4. **Ajouter le formatage avec `format_programme_value()`**

### Modifier la structure d'un tableau

#### Exemple : Ajouter une colonne au tableau des indicateurs

1. **Localiser** : `_create_indicateurs_table()` (ligne `5855`)
2. **Modifier les en-têtes** : Ajouter une nouvelle colonne dans `header`
3. **Ajuster les largeurs** : Modifier `col_widths` (total = 1.0)
4. **Ajouter les données** : Dans la boucle qui crée les lignes

### Modifier un graphique

#### Exemple : Changer l'échelle d'un graphique d'indicateur

**Fonction** : `_create_indicateur_evolution_chart()` (ligne `4993`)

**Actuel** :
```python
ax.set_ylim(0, 100)  # Échelle fixe 0-100%
```

**Modifier** :
```python
# Échelle dynamique
y_min = min(valeurs) - 10
y_max = max(valeurs) + 10
ax.set_ylim(y_min, y_max)
```

### Ajouter une nouvelle source de données

1. **Créer la fonction de chargement** dans `load_system_settings_data()` ou `load_budget_data()`
2. **Ajouter à `cls.data`**
3. **Marquer comme DB** : `cls._db_data_keys.add("ma_cle")`
4. **Utiliser dans les fonctions de génération**

### Modifier la pagination

#### Pages Canvas
- Pagination manuelle : `pdf.showPage()` pour créer une nouvelle page
- Retourner le numéro de page final

#### Pages SimpleDocTemplate
- Pagination automatique gérée par ReportLab
- Utiliser `CondPageBreak()` pour éviter les coupures

---

## Structure des données dans `cls.data`

### Données de premier niveau

```python
cls.data = {
    "ministere": "MINISTERE DU PATRIMOINE...",
    "logo_path": "images/logo.webp",
    "annee": 2025,
    "mode": "brouillon" ou "final",
    "titre_rapport": "RAPPORT ANNUEL DE PERFORMANCE",
    "titre_annee": "AU TITRE DE L'ANNÉE",
    "date_publication": "Novembre 2025",
    # ...
}
```

### Données d'introduction

```python
cls.data["introduction"] = {
    "ministre_nom": "Moussa SANOGO",
    "ministre_date_nomination": date(...),
    "decret_attribution_numero": "2024-123",
    "mission_ministere": "Texte de mission...",
    "structure_directions_centrales": 5,
    "structure_services": 12,
    "contexte_texte": "Texte de contexte...",
    "rapport_structure_premiere_partie": [...],  # JSON array
    "rapport_structure_seconde_partie": [...],   # JSON array
}
```

### Données de partie ministère

```python
cls.data["partie_ministere"] = {
    "total_programmes": 2,
    "total_actions": 32,
    "total_activites": 45,
    "programme_details": [
        {"numero": 1, "titre": "...", "actions": 15, "activites": 20},
        {"numero": 2, "titre": "...", "actions": 17, "activites": 25}
    ],
    "prog1_pct": 44.4,
    "prog2_pct": 55.6,
}
```

### Données de financement

```python
cls.data["financement_interpretations"] = {
    "taux_execution_global": 94.74,
    "raisons_augmentation": ["Raison 1", "Raison 2"],
    "note_comparaison": "...",
    "analyse_personnel": "...",
    "analyse_biens": "...",
    "analyse_transferts": "...",
    "analyse_investissements": "...",
}
```

### Données de programmes

```python
cls.data["programmes"] = [
    {
        "numero": 1,
        "code": "P1",
        "titre": "ADMINISTRATION GÉNÉRALE",
        "nb_actions": 15,
        "nb_activites": 20,
        "_is_fake": False  # ou True si factice
    },
    # ...
]
```

### Données de conclusion par programme

```python
cls.data["conclusion_interpretations"] = {
    "P1": {
        "points_positifs": ["Point 1", "Point 2"],
        "difficultes": "Texte...",
        "recommandations": "Texte...",
        "conclusion": "Texte..."
    },
    "P2": { ... }
}
```

### Données de conclusion générale

```python
cls.data["conclusion_generale"] = {
    "intro": "Texte...",
    "performance_indicators": "Texte...",
    "budget_execution": "Texte...",
    "avancees": "Texte...",
    "limites": "Texte...",
    "perspectives": "Texte..."
}
```

---

## Points d'attention

### Gestion des années dynamiques

Toutes les années sont calculées dynamiquement à partir de `annee` (année N) :
- N-3 : `annee - 3`
- N-2 : `annee - 2`
- N-1 : `annee - 1`
- N : `annee`
- N+1 : `annee + 1`
- N+2 : `annee + 2`

**Important** : Ne jamais hardcoder une année. Toujours utiliser des calculs basés sur `annee`.

### Gestion des données factices

- En mode "brouillon" : Génère des données factices si la DB est vide
- En mode "final" : Retourne des listes vides ou messages "NC"/"0" si pas de données
- Toujours ajouter un flag (`_is_fake`, `_source`, `_taux_execution`) pour identifier les données factices

### Formatage cohérent

- **Chaque valeur individuelle** doit être formatée selon sa propre source
- Ne pas se baser sur un flag global pour toute une section
- Utiliser `format_programme_value(value, is_this_value_fake)` pour chaque valeur

### Pagination

- **Canvas** : Pagination manuelle, retourner le numéro de page final
- **SimpleDocTemplate** : Pagination automatique, utiliser `CondPageBreak()` si nécessaire
- **LongTable** : Découpage automatique sur plusieurs pages

### Fusion de PDFs

Le système fusionne plusieurs PDFs avec PyPDF2 :
1. Couverture (Canvas)
2. Pages préliminaires (Canvas)
3. Parties programmes (SimpleDocTemplate, une par programme)
4. Conclusion générale (SimpleDocTemplate)

**Ordre** : Important de respecter l'ordre lors de l'ajout avec `writer.add_page()`

---

## Exemples pratiques

### Exemple 1 : Modifier le texte d'introduction

**Localisation** : `_draw_introduction_generale()` (ligne `1895`)

**Modification** :
```python
# Trouver la ligne qui génère le texte
intro_text = f"Le texte actuel avec {variable}"

# Modifier
intro_text = f"Le nouveau texte avec {variable}"
```

### Exemple 2 : Ajouter une colonne au tableau des effectifs

**Localisation** : `_create_effectifs_table()` (ligne `6203`)

**Modification** :
1. Ajouter la colonne dans `header`
2. Ajuster `col_widths` (réduire les autres pour faire place)
3. Ajouter la valeur dans la boucle de création des lignes

### Exemple 3 : Changer les couleurs d'un graphique

**Localisation** : `_create_bar_chart_execution_rates()` (ligne `4890`)

**Modification** :
```python
# Actuel
color='#5b9bd5'  # Bleu

# Modifier
color='#FF5733'  # Orange
```

### Exemple 4 : Ajouter une nouvelle statistique dans la PARTIE I

**Localisation** : `_draw_partie_i_ministere()` (ligne `2242`)

**Processus** :
1. Charger les données nécessaires
2. Ajouter un paragraphe ou un tableau dans la section appropriée
3. Formater avec `_format_db_data()` si c'est de la DB

---

## Troubleshooting

### Les données ne s'affichent pas

1. Vérifier que les données sont bien chargées dans `cls.data`
2. Vérifier les logs pour voir si les données DB sont chargées
3. Vérifier que la clé existe dans `cls.data` avant de l'utiliser

### Formatage incorrect

1. Vérifier que `format_programme_value()` est appelée avec le bon paramètre `is_fake`
2. Vérifier que le flag `_is_fake` ou `_source` est correctement défini
3. Vérifier le mode ("brouillon" vs "final")

### Erreurs de pagination

1. Pour Canvas : Vérifier que `next_page` est correctement incrémenté
2. Pour SimpleDocTemplate : Vérifier que les éléments sont bien ajoutés à `story`

### Données factices affichées en rouge

1. Vérifier que le flag `_is_fake` est bien défini
2. Vérifier que `format_programme_value()` utilise le bon flag
3. Vérifier la logique de détection dans la fonction concernée

---

## Conclusion

Cette documentation couvre tous les aspects du système de génération de rapport. Pour toute modification :

1. **Identifier la fonction concernée** dans cette documentation
2. **Comprendre la source des données** (tables DB)
3. **Suivre le guide de modification** approprié
4. **Tester en mode brouillon et final**

Les logs sont très détaillés et indiquent clairement :
- Quelles données sont chargées depuis la DB
- Quelles données sont factices
- Les numéros de pages générées
- Les erreurs éventuelles

