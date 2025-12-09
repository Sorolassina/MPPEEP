# Architecture Modulaire du Générateur de Rapport Annuel de Performance

## Vue d'ensemble

Le générateur de rapport a été divisé en plusieurs sous-classes spécialisées pour améliorer la maintenabilité et la réutilisabilité. Chaque classe a une responsabilité unique et bien définie.

## Structure des Classes

```
RAPBaseGenerator (Classe de base)
├── RAPPageManager (Gestion des pages)
├── RAPStylingManager (Formatage et styles)
├── RAPDataLoader (Chargement des données)
├── RAPLayoutDrawer (Éléments de layout)
├── RAPContentDrawer (Contenu principal)
├── RAPTableDrawer (Gestion des tableaux)
├── RAPChartGenerator (Génération des graphiques)
├── RAPProgramSectionDrawer (Sections par programme)
└── RAPPDFGenerator (Orchestrateur principal)
```

## Détail des Classes

### 1. RAPBaseGenerator
**Responsabilité** : Classe de base avec constantes et utilitaires communs

**Contenu** :
- Constantes de couleurs (PRIMARY_GREEN, PRIMARY_ORANGE, etc.)
- Variables d'état partagées (_db_session, data, _page_positions, etc.)
- Compteurs (_tableau_counter, _figure_counter)
- Méthodes utilitaires :
  - `number_to_roman()` : Conversion en chiffres romains
  - `normalize_text_for_search()` : Normalisation de texte
  - `get_next_tableau_numero()` : Numérotation des tableaux
  - `get_next_figure_numero()` : Numérotation des figures
  - `reset_tableau_counter()` / `reset_figure_counter()` : Réinitialisation

### 2. RAPPageManager (hérite de RAPBaseGenerator)
**Responsabilité** : Gestion des pages (numérotation, positions, recherche)

**Méthodes principales** :
- `register_page_position(key, page_number)` : Enregistrer une position de page
- `get_page_position(key, default=0)` : Récupérer une position de page
- `find_text_in_pdf(pdf_reader, search_text, exact_match=False)` : Rechercher du texte dans le PDF
- `find_text_in_pdf_with_range(pdf_reader, search_text, start_page, end_page)` : Recherche dans une plage
- `find_all_toc_pages(pdf_reader, nb_pages_sommaire=0)` : Trouver toutes les pages du sommaire
- `find_tableaux_and_graphiques_pages(pdf_reader)` : Trouver les pages des tableaux et figures
- `extract_title_from_page_text(page_text, numero, type_label)` : Extraire un titre d'une page
- `reset_page_tracking()` : Réinitialiser le suivi des pages

**Origine des méthodes** :
- `_register_page_position()` → `register_page_position()`
- `_get_page_position()` → `get_page_position()`
- `_find_text_in_pdf()` → `find_text_in_pdf()`
- `_find_text_in_pdf_with_range()` → `find_text_in_pdf_with_range()`
- `_find_all_toc_pages()` → `find_all_toc_pages()`
- `_find_tableaux_and_graphiques_pages()` → `find_tableaux_and_graphiques_pages()`
- `_extract_title_from_page_text()` → `extract_title_from_page_text()`
- `_normalize_text_for_search()` → Déjà dans RAPBaseGenerator

### 3. RAPStylingManager (hérite de RAPBaseGenerator)
**Responsabilité** : Formatage et styling des données

**Méthodes principales** :
- `format_db_data(value)` : Formater une valeur provenant de la DB (rouge)
- `format_fake_data(value)` : Formater une valeur factice (violet italique)
- `format_programme_value(value, is_fake)` : Formater selon la source
- `format_partie_value(value, is_fake)` : Formater pour la partie I
- `get_color_for_source(source)` : Obtenir la couleur selon la source
- `format_fcfa(amount)` : Formater un montant en FCFA

**Origine des méthodes** :
- `_format_db_data()` → `format_db_data()`
- `_format_fake_data()` → `format_fake_data()`
- `_format_programme_value()` → `format_programme_value()`
- `_format_partie_value()` → `format_partie_value()`
- `_get_color_for_source()` → `get_color_for_source()`
- `_format_fcfa()` → `format_fcfa()`

### 4. RAPDataLoader (hérite de RAPBaseGenerator)
**Responsabilité** : Chargement des données depuis la base de données

