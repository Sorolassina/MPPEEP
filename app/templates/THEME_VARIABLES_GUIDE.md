# 🎨 Guide des Variables CSS - MPPEEP Dashboard

## 📋 Vue d'Ensemble

Ce document liste **toutes les variables CSS** disponibles dans le système. Tous les templates doivent utiliser ces variables au lieu de couleurs codées en dur.

---

## ✨ Système d'Injection Automatique

Les couleurs sont injectées automatiquement dans `layouts/base.html` :

```html
<!-- layouts/base.html -->
<link rel="stylesheet" href="{{ static_url('css/theme.css') }}">

{% if system_settings %}
<style>
    :root {
        /* Ces variables ÉCRASENT celles de theme.css */
        --primary-color: {{ system_settings.primary_color }};
        --secondary-color: {{ system_settings.secondary_color }};
        --accent-color: {{ system_settings.accent_color }};
        --primary-dark: {{ system_settings.primary_dark }};
        --primary-light: {{ system_settings.primary_light }};
    }
</style>
{% endif %}
```

**Résultat** : Les couleurs de la base de données ont priorité sur celles de `theme.css` !

---

## 🎨 Variables de Couleurs Disponibles

### Couleurs Principales

| Variable | Valeur par défaut | Usage | Exemple |
|----------|-------------------|-------|---------|
| `--primary-color` | #ffd300 | Couleur principale (jaune) | Boutons primaires, textes importants |
| `--primary-dark` | #e6be00 | Variante foncée | Hover sur boutons jaunes |
| `--primary-light` | #ffe664 | Variante claire | Backgrounds légers |
| `--secondary-color` | #036c1d | Couleur secondaire (vert) | Navbar, titres, footer |
| `--white-color` | #FFFFFF | Blanc | Backgrounds, textes sur fond sombre |
| `--accent-color` | #e63600 | Couleur d'accent (rouge) | **Tous les hovers**, CTAs importants |

### Nuances de Gris

| Variable | Valeur | Usage |
|----------|--------|-------|
| `--gray-100` | #f8f9fa | Backgrounds très légers |
| `--gray-200` | #e9ecef | Borders, séparateurs |
| `--gray-300` | #dee2e6 | Borders plus visibles |
| `--gray-400` | #ced4da | Borders actifs |
| `--gray-500` | #adb5bd | Textes secondaires |
| `--gray-600` | #6c757d | Textes normaux |
| `--gray-700` | #495057 | Textes foncés |
| `--gray-800` | #343a40 | Textes très foncés |
| `--gray-900` | #212529 | Noir presque pur |

### Alias Pratiques

| Variable | Équivalent | Usage |
|----------|------------|-------|
| `--gray-light` | `--gray-100` | Backgrounds légers |
| `--gray-medium` | `--gray-600` | Textes secondaires |
| `--gray-dark` | `--gray-800` | Textes importants |

### Couleurs Système

| Variable | Valeur | Usage |
|----------|--------|-------|
| `--success-color` | #28a745 | Messages de succès |
| `--success-light` | #d4edda | Background succès |
| `--success-dark` | #155724 | Texte succès |
| `--success-border` | #c3e6cb | Border succès |
| **Info** | | |
| `--info-color` | #17a2b8 | Messages d'information |
| `--info-light` | #d1ecf1 | Background info |
| `--info-dark` | #0c5460 | Texte info |
| `--info-border` | #bee5eb` | Border info |
| **Warning** | | |
| `--warning-color` | #ffc107 | Avertissements |
| `--warning-light` | #fff3cd | Background warning |
| `--warning-dark` | #856404 | Texte warning |
| `--warning-border` | #ffeaa7 | Border warning |
| **Danger/Error** | | |
| `--danger-color` | #dc3545 | Erreurs, suppressions |
| `--danger-light` | #f8d7da | Background danger |
| `--danger-dark` | #721c24 | Texte danger |
| `--danger-border` | #f5c6cb | Border danger |
| `--error-color` | #dc3545 | Alias de danger |

---

## 📏 Variables d'Espacement

| Variable | Valeur | Pixels | Usage |
|----------|--------|--------|-------|
| `--spacing-xs` | 0.25rem | 4px | Petits espacements |
| `--spacing-sm` | 0.5rem | 8px | Espacements moyens |
| `--spacing-md` | 1rem | 16px | Espacements standards |
| `--spacing-lg` | 1.5rem | 24px | Grands espacements |
| `--spacing-xl` | 3rem | 48px | Très grands espacements |

---

## 🔲 Variables de Bordures

| Variable | Valeur | Usage |
|----------|--------|-------|
| `--border-radius` | 0.375rem (6px) | Bordures arrondies standard |
| `--border-radius-lg` | 0.5rem (8px) | Bordures arrondies larges |
| `--border-width` | 1px | Épaisseur des bordures |

