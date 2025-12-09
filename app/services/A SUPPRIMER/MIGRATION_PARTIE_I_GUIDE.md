# Guide de Migration pour draw_partie_i_ministere

## Remplacements à effectuer dans le code original

### Appels de méthodes à adapter:

1. `cls._format_db_data(` → `RAPStylingManager.format_db_data(`
2. `cls._format_fake_data(` → `RAPStylingManager.format_fake_data(`
3. `cls._get_sigle_ministere()` → `RAPStylingManager.get_sigle_ministere()`
4. `cls._should_use_fake_data()` → `RAPBaseGenerator.should_use_fake_data()`
5. `cls._get_next_tableau_numero()` → `RAPBaseGenerator.get_next_tableau_numero()`
6. `cls._get_next_figure_numero()` → `RAPBaseGenerator.get_next_figure_numero()`
7. `cls._create_pie_chart_budget(` → `RAPChartGenerator.create_pie_chart_budget(`
8. `cls._draw_page_footer(` → `RAPLayoutDrawer.draw_page_footer(`
9. `cls._db_session` → `RAPBaseGenerator._db_session`
10. `cls._render_multipage_story(` → `cls._render_multipage_story(` (reste identique - même classe)

### Localisation:
- **Fichier original**: `rapport_annuel_performance_service_simpledoc.py`
- **Lignes**: 3648-5768 (~2120 lignes)
- **Fichier destination**: `rapport_annuel_performance_generator_modular.py`
- **Méthode**: `RAPContentDrawer.draw_partie_i_ministere()`
- **Ligne TODO**: ~5343

### Structure de la méthode:
1. Initialisation (marges, styles)
2. Chargement des données
3. Section I.1. Architecture programmatique (avec Tableau 1)
4. Section I.2. Politique ministérielle (avec tableau)
5. Section II. Performance générale (avec Tableaux 2 et 3)
6. Section III. Financement global (avec Tableau 4 et Figure 1)

### Notes importantes:
- La méthode utilise `_render_multipage_story` qui reste dans la même classe (RAPContentDrawer)
- Tous les autres appels doivent être adaptés vers les classes spécialisées
- La méthode retourne le numéro de page final

