# Migration Complète - draw_partie_i_ministere

## Statut: 🚧 EN COURS

Cette méthode de ~2120 lignes nécessite une migration complète avec tous les remplacements.

Vu la longueur, la méthode complète adaptée sera créée directement dans le fichier modulaire.

## Tous les remplacements nécessaires:

```python
# Formatage
cls._format_db_data(          → RAPStylingManager.format_db_data(
cls._format_fake_data(        → RAPStylingManager.format_fake_data(
cls._get_sigle_ministere()    → RAPStylingManager.get_sigle_ministere()

# Base generator
cls._should_use_fake_data()   → RAPBaseGenerator.should_use_fake_data()
cls._get_next_tableau_numero() → RAPBaseGenerator.get_next_tableau_numero()
cls._get_next_figure_numero()  → RAPBaseGenerator.get_next_figure_numero()
cls._db_session                → RAPBaseGenerator._db_session

# Charts
cls._create_pie_chart_budget(  → RAPChartGenerator.create_pie_chart_budget(

# Layout
cls._draw_page_footer(         → RAPLayoutDrawer.draw_page_footer(

# Reste identique
cls._render_multipage_story(   → cls._render_multipage_story( (même classe)
```

## Prochaines étapes:

1. ✅ Création du guide de remplacements
2. ⏳ Migration directe du code complet dans modular.py
3. ⏳ Vérification des remplacements
4. ⏳ Tests

## Note:

La méthode complète sera insérée directement en remplaçant le TODO à la ligne ~5343 de `rapport_annuel_performance_generator_modular.py`.