---

## 🌑 Variables d'Ombres

| Variable | Valeur | Usage |
|----------|--------|-------|
| `--shadow-sm` | `0 0.125rem 0.25rem rgba(0,0,0,0.075)` | Ombre légère |
| `--shadow` | `0 0.5rem 1rem rgba(0,0,0,0.15)` | Ombre standard |
| `--shadow-md` | `0 0.75rem 1.5rem rgba(0,0,0,0.12)` | Ombre moyenne |
| `--shadow-lg` | `0 1rem 3rem rgba(0,0,0,0.175)` | Ombre forte |

---

## 📐 Variables de Layout

| Variable | Valeur | Usage |
|----------|--------|-------|
| `--sidebar-width` | 220px | Largeur sidebar ouverte |
| `--sidebar-width-collapsed` | 60px | Largeur sidebar fermée |

---

## 🎯 Comment Utiliser les Variables

### ✅ CORRECT - Utiliser les variables CSS

```html
<style>
/* En-tête avec couleur secondaire */
.page-header {
  background: var(--secondary-color);
  color: var(--white-color);
  padding: var(--spacing-lg);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow-sm);
}

/* Bouton avec hover sur accent */
.btn-custom {
  background: var(--primary-color);
  color: var(--gray-900);
  padding: var(--spacing-sm) var(--spacing-lg);
  border: 1px solid var(--primary-color);
}

.btn-custom:hover {
  background: var(--accent-color);
  border-color: var(--accent-color);
  color: var(--white-color);
}

/* Card avec couleurs système */
.card-info {
  background: var(--info-light);
  border-left: 4px solid var(--info-color);
  color: var(--info-dark);
}

/* Gradient avec variables */
.gradient-bg {
  background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
}
</style>
```

### ❌ INCORRECT - Couleurs codées en dur

```html
<style>
/* NE PAS FAIRE ÇA ! */
.page-header {
  background: #036c1d;  /* ❌ Codé en dur */
  color: #FFFFFF;        /* ❌ Codé en dur */
  padding: 24px;         /* ❌ Devrait être var(--spacing-lg) */
}

.btn-custom {
  background: #ffd300;   /* ❌ Devrait être var(--primary-color) */
}

.btn-custom:hover {
  background: #e63600;   /* ❌ Devrait être var(--accent-color) */
}
</style>
```

---

## 🔄 Exemples de Migration

### Exemple 1 : En-tête de Page

#### Avant
```html
<div style="background: #667eea; color: white; padding: 2rem; border-radius: 12px;">
    <h1 style="color: white;">Mon Titre</h1>
</div>
```

#### Après
```html
<div style="background: var(--secondary-color); color: var(--white-color); padding: var(--spacing-xl); border-radius: var(--border-radius-lg);">
    <h1 style="color: var(--white-color);">Mon Titre</h1>
</div>
```

### Exemple 2 : Bouton avec Gradient

#### Avant
```html
<button style="background: linear-gradient(135deg, #ffd300, #e6be00); color: #000; padding: 12px 24px;">
    Cliquez-moi
</button>
```

#### Après
```html
<button style="background: linear-gradient(135deg, var(--primary-color), var(--primary-dark)); color: var(--gray-900); padding: var(--spacing-sm) var(--spacing-lg);">
    Cliquez-moi
</button>
```

### Exemple 3 : Card avec Border Colorée

#### Avant
```html
<div style="background: white; border-left: 4px solid #28a745; padding: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
    Message de succès
</div>
```

#### Après
```html
<div style="background: var(--white-color); border-left: 4px solid var(--success-color); padding: var(--spacing-lg); box-shadow: var(--shadow-sm);">
    Message de succès
</div>
```

### Exemple 4 : Avatar avec Gradient

#### Avant
```html
<div style="width: 120px; height: 120px; border-radius: 50%; background: linear-gradient(135deg, #667eea, #764ba2); display: flex; align-items: center; justify-content: center; color: white; font-size: 3rem;">
    JD
</div>
```

#### Après
```html
<div style="width: 120px; height: 120px; border-radius: 50%; background: linear-gradient(135deg, var(--secondary-color), var(--accent-color)); display: flex; align-items: center; justify-content: center; color: var(--white-color); font-size: 3rem;">
    JD
</div>
```

---

## 📝 Règles de Nommage des Couleurs

### Convention pour les Gradients

```css
/* Gradient principal (primary → primary-dark) */
background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));

/* Gradient secondaire (secondary → accent) */
background: linear-gradient(135deg, var(--secondary-color), var(--accent-color));

/* Gradient neutre (gris) */
background: linear-gradient(135deg, var(--gray-100), var(--gray-300));
```