**Méthodes principales** :
- `load_system_settings_data(session)` : Charger les paramètres système
- `load_budget_data(session, annee)` : Charger les données budgétaires
- `get_sigle_ministere()` : Obtenir le sigle du ministère
- `get_investissement_data(numero, titre, annee, session)` : Données d'investissement
- `get_activites_majeures(numero, titre, annee, session)` : Activités majeures
- `get_indicateurs_performance_data(numero, titre, annee, session)` : Indicateurs de performance
- `get_effectifs_data(numero, titre, annee, session)` : Données d'effectifs

**Origine des méthodes** :
- `load_system_settings_data()` → `load_system_settings_data()`
- `load_budget_data()` → `load_budget_data()`
- `_get_sigle_ministere()` → `get_sigle_ministere()`
- `_get_investissement_data()` → `get_investissement_data()`
- `_get_activites_majeures()` → `get_activites_majeures()`
- `_get_indicateurs_performance_data()` → `get_indicateurs_performance_data()`
- `_get_effectifs_data()` → `get_effectifs_data()`

### 5. RAPLayoutDrawer (hérite de RAPBaseGenerator)
**Responsabilité** : Éléments de layout (cover, footer, header, background)

**Méthodes principales** :
- `draw_cover_page(pdf, width, height)` : Page de couverture
- `draw_cover_block(pdf, width, height)` : Bloc de couverture
- `draw_footer(pdf, width, height, page_num)` : Pied de page
- `draw_header(pdf, width, height)` : En-tête
- `draw_page_footer(pdf, width, height, page_num)` : Footer avec numéro de page
- `draw_background_shapes(pdf, width, height)` : Formes de fond

**Origine des méthodes** :
- `_draw_cover_block()` → `draw_cover_page()` + `draw_cover_block()`
- `_draw_footer()` → `draw_footer()`
- `_draw_header()` → `draw_header()`
- `_draw_page_footer()` → `draw_page_footer()`
- `_draw_background_shapes()` → `draw_background_shapes()`

### 6. RAPContentDrawer (hérite de RAPBaseGenerator)
**Responsabilité** : Contenu principal du rapport (hors programmes)

**Méthodes principales** :
- `draw_table_of_contents(pdf, width, height, pdf_reader, nb_pages_sommaire)` : Table des matières
- `draw_liste_tableaux(pdf, width, height, start_page)` : Liste des tableaux
- `draw_liste_graphiques(pdf, width, height, start_page)` : Liste des graphiques
- `draw_liste_sigles_abreviations(pdf, width, height, start_page)` : Liste des sigles
- `draw_introduction_generale(pdf, width, height, start_page)` : Introduction générale
- `draw_partie_i_ministere(pdf, width, height, start_page)` : Partie I - Le Ministère
- `draw_conclusion_generale(start_page, session)` : Conclusion générale

**Origine des méthodes** :
- `_draw_table_of_contents()` → `draw_table_of_contents()`
- `_draw_liste_tableaux()` → `draw_liste_tableaux()`
- `_draw_liste_graphiques()` → `draw_liste_graphiques()`
- `_draw_liste_sigles_abreviations()` → `draw_liste_sigles_abreviations()`
- `_draw_introduction_generale()` → `draw_introduction_generale()`
- `_draw_partie_i_ministere()` → `draw_partie_i_ministere()`
- `_draw_conclusion_generale()` → `draw_conclusion_generale()`

### 7. RAPTableDrawer (hérite de RAPBaseGenerator)
**Responsabilité** : Gestion et création des tableaux

**Méthodes principales** :
- `create_investissement_table(projects, available_width, format_fcfa, annee, is_fake, format_programme_value)` : Tableau d'investissements
- `create_indicateurs_table(indicateurs_data, available_width, annee, format_programme_value)` : Tableau d'indicateurs
- `create_effectifs_table(effectifs_data, available_width, annee, is_fake, format_programme_value)` : Tableau d'effectifs
- `create_table(table_data, col_widths, repeat_rows=1)` : Créer un tableau générique

**Origine des méthodes** :
- `_create_investissement_table()` → `create_investissement_table()`
- `_create_indicateurs_table()` → `create_indicateurs_table()`
- `_create_effectifs_table()` → `create_effectifs_table()`

### 8. RAPChartGenerator (hérite de RAPBaseGenerator)
**Responsabilité** : Génération des graphiques (pie, bar, line)

