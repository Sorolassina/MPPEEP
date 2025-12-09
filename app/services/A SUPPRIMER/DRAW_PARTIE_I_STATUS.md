# État de la Migration - draw_partie_i_ministere

## Statut: ⚠️ EN COURS

**Méthode**: `RAPContentDrawer.draw_partie_i_ministere()`  
**Localisation originale**: `rapport_annuel_performance_service_simpledoc.py` lignes 3648-5768  
**Longueur**: ~2120 lignes  
**Complexité**: ⭐⭐⭐⭐⭐ (Très élevée)

## Remplacements à effectuer

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
10. `cls._render_multipage_story(` → `cls._render_multipage_story(` (reste identique)

## Structure de la méthode

La méthode génère la Partie I du rapport qui inclut:

1. **I. PRÉSENTATION GÉNÉRALE DU MINISTÈRE**
   - I.1. Architecture programmatique (avec Tableau 1)
   - I.2. Politique ministérielle (avec tableau)

2. **II. PERFORMANCE GÉNÉRALE DU MINISTÈRE**
   - II.1. Architecture du cadre de performance (avec Tableau 2)
   - II.2. Bilan des données globales (avec Tableau 3)

3. **III. FINANCEMENT GLOBAL DU MINISTÈRE**
   - Paragraphes introductifs
   - Tableau 4: Exécution du budget
   - Figure 1: Répartition par nature de dépenses

## Prochaines étapes

1. ✅ Créer le guide de migration
2. ⏳ Extraire le code original complet
3. ⏳ Appliquer tous les remplacements
4. ⏳ Insérer dans `rapport_annuel_performance_generator_modular.py`
5. ⏳ Vérifier et tester

## Notes importantes

- La méthode utilise `_render_multipage_story` qui reste dans la même classe
- Beaucoup de logique conditionnelle pour les données factices vs DB
- Plusieurs tableaux complexes avec styles personnalisés
- Génération de graphiques (camembert)

