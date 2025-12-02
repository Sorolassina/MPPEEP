# Guide de Complétion des TODO - Architecture Modulaire RAP

Ce document liste tous les TODO à compléter dans `rapport_annuel_performance_generator_modular.py` avec leurs emplacements dans le fichier original.

## Structure du Document

Chaque section correspond à une classe modulaire. Les méthodes sont listées avec :
- **Ligne dans modular.py** : Où se trouve le TODO
- **Ligne dans simpledoc.py** : Où trouver l'implémentation originale
- **Description** : Ce que fait la méthode
- **Statut** : Complété / À compléter

---

## 1. RAPPageManager

### ✅ Complétées
- `find_text_in_pdf_with_range()` - Complété
- `extract_title_from_page_text()` - Complété  
- `find_tableaux_and_graphiques_pages()` - Complété

### ⏳ À Compléter

#### `find_all_toc_pages(pdf_reader, nb_pages_sommaire=0)`
- **Ligne modular.py** : ~650
- **Ligne simpledoc.py** : 481-775
- **Description** : Trouve toutes les pages du sommaire en parcourant le PDF une seule fois
- **Complexité** : Haute (~300 lignes)
- **Priorité** : Critique

---

## 2. RAPDataLoader

### ⏳ À Compléter

#### `load_system_settings_data(session)`
- **Ligne modular.py** : ~826
- **Ligne simpledoc.py** : ~1200-2000 (méthodes de chargement)
- **Description** : Charge SystemSettings et RapData depuis la base de données
- **Priorité** : Critique

#### `load_budget_data(session, annee)`
- **Ligne modular.py** : ~868
- **Ligne simpledoc.py** : Rechercher méthodes de chargement budget
- **Description** : Charge les données budgétaires depuis SigobeExecution
- **Priorité** : Critique

#### `get_investissement_data(programme_id, annee)`
- **Ligne modular.py** : ~903
- **Description** : Charge les données d'investissement
- **Priorité** : Haute

#### `get_activites_majeures(programme_id, annee)`
- **Ligne modular.py** : ~932
- **Description** : Charge les activités majeures d'un programme
- **Priorité** : Haute

#### `get_indicateurs_performance_data(programme_id, annee)`
- **Ligne modular.py** : ~964
- **Description** : Charge les indicateurs de performance
- **Priorité** : Haute

#### `get_effectifs_data(programme_id, annee)`
- **Ligne modular.py** : ~994
- **Description** : Charge les données d'effectifs
- **Priorité** : Haute

#### `load_performance_hierarchy_from_db(session)`
- **Ligne modular.py** : ~1031
- **Description** : Charge la hiérarchie de performance complète
- **Priorité** : Haute

---

## 3. RAPLayoutDrawer

### ⏳ À Compléter

#### `draw_background_shapes(pdf, width, height)`
- **Ligne modular.py** : ~1102
- **Ligne simpledoc.py** : ~2500-2600
- **Description** : Dessine les formes de fond décoratives
- **Priorité** : Moyenne

#### `draw_header(pdf, ministere, logo_path, width)`
- **Ligne modular.py** : ~1127
- **Ligne simpledoc.py** : ~2600-2700
- **Description** : Dessine l'en-tête avec logo et ministère
- **Priorité** : Haute

#### `draw_cover_block(pdf, x, y, width, height, content)`
- **Ligne modular.py** : ~1153
- **Description** : Dessine un bloc de couverture
- **Priorité** : Moyenne

#### `draw_footer(pdf, page_number, width, footer_margin, footer_height)`
- **Ligne modular.py** : ~1175
- **Ligne simpledoc.py** : ~1118-1250
- **Description** : Dessine le footer avec numéro de page
- **Priorité** : Haute

#### `draw_page_footer(pdf, page_number, width, footer_margin, footer_height)`
- **Ligne modular.py** : ~1210
- **Ligne simpledoc.py** : ~1118-1250
- **Description** : Dessine le footer pour une page spécifique
- **Priorité** : Haute

#### `_resolve_asset_path(relative_path)`
- **Ligne modular.py** : ~1237
- **Description** : Résout le chemin d'un asset (logo, etc.)
- **Priorité** : Moyenne

---

## 4. RAPContentDrawer

### ⏳ À Compléter

