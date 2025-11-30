# Vérification des méthodes manquantes

## ✅ Méthodes PRÉSENTES dans le service simpledoc :

1. ✅ `_determine_data_source_for_canvas` (ligne 225)
2. ✅ `_get_color_for_source` (ligne 261 et ligne 1623 - doublon ?)
3. ✅ `_format_text_for_canvas` (ligne 279)
4. ✅ `_draw_footer` (ligne 312)
5. ✅ `_draw_header` (ligne 358)
6. ✅ `_draw_cover_block` (ligne 508)
7. ✅ `_draw_table_of_contents` (ligne 679)
8. ✅ `_draw_liste_tableaux` (ligne 932)
9. ✅ `_draw_liste_graphiques` (ligne 1160)
10. ✅ `_draw_liste_sigles_abreviations` (ligne 1388)
11. ✅ `_draw_introduction_generale` (ligne 1654)
12. ✅ `_draw_partie_i_ministere` (ligne 1960)
13. ✅ `load_system_settings_data` (ligne 7107)
14. ✅ `load_budget_data` (ligne 7206)

## ❌ Méthodes MANQUANTES :

1. ❌ **`_draw_background_shapes`** - APPELÉE ligne 7580 mais NON DÉFINIE

## 📋 Informations pour copier la méthode manquante :

**`_draw_background_shapes`**
- Fichier source : `app/services/rapport_annuel_performance_service.py`
- Ligne de début : **984**
- Ligne de fin : **1309** (ligne avant `@classmethod def _draw_header`)
- Nombre de lignes : ~326 lignes
- Où coller : Juste avant la méthode `generate_pdf` (actuellement ligne 7515)

## 📝 Autres vérifications :

- ✅ L'import du service original a été supprimé (pas d'import trouvé)
- ✅ Toutes les références utilisent `cls.` au lieu de `RapportAnnuelPerformanceGenerator.`
