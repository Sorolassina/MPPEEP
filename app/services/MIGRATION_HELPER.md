# Aide à la Migration - Complétion Automatique des TODO

Ce document liste tous les TODO restants avec leurs emplacements exacts pour faciliter la migration.

---

## TODO Restants par Classe

### 1. RAPDataLoader (5 méthodes)

#### `load_budget_data()` - Ligne ~1746
- **Fichier original** : ligne 12273-12662 (~390 lignes)
- **Méthode** : Charge les programmes, budgets, actions, activités depuis SigobeExecution
- **Priorité** : Critique
- **Note** : Très volumineuse, charger les programmes avec leurs budgets et données de performance

#### `get_investissement_data()` - Ligne ~1781
- **Fichier original** : ligne 6645-7054 (~409 lignes)
- **Méthode** : Charge les projets d'investissement depuis SigobeExecution
- **Priorité** : Haute
- **Note** : Groupe par projet et accumule les montants

#### `get_activites_majeures()` - Ligne ~1810
- **Fichier original** : ligne 7055-7118 (~63 lignes)
- **Méthode** : Charge les activités majeures par taux d'exécution
- **Priorité** : Haute
- **Note** : Relativement simple, filtrer par taux d'exécution > 0

#### `get_indicateurs_performance_data()` - Ligne ~1842
- **Fichier original** : ligne 7119-7637 (~518 lignes)
- **Méthode** : Charge les indicateurs avec valeurs historiques depuis IndicateurPerformance
- **Priorité** : Haute
- **Note** : Très volumineuse, charge hiérarchie OS -> Indicateurs avec valeurs par année

#### `get_effectifs_data()` - Ligne ~1872
- **Fichier original** : ligne 7638-7976 (~338 lignes)
- **Méthode** : Charge les effectifs par catégorie depuis AgentComplet
- **Priorité** : Haute
- **Note** : Volumineuse, charge effectifs pour N-1 et N par catégorie

---

### 2. RAPLayoutDrawer (6 méthodes)

#### `draw_background_shapes()` - Ligne ~2072
- **Fichier original** : Rechercher dans les méthodes de couverture
- **Méthode** : Dessine les formes de fond décoratives
- **Priorité** : Moyenne

#### `draw_header()` - Ligne ~2097
- **Fichier original** : Rechercher dans les méthodes de couverture
- **Méthode** : Dessine l'en-tête avec logo et ministère
- **Priorité** : Haute

#### `draw_cover_block()` - Ligne ~2123
- **Fichier original** : Rechercher dans les méthodes de couverture
- **Méthode** : Dessine un bloc de couverture
- **Priorité** : Moyenne

#### `draw_footer()` - Ligne ~2145
- **Fichier original** : ligne 1118-1250 (~132 lignes)
- **Méthode** : Dessine le footer avec numéro de page
- **Priorité** : Haute

#### `draw_page_footer()` - Ligne ~2180
- **Fichier original** : ligne 1118-1250 (~132 lignes)
- **Méthode** : Dessine le footer pour une page spécifique
- **Priorité** : Haute

#### `_resolve_asset_path()` - Ligne ~2207
- **Fichier original** : Rechercher méthodes de résolution de chemin
- **Méthode** : Résout le chemin d'un asset (logo, etc.)
- **Priorité** : Moyenne

---

### 3. RAPContentDrawer (8 méthodes)

#### `draw_table_of_contents()` - Ligne ~2275
- **Fichier original** : ligne 1700-2488 (~788 lignes)
- **Méthode** : Dessine la table des matières complète
- **Priorité** : Critique
- **Note** : Très volumineuse, gère la numérotation des pages

#### `draw_liste_tableaux()` - Ligne ~2307
- **Fichier original** : ligne 1098-1200 (~102 lignes)
- **Méthode** : Dessine la liste des tableaux
- **Priorité** : Haute

#### `draw_liste_graphiques()` - Ligne ~2339
- **Fichier original** : ligne 1401-1500 (~99 lignes)
- **Méthode** : Dessine la liste des graphiques
- **Priorité** : Haute

#### `draw_liste_sigles_abreviations()` - Ligne ~2370
- **Fichier original** : ligne 1694-1728 (~34 lignes)
- **Méthode** : Dessine la liste des sigles et abréviations
- **Priorité** : Moyenne

#### `draw_introduction_generale()` - Ligne ~2407
- **Fichier original** : ligne 2700-3700 (~1000 lignes) - À vérifier
- **Méthode** : Dessine l'introduction générale complète
- **Priorité** : Critique
- **Note** : Très volumineuse

#### `draw_partie_i_ministere()` - Ligne ~2446
- **Fichier original** : ligne 3700-6000 (~2300 lignes) - À vérifier
- **Méthode** : Dessine la Partie I complète (Le Ministère)
- **Priorité** : Critique
- **Note** : Très très volumineuse

#### `draw_conclusion_generale()` - Ligne ~2485
- **Fichier original** : ligne 9663-9813 (~150 lignes)
- **Méthode** : Dessine la conclusion générale
- **Priorité** : Haute

#### `_build_toc_items_from_pdf_or_positions()` - Ligne ~2519
- **Fichier original** : Rechercher dans les méthodes de sommaire
- **Méthode** : Construit les éléments du sommaire depuis le PDF ou les positions
- **Priorité** : Haute

---

### 4. RAPTableDrawer (3 méthodes)

