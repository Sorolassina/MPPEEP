# Instructions Finales - Migration draw_partie_i_ministere

## 🎯 Objectif

Migrer la méthode `draw_partie_i_ministere` (~2120 lignes) du fichier original vers la structure modulaire.

## 📋 Localisation

- **Fichier original**: `rapport_annuel_performance_service_simpledoc.py`
- **Lignes**: 3648-5768
- **Fichier destination**: `rapport_annuel_performance_generator_modular.py`
- **Méthode**: `RAPContentDrawer.draw_partie_i_ministere()`
- **Ligne TODO**: ~5343

## 🔄 Remplacements à Effectuer

Utilisez la fonction "Chercher/Remplacer" de votre éditeur pour effectuer ces remplacements dans l'ordre:

### 1. Formatage (RAPStylingManager)
```python
cls._format_db_data(          → RAPStylingManager.format_db_data(
cls._format_fake_data(        → RAPStylingManager.format_fake_data(
cls._get_sigle_ministere()    → RAPStylingManager.get_sigle_ministere()
```

### 2. Base Generator (RAPBaseGenerator)
```python
cls._should_use_fake_data()      → RAPBaseGenerator.should_use_fake_data()
cls._get_next_tableau_numero()   → RAPBaseGenerator.get_next_tableau_numero()
cls._get_next_figure_numero()    → RAPBaseGenerator.get_next_figure_numero()
cls._db_session                  → RAPBaseGenerator._db_session
```

### 3. Charts (RAPChartGenerator)
```python
cls._create_pie_chart_budget( → RAPChartGenerator.create_pie_chart_budget(
```

### 4. Layout (RAPLayoutDrawer)
```python
cls._draw_page_footer( → RAPLayoutDrawer.draw_page_footer(
```

### 5. Reste identique (même classe)
```python
cls._render_multipage_story( → cls._render_multipage_story(  # Pas de changement
```

## 📝 Étapes de Migration

1. **Copier le code original**
   - Ouvrir `rapport_annuel_performance_service_simpledoc.py`
   - Sélectionner les lignes 3648-5768
   - Copier

2. **Coller dans le fichier modulaire**
   - Ouvrir `rapport_annuel_performance_generator_modular.py`
   - Aller à la ligne ~5343
   - Remplacer le TODO par le code copié

3. **Adapter la signature**
   - Changer `def _draw_partie_i_ministere(cls,` en `def draw_partie_i_ministere(cls,`
   - Retirer le préfixe `_`

4. **Appliquer tous les remplacements**
   - Utiliser la fonction "Chercher/Remplacer" avec chaque remplacement ci-dessus

5. **Vérifier**
   - S'assurer que tous les remplacements ont été effectués
   - Vérifier qu'il n'y a pas d'erreurs de syntaxe

## ⚠️ Notes Importantes

- La méthode `cls._render_multipage_story` reste identique (même classe RAPContentDrawer)
- Tous les autres appels doivent être adaptés
- Les variables partagées (`cls.data`, etc.) restent accessibles
- La logique métier ne doit pas changer

## ✅ Checklist

- [ ] Code original copié
- [ ] Code collé dans modular.py (remplacement du TODO)
- [ ] Signature adaptée (retrait du `_`)
- [ ] Tous les remplacements appliqués
- [ ] Vérification syntaxe
- [ ] Tests fonctionnels

## 📊 Statistiques

- **Longueur**: ~2120 lignes
- **Complexité**: ⭐⭐⭐⭐⭐ (Très élevée)
- **Temps estimé**: 30-60 minutes (migration manuelle)

---

**Date**: 2024-12-19
**Status**: ⏳ En attente de migration