### Convention pour les Hovers

```css
/* TOUS les boutons utilisent accent-color au hover */
.btn:hover,
.btn-primary:hover,
.btn-secondary:hover,
.btn-outline:hover {
  background-color: var(--accent-color);
  color: var(--white-color);
}
```

### Convention pour les Bordures Colorées

```css
/* Border gauche pour les alertes/messages */
.alert-success { border-left: 4px solid var(--success-color); }
.alert-info { border-left: 4px solid var(--info-color); }
.alert-warning { border-left: 4px solid var(--warning-color); }
.alert-danger { border-left: 4px solid var(--danger-color); }

/* Border top pour les cards */
.card-header { border-top: var(--border-width) solid var(--primary-color); }
```

---

## 🛠️ Outils de Migration

### Script de Recherche des Couleurs Codées en Dur

```bash
# Trouver toutes les couleurs hex dans les templates
grep -r "#[0-9a-fA-F]\{3,6\}" app/templates/pages/

# Trouver les couleurs RGB/RGBA
grep -r "rgba\?\(" app/templates/pages/
```

### Remplacements Courants

| Ancien | Nouveau | Variable |
|--------|---------|----------|
| `#ffd300` | `var(--primary-color)` | Jaune principal |
| `#036c1d` | `var(--secondary-color)` | Vert principal |
| `#e63600` | `var(--accent-color)` | Rouge accent |
| `#FFFFFF` | `var(--white-color)` | Blanc |
| `#28a745` | `var(--success-color)` | Vert succès |
| `#dc3545` | `var(--danger-color)` | Rouge erreur |
| `#667eea` | `var(--secondary-color)` | Bleu/Vert |
| `#764ba2` | `var(--accent-color)` | Violet/Rouge |

---

## 🎨 Exemples par Type de Composant

### En-têtes de Page

```html
<style>
.page-header {
  background: linear-gradient(135deg, var(--secondary-color), var(--accent-color));
  color: var(--white-color);
  padding: var(--spacing-xl) var(--spacing-lg);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-md);
}

.page-title {
  color: var(--white-color);
  margin-bottom: var(--spacing-sm);
}
</style>
```

### Cards/Cartes

```html
<style>
.custom-card {
  background: var(--white-color);
  border: var(--border-width) solid var(--gray-200);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.custom-card:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--primary-color);
}
</style>
```

### Boutons Personnalisés

```html
<style>
.btn-action {
  background: var(--secondary-color);
  color: var(--white-color);
  padding: var(--spacing-sm) var(--spacing-lg);
  border: none;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-action:hover {
  background: var(--accent-color);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}
</style>
```

### Badges/Labels

```html
<style>
.badge-primary {
  background: var(--primary-color);
  color: var(--gray-900);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--border-radius);
  font-size: 0.875rem;
}

.badge-success {
  background: var(--success-color);
  color: var(--white-color);
}

.badge-danger {
  background: var(--danger-color);
  color: var(--white-color);
}
</style>
```

### Tableaux

```html
<style>
.custom-table {
  width: 100%;
  background: var(--white-color);
  border-radius: var(--border-radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.custom-table thead {
  background: var(--secondary-color);
  color: var(--white-color);
}

.custom-table tbody tr:hover {
  background: var(--gray-100);
}

.custom-table td {
  padding: var(--spacing-sm) var(--spacing-md);
  border-bottom: var(--border-width) solid var(--gray-200);
}
</style>
```

---

## ✅ Checklist de Migration d'un Template

- [ ] Remplacer toutes les couleurs hex (#xxx) par `var(--xxx-color)`
- [ ] Remplacer les spacings (px/rem) par `var(--spacing-xxx)`
- [ ] Remplacer les border-radius par `var(--border-radius)`
- [ ] Remplacer les box-shadow par `var(--shadow-xxx)`
- [ ] Vérifier que tous les hovers utilisent `var(--accent-color)`
- [ ] Tester l'affichage dans différents thèmes
- [ ] Vérifier la cohérence visuelle

---

## 🚀 Avantages du Système

1. **Cohérence** : Tous les templates utilisent les mêmes couleurs
2. **Maintenabilité** : Changement de couleur en 1 seul endroit (DB)
3. **Thèmes** : Possibilité d'ajouter des thèmes facilement
4. **Performance** : Variables CSS = 0 overhead
5. **Accessibilité** : Contraste calculé automatiquement

---

## 📚 Ressources

- **Fichier theme.css** : `app/static/css/theme.css`
- **Layout de base** : `app/templates/layouts/base.html`
- **Service système** : `app/services/system_settings_service.py`
- **Documentation couleurs** : `app/static/css/COLORS_SYSTEM.md`

---

**🎨 Utilisez toujours les variables CSS pour une cohérence maximale !**