#### `create_investissement_table()` - Ligne ~2593
- **Fichier original** : ligne 6789-7400 (~611 lignes)
- **Méthode** : Crée le tableau d'investissement complexe
- **Priorité** : Haute
- **Note** : Très volumineuse, structure complexe avec sous-lignes

#### `create_indicateurs_table()` - Ligne ~2627
- **Fichier original** : ligne 7402-7750 (~348 lignes)
- **Méthode** : Crée le tableau d'indicateurs de performance
- **Priorité** : Haute
- **Note** : Volumineuse, tableau complexe avec OS et indicateurs

#### `create_effectifs_table()` - Ligne ~2663
- **Fichier original** : ligne 7750-7977 (~227 lignes)
- **Méthode** : Crée le tableau d'effectifs
- **Priorité** : Haute

---

### 5. RAPChartGenerator (5 méthodes)

#### `create_pie_chart_budget()` - Ligne ~2715
- **Fichier original** : ligne 5771-6347 (~576 lignes)
- **Méthode** : Crée le graphique en camembert pour le budget ministère
- **Priorité** : Haute
- **Note** : Volumineuse

#### `create_pie_chart_programme()` - Ligne ~2763
- **Fichier original** : ligne 6347-6437 (~90 lignes)
- **Méthode** : Crée le graphique en camembert pour un programme
- **Priorité** : Haute

#### `create_bar_chart_execution_rates()` - Ligne ~2794
- **Fichier original** : ligne 6437-6540 (~103 lignes)
- **Méthode** : Crée le graphique en barres pour les taux d'exécution
- **Priorité** : Haute

#### `create_bar_chart_effectifs()` - Ligne ~2827
- **Fichier original** : ligne 7977-8073 (~96 lignes)
- **Méthode** : Crée le graphique en barres pour les effectifs
- **Priorité** : Haute

#### `create_indicateur_evolution_chart()` - Ligne ~2872
- **Fichier original** : ligne 6540-6788 (~248 lignes)
- **Méthode** : Crée le graphique d'évolution d'un indicateur
- **Priorité** : Haute
- **Note** : Volumineuse

---

### 6. RAPProgramSectionDrawer (1 méthode)

#### `draw_partie_programme()` - Ligne ~2920
- **Fichier original** : ligne 8073-11434 (~3361 lignes)
- **Méthode** : Génère la partie complète d'un programme avec toutes ses sections
- **Priorité** : Critique
- **Note** : LA PLUS VOLUMINEUSE - Contient toute la logique de génération des sections par programme

---

### 7. RAPPDFGenerator (1 méthode)

#### `generate_pdf()` - Ligne ~2960
- **Fichier original** : ligne 12665-13277 (~612 lignes)
- **Méthode** : Orchestrateur principal qui génère le PDF complet
- **Priorité** : Critique
- **Note** : Orchestrateur - Appelle toutes les autres classes

---

## Stratégie de Migration Recommandée

### Phase 1 : Méthodes Courtes (< 150 lignes)
1. `get_activites_majeures()` (~63 lignes)
2. `draw_liste_tableaux()` (~102 lignes)
3. `draw_liste_graphiques()` (~99 lignes)
4. `draw_liste_sigles_abreviations()` (~34 lignes)
5. `create_pie_chart_programme()` (~90 lignes)
6. `create_bar_chart_execution_rates()` (~103 lignes)
7. `create_bar_chart_effectifs()` (~96 lignes)
8. `draw_conclusion_generale()` (~150 lignes)

### Phase 2 : Méthodes Moyennes (150-400 lignes)
1. `get_effectifs_data()` (~338 lignes)
2. `get_investissement_data()` (~409 lignes)
3. `create_effectifs_table()` (~227 lignes)
4. `create_indicateur_evolution_chart()` (~248 lignes)

### Phase 3 : Méthodes Volumineuses (400-800 lignes)
1. `load_budget_data()` (~390 lignes)
2. `get_indicateurs_performance_data()` (~518 lignes)
3. `create_investissement_table()` (~611 lignes)
4. `generate_pdf()` (~612 lignes)
5. `create_pie_chart_budget()` (~576 lignes)
6. `create_indicateurs_table()` (~348 lignes)

### Phase 4 : Méthodes Très Volumineuses (> 800 lignes)
1. `draw_table_of_contents()` (~788 lignes)
2. `draw_introduction_generale()` (~1000 lignes)
3. `draw_partie_i_ministere()` (~2300 lignes)
4. `draw_partie_programme()` (~3361 lignes) - LA PLUS GRANDE

---

## Instructions de Migration

Pour chaque méthode :

1. **Localiser dans le fichier original** :
   ```bash
   # Ouvrir rapport_annuel_performance_service_simpledoc.py
   # Aller à la ligne indiquée
   ```

2. **Identifier la méthode** :
   - Chercher `def _method_name(` ou `@classmethod def _method_name(`
   - Noter les lignes de début et de fin

3. **Copier l'implémentation** :
   - Copier tout le corps de la méthode
   - Inclure les imports nécessaires

4. **Adapter au contexte modulaire** :
   - Changer `cls._method()` → `cls.method()` (méthodes publiques)
   - Utiliser les méthodes des classes parentes via héritage
   - Conserver la même logique métier

5. **Tester** :
   - Vérifier que les imports sont corrects
   - S'assurer que les références aux autres méthodes sont valides

---

## Statistiques Globales

- **Total TODO restants** : 30
- **Lignes estimées à migrer** : ~12,000 lignes
- **Méthodes complétées** : 10/40 (25%)
- **Travail restant** : 75%

---

**Dernière mise à jour** : 2024-12-19

