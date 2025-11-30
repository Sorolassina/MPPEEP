# Méthodes manquantes à copier dans le service simpledoc

Voici la liste des méthodes Canvas qui doivent être copiées depuis `rapport_annuel_performance_service.py` vers `rapport_annuel_performance_service_simpledoc.py` :

## Méthodes helper Canvas (à copier EN PREMIER)

Ces méthodes sont utilisées par les autres méthodes Canvas et doivent être copiées en premier :

0. **`_determine_data_source_for_canvas`**
   - Ligne de début : 70
   - Ligne de fin : 104 (ligne avant `@classmethod def _get_color_for_source`)
   - Nombre de lignes : ~34 lignes

0. **`_get_color_for_source`**
   - Ligne de début : 104
   - Ligne de fin : 122 (ligne avant `@classmethod def _format_text_for_canvas`)
   - Nombre de lignes : ~18 lignes

0. **`_format_text_for_canvas`**
   - Ligne de début : 122
   - Ligne de fin : 155 (ligne avant `@staticmethod def _format_default_data`)
   - Nombre de lignes : ~33 lignes

## Méthodes Canvas à copier

1. **`_draw_background_shapes`**
   - Ligne de début : 984
   - Ligne de fin : 1309 (ligne avant `@classmethod def _draw_header`)
   - Nombre de lignes : ~326 lignes

2. **`_draw_header`**
   - Ligne de début : 1309
   - Ligne de fin : 1459 (ligne avant `@classmethod def _draw_cover_block`)
   - Nombre de lignes : ~151 lignes

3. **`_draw_cover_block`**
   - Ligne de début : 1459
   - Ligne de fin : 1630 (ligne avant `@classmethod def _draw_footer`)
   - Nombre de lignes : ~172 lignes

4. **`_draw_footer`**
   - Ligne de début : 1630
   - Ligne de fin : 1673 (ligne avant `@classmethod def _draw_table_of_contents`)
   - Nombre de lignes : ~44 lignes

5. **`_draw_table_of_contents`**
   - Ligne de début : 1673
   - Ligne de fin : 1926 (ligne avant `@classmethod def _draw_liste_tableaux`)
   - Nombre de lignes : ~254 lignes

6. **`_draw_liste_tableaux`**
   - Ligne de début : 1926
   - Ligne de fin : 2154 (ligne avant `@classmethod def _draw_liste_graphiques`)
   - Nombre de lignes : ~229 lignes

7. **`_draw_liste_graphiques`**
   - Ligne de début : 2154
   - Ligne de fin : 2382 (ligne avant `@classmethod def _draw_liste_sigles_abreviations`)
   - Nombre de lignes : ~229 lignes

8. **`_draw_liste_sigles_abreviations`**
   - Ligne de début : 2382
   - Ligne de fin : 2702 (ligne avant `@classmethod def _draw_introduction_generale`)
   - Nombre de lignes : ~321 lignes

9. **`_draw_introduction_generale`**
   - Ligne de début : 2702
   - Ligne de fin : 3008 (ligne avant `@classmethod def _draw_partie_i_ministere`)
   - Nombre de lignes : ~307 lignes

10. **`_draw_partie_i_ministere`**
    - Ligne de début : 3008
    - Ligne de fin : 4309 (ligne avant `@classmethod def _create_pie_chart_budget`)
    - Nombre de lignes : ~1302 lignes (c'est une très grande méthode)

## Instructions

1. Ouvrez `app/services/rapport_annuel_performance_service.py`
2. Pour chaque méthode, copiez depuis la ligne de début (incluant `@classmethod` et la définition `def`) jusqu'à la ligne de fin (non incluse)
3. Collez chaque méthode dans `app/services/rapport_annuel_performance_service_simpledoc.py` juste avant la méthode `generate_pdf` (qui commence à la ligne 4491)

## Ordre recommandé pour la copie

**ÉTAPE 1 : Copiez d'abord les méthodes helper Canvas (nécessaires pour les autres méthodes) :**
1. `_determine_data_source_for_canvas` (~34 lignes)
2. `_get_color_for_source` (~18 lignes)
3. `_format_text_for_canvas` (~33 lignes)

**ÉTAPE 2 : Puis copiez les méthodes Canvas (du plus petit au plus grand) :**
1. `_draw_footer` (~44 lignes)
2. `_draw_header` (~151 lignes)
3. `_draw_cover_block` (~172 lignes)
4. `_draw_liste_graphiques` (~229 lignes)
5. `_draw_liste_tableaux` (~229 lignes)
6. `_draw_table_of_contents` (~254 lignes)
7. `_draw_introduction_generale` (~307 lignes)
8. `_draw_background_shapes` (~326 lignes)
9. `_draw_liste_sigles_abreviations` (~321 lignes)
10. `_draw_partie_i_ministere` (~1300 lignes - la plus grande)

## Vérification finale

Après avoir copié toutes les méthodes :
- Vérifiez qu'il n'y a plus de références à `RapportAnnuelPerformanceGenerator` dans le fichier simpledoc
- Supprimez la ligne d'import : `from app.services.rapport_annuel_performance_service import RapportAnnuelPerformanceGenerator`
- Vérifiez que toutes les méthodes utilisent bien `cls.` au lieu de `RapportAnnuelPerformanceGenerator.`