#### `draw_table_of_contents(pdf, toc_items, width, height, start_y)`
- **Ligne modular.py** : ~1305
- **Ligne simpledoc.py** : ~2000-2500
- **Description** : Dessine la table des matières complète
- **Complexité** : Haute
- **Priorité** : Critique

#### `draw_liste_tableaux(pdf, tableaux_list, width, height, start_y)`
- **Ligne modular.py** : ~1337
- **Ligne simpledoc.py** : ~1098-1200
- **Description** : Dessine la liste des tableaux
- **Priorité** : Haute

#### `draw_liste_graphiques(pdf, graphiques_list, width, height, start_y)`
- **Ligne modular.py** : ~1369
- **Ligne simpledoc.py** : ~1401-1500
- **Description** : Dessine la liste des graphiques
- **Priorité** : Haute

#### `draw_liste_sigles_abreviations(pdf, sigles_list, width, height, start_y)`
- **Ligne modular.py** : ~1400
- **Ligne simpledoc.py** : ~1694-1728
- **Description** : Dessine la liste des sigles et abréviations
- **Priorité** : Moyenne

#### `draw_introduction_generale(pdf, intro_data, width, height, start_y)`
- **Ligne modular.py** : ~1437
- **Ligne simpledoc.py** : ~3000-4000
- **Description** : Dessine l'introduction générale complète
- **Complexité** : Haute
- **Priorité** : Critique

#### `draw_partie_i_ministere(pdf, partie_data, width, height, start_y)`
- **Ligne modular.py** : ~1476
- **Ligne simpledoc.py** : ~4000-6000
- **Description** : Dessine la Partie I complète (Le Ministère)
- **Complexité** : Très Haute
- **Priorité** : Critique

#### `draw_conclusion_generale(pdf, conclusion_data, width, height, start_y)`
- **Ligne modular.py** : ~1509
- **Ligne simpledoc.py** : ~9663-9813
- **Description** : Dessine la conclusion générale
- **Priorité** : Haute

#### `_build_toc_items_from_pdf_or_positions(pdf_reader_complet, pages_found, programmes)`
- **Ligne modular.py** : ~1543
- **Description** : Construit les éléments du sommaire depuis le PDF ou les positions
- **Priorité** : Haute

---

## 5. RAPTableDrawer

### ⏳ À Compléter

#### `create_investissement_table(...)`
- **Ligne modular.py** : ~1603
- **Ligne simpledoc.py** : 6789-7400
- **Description** : Crée le tableau d'investissement complexe
- **Complexité** : Très Haute (~600 lignes)
- **Priorité** : Haute

#### `create_indicateurs_table(...)`
- **Ligne modular.py** : ~1637
- **Ligne simpledoc.py** : 7402-7750
- **Description** : Crée le tableau d'indicateurs de performance
- **Complexité** : Haute (~350 lignes)
- **Priorité** : Haute

#### `create_effectifs_table(...)`
- **Ligne modular.py** : ~1673
- **Ligne simpledoc.py** : 7750-7977
- **Description** : Crée le tableau d'effectifs
- **Complexité** : Moyenne (~200 lignes)
- **Priorité** : Haute

---

## 6. RAPChartGenerator

### ⏳ À Compléter

#### `create_pie_chart_budget(...)`
- **Ligne modular.py** : ~1735
- **Ligne simpledoc.py** : 5771-6347
- **Description** : Crée le graphique en camembert pour le budget ministère
- **Complexité** : Haute
- **Priorité** : Haute

#### `create_pie_chart_programme(...)`
- **Ligne modular.py** : ~1774
- **Ligne simpledoc.py** : 6347-6437
- **Description** : Crée le graphique en camembert pour un programme
- **Priorité** : Haute

#### `create_bar_chart_execution_rates(...)`
- **Ligne modular.py** : ~1803
- **Ligne simpledoc.py** : 6437-6540
- **Description** : Crée le graphique en barres pour les taux d'exécution
- **Priorité** : Haute

#### `create_bar_chart_effectifs(...)`
- **Ligne modular.py** : ~1836
- **Ligne simpledoc.py** : 7977-8073
- **Description** : Crée le graphique en barres pour les effectifs
- **Priorité** : Haute

#### `create_indicateur_evolution_chart(...)`
- **Ligne modular.py** : ~1881
- **Ligne simpledoc.py** : 6540-6788
- **Description** : Crée le graphique d'évolution d'un indicateur
- **Priorité** : Haute