**Méthodes principales** :
- `create_pie_chart_budget(personnel, pct_personnel, biens, pct_biens, transferts, pct_transferts, investissements, pct_investissements, titre_ministere)` : Camembert budget ministère
- `create_pie_chart_programme(personnel, pct_personnel, biens, pct_biens, transferts, pct_transferts, investissements, pct_investissements, titre_programme)` : Camembert budget programme
- `create_bar_chart_execution_rates(bar_chart_data, annee_precedente, annee)` : Graphique en barres des taux d'exécution
- `create_bar_chart_effectifs(effectifs_data, annee_precedente, annee)` : Graphique en barres des effectifs
- `create_indicateur_evolution_chart(indicateur_nom, annee_n_3, annee_n_2, annee_n_1, annee, valeur_n_3, valeur_n_2, valeur_n_1, valeur_n, cible)` : Graphique d'évolution d'un indicateur

**Origine des méthodes** :
- `_create_pie_chart_budget()` → `create_pie_chart_budget()`
- `_create_pie_chart_programme()` → `create_pie_chart_programme()`
- `_create_bar_chart_execution_rates()` → `create_bar_chart_execution_rates()`
- `_create_bar_chart_effectifs()` → `create_bar_chart_effectifs()`
- `_create_indicateur_evolution_chart()` → `create_indicateur_evolution_chart()`

### 9. RAPProgramSectionDrawer (hérite de RAPBaseGenerator)
**Responsabilité** : Génération des sections par programme

**Méthodes principales** :
- `draw_partie_programme(programme, start_page, session)` : Dessiner toute la partie d'un programme
  - Introduction du programme
  - Section I : Présentation de la stratégie
  - Section II : Réalisations
  - Section III : Performance (avec tableaux et graphiques)
  - Section IV : Perspectives (si programme 2)
  - Conclusion du programme

**Origine des méthodes** :
- `_draw_partie_programme_simpledoc()` → `draw_partie_programme()`

### 10. RAPPDFGenerator (hérite de toutes les classes)
**Responsabilité** : Orchestrateur principal de la génération du PDF

**Méthode principale** :
- `generate_pdf(data, session)` : Méthode principale qui orchestre toute la génération

**Flux de génération** :
1. Initialisation des compteurs et variables
2. Chargement des données (via RAPDataLoader)
3. Fusion des données (DB + formulaire)
4. Génération de la couverture (via RAPLayoutDrawer)
5. Génération du contenu (via RAPContentDrawer)
6. Génération des sections par programme (via RAPProgramSectionDrawer)
7. Génération de la conclusion (via RAPContentDrawer)
8. Fusion des PDFs et ajout du sommaire
9. Retour du PDF final

**Origine des méthodes** :
- `generate_pdf()` → `generate_pdf()` (orchestration de toutes les autres classes)

## Flowables Personnalisés

### PageMarker
Flowable invisible qui enregistre la page où il est rendu.

### ParagraphWithMarker
Combinaison d'un Paragraph avec un PageMarker.

### TableTitleFlowable
Flowable pour gérer automatiquement la numérotation des tableaux.

## Migration du Code

### Étape 1 : Créer les classes de base
- [x] RAPBaseGenerator avec constantes et utilitaires
- [x] RAPPageManager avec gestion des pages
- [ ] RAPStylingManager avec formatage
- [ ] RAPDataLoader avec chargement des données

### Étape 2 : Créer les classes de dessin
- [ ] RAPLayoutDrawer pour le layout
- [ ] RAPContentDrawer pour le contenu
- [ ] RAPTableDrawer pour les tableaux
- [ ] RAPChartGenerator pour les graphiques
- [ ] RAPProgramSectionDrawer pour les programmes

### Étape 3 : Créer l'orchestrateur
- [ ] RAPPDFGenerator qui utilise toutes les autres classes

### Étape 4 : Tests et validation
- [ ] Tester chaque classe indépendamment
- [ ] Tester l'intégration complète
- [ ] Valider que le PDF généré est identique

## Avantages de cette Architecture

1. **Maintenabilité** : Chaque classe a une responsabilité unique et claire
2. **Réutilisabilité** : Les classes peuvent être réutilisées pour d'autres rapports
3. **Testabilité** : Chaque classe peut être testée indépendamment
4. **Extensibilité** : Facile d'ajouter de nouvelles fonctionnalités
5. **Documentation** : Chaque classe est bien documentée avec ses responsabilités

## Utilisation

```python
from app.services.rapport_annuel_performance_generator_modular import RAPPDFGenerator

# Générer le rapport
pdf_buffer = RAPPDFGenerator.generate_pdf(data, session)

# Ou utiliser les classes individuelles
from app.services.rapport_annuel_performance_generator_modular import RAPChartGenerator

chart = RAPChartGenerator.create_pie_chart_budget(...)
```