---

## 7. RAPProgramSectionDrawer

### ⏳ À Compléter

#### `draw_partie_programme(programme, start_page, session)`
- **Ligne modular.py** : ~1950
- **Ligne simpledoc.py** : 8073-11434
- **Description** : Génère la partie complète d'un programme avec toutes ses sections
- **Complexité** : Très Très Haute (~3300 lignes)
- **Priorité** : Critique

Cette méthode est la plus volumineuse et contient toute la logique de génération des sections par programme :
- Introduction du programme
- Section I : Présentation de la stratégie
- Section II : Réalisations
- Section III : Performance
- Section IV : Perspectives (si programme 2)
- Conclusion du programme

---

## 8. RAPPDFGenerator

### ⏳ À Compléter

#### `generate_pdf(data, session)`
- **Ligne modular.py** : ~2060
- **Ligne simpledoc.py** : 12665-13277
- **Description** : Orchestrateur principal qui génère le PDF complet
- **Complexité** : Très Haute (~600 lignes)
- **Priorité** : Critique

Cette méthode orchestre toute la génération :
1. Initialisation des compteurs et variables
2. Chargement des données (via RAPDataLoader)
3. Génération de la couverture (via RAPLayoutDrawer)
4. Génération du contenu (via RAPContentDrawer)
5. Génération des programmes (via RAPProgramSectionDrawer)
6. Fusion et ajout du sommaire
7. Retour du PDF final

---

## Plan de Migration Recommandé

### Phase 1 : Méthodes Critiques (Priorité Maximale)
1. ✅ `find_tableaux_and_graphiques_pages()` - Complété
2. ⏳ `find_all_toc_pages()` - À compléter
3. ⏳ `load_system_settings_data()` - À compléter
4. ⏳ `generate_pdf()` - À compléter

### Phase 2 : Layout et Contenu Principal (Priorité Haute)
5. ⏳ `draw_table_of_contents()` - À compléter
6. ⏳ `draw_introduction_generale()` - À compléter
7. ⏳ `draw_partie_i_ministere()` - À compléter
8. ⏳ `draw_footer()` / `draw_page_footer()` - À compléter

### Phase 3 : Tableaux et Graphiques (Priorité Haute)
9. ⏳ `create_investissement_table()` - À compléter
10. ⏳ `create_indicateurs_table()` - À compléter
11. ⏳ `create_effectifs_table()` - À compléter
12. ⏳ `create_pie_chart_budget()` - À compléter
13. ⏳ Tous les autres graphiques - À compléter

### Phase 4 : Programmes (Priorité Critique mais Complexe)
14. ⏳ `draw_partie_programme()` - À compléter (très volumineuse)

### Phase 5 : Méthodes Auxiliaires (Priorité Moyenne)
15. ⏳ Toutes les méthodes restantes - À compléter

---

## Comment Migrer

Pour chaque méthode :

1. **Localiser dans simpledoc.py** : Utiliser le numéro de ligne indiqué
2. **Lire l'implémentation** : Comprendre la logique et les dépendances
3. **Adapter au contexte modulaire** :
   - Remplacer les références `cls._` par les méthodes de la classe modulaire
   - Utiliser les méthodes des autres classes modulaires via l'héritage
   - Conserver la même logique métier
4. **Tester** : Vérifier que la méthode fonctionne dans le contexte modulaire
5. **Documenter** : S'assurer que les docstrings sont à jour

---

## Notes Importantes

- **Héritage multiple** : `RAPPDFGenerator` hérite de toutes les classes, donc toutes les méthodes sont accessibles
- **Variables partagées** : `cls.data`, `cls._page_positions`, etc. sont accessibles dans toutes les classes
- **Compatibilité** : L'alias `RapportAnnuelPerformanceGeneratorSimpleDoc = RAPPDFGenerator` permet la compatibilité
- **Migration progressive** : On peut migrer méthode par méthode sans casser le système existant

---

## Statistiques

- **Total de TODO** : 31
- **Complétés** : 3
- **À compléter** : 28
- **Lignes estimées à migrer** : ~10,000 lignes
- **Complexité moyenne** : Haute

---

**Date de création** : 2024-12-19
**Dernière mise à jour** : 2024-12-19

