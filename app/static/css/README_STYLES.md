# 🎨 Guide des Styles - MPPEEP Dashboard

## 📁 Organisation des Fichiers CSS

### Structure des Fichiers
```
app/static/css/
├── base.css          ← Styles de base (reset, typographie)
├── theme.css         ← Variables de couleurs et thème
├── components.css    ← Composants réutilisables (alertes, modales, overlay)
└── pages.css         ← ✨ NOUVEAU : Styles communs des pages
```

---

## 🆕 pages.css - Styles Centralisés

Ce fichier contient **tous les styles communs** pour les pages de l'application :

### 1. **Layout & Grilles**
- `.page-grid` : Grille principale avec arrière-plan gradient grisé
- Padding, gaps, max-width standardisés

### 2. **Cards**
- `.card` : Card blanc avec shadow et hover effect
- Border-radius 20px pour un look moderne

### 3. **Stats Cards**
- `.stats-cards` : Grille responsive pour les statistiques
- `.stat-card` : Card avec gradient coloré
  - `.stat-card.secondary` : Variant rose/rouge
  - `.stat-card.success` : Variant bleu
  - `.stat-card.warning` : Variant rose/jaune
- `.stat-number` : Chiffre animé
- `.stat-label` : Label en majuscules

### 4. **Barre d'Actions**
- `.actions-bar` : Container flex pour actions
- `.search-box` : Champ de recherche stylisé

### 5. **Boutons**
- `.btn-primary` : Bouton principal avec gradient violet
- `.btn-back` : Bouton retour avec gradient gris
- Effets "ripple" au hover

### 6. **Tables**
- `.data-table` : Table moderne avec animations
- Header avec gradient violet
- Hover effects sur les lignes

### 7. **Badges**
- `.badge` : Badge générique
- `.badge-success` : Vert
- `.badge-danger` : Rouge
- `.badge-warning` : Rose
- `.badge-info` : Bleu

### 8. **Action Icons**
- `.action-icons` : Container flex
- `.action-icon` : Icône cliquable avec hover

### 9. **Empty State**
- `.empty-state` : Message quand pas de données
- `.empty-state-icon` : Icône animée

### 10. **Animations**
- `countUp` : Animation des chiffres
- `slideUp` : Slide de bas en haut
- `fadeIn` : Fondu
- `pulse` : Pulsation

---

## 🎯 Comment Utiliser

### Méthode 1 : Automatique (Recommandé)
Le fichier `pages.css` est **automatiquement chargé** dans `layouts/base.html` :

```html
<!-- base.html -->
<link rel="stylesheet" href="{{ static_url('css/pages.css') }}">
```

**Toutes les pages qui étendent `base.html` ont accès aux styles !**

### Méthode 2 : Classes Standard

Utilisez les classes génériques dans vos templates :

```html
<!-- Page avec grille -->
<div class="page-grid">
  
  <!-- Card -->
  <div class="card">
    <h1>Titre</h1>
    <p>Contenu</p>
  </div>

  <!-- Stats Cards -->
  <div class="stats-cards">
    <div class="stat-card">
      <div class="stat-label">Total</div>
      <div class="stat-number">250</div>
    </div>
    
    <div class="stat-card success">
      <div class="stat-label">Actifs</div>
      <div class="stat-number">180</div>
    </div>
  </div>

  <!-- Table -->
  <div class="data-table">
    <table>
      <thead>
        <tr>
          <th>Colonne 1</th>
          <th>Colonne 2</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Donnée 1</td>
          <td>Donnée 2</td>
        </tr>
      </tbody>
    </table>
  </div>

</div>
```

---

## ✅ Pages Migrées

### ✨ Personnel (`pages/personnel.html`)
- ✅ Utilise `.page-grid`
- ✅ Utilise `.card`
- ✅ Utilise `.stats-cards`
- ✅ Utilise `.data-table`
- ✅ Utilise `.btn-primary`, `.btn-back`
- ✅ Utilise `.badge-success`, `.badge-danger`
- ✅ **0 styles dupliqués**

### ✨ RH (`pages/rh.html`)
- ✅ Utilise `.page-grid`
- ✅ Utilise `.card`
- ✅ Utilise `.btn-back`
- ✅ Garde ses styles spécifiques pour KPIs (design différent)
- ✅ **90% styles centralisés**

---

## 🔧 Personnalisation

### Ajouter une Variante de Stat-Card

```css
/* Dans pages.css */
.stat-card.custom {
  background: linear-gradient(135deg, #couleur1 0%, #couleur2 100%);
  box-shadow: 0 10px 30px rgba(...);
}

.stat-card.custom:hover {
  box-shadow: 0 15px 40px rgba(...);
}
```

### Créer un Nouveau Style de Badge

```css
/* Dans pages.css */
.badge-purple {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}
```

---

## 📱 Responsive

Le fichier `pages.css` inclut des breakpoints responsive :

```css
@media (max-width: 768px) {
  .page-grid {
    padding: 1rem;
    gap: 1.5rem;
  }

  .stats-cards {
    grid-template-columns: 1fr;
  }

  .actions-bar {
    flex-direction: column;
  }
}
```

---

## 🎨 Palette de Couleurs

### Gradients Principaux
- **Primary** : `#667eea → #764ba2` (Violet)
- **Secondary** : `#f093fb → #f5576c` (Rose/Rouge)
- **Success** : `#4facfe → #00f2fe` (Bleu)
- **Warning** : `#fa709a → #fee140` (Rose/Jaune)
- **Back** : `#6c757d → #495057` (Gris)

### Background
- **Page** : `#f5f7fa → #c3cfe2` (Gris clair)

---

## 📊 Avantages

### ✅ Uniformité
Toutes les pages ont le même look & feel

### ✅ Maintenabilité
Un seul fichier à modifier pour changer le style global

### ✅ Performance
Moins de CSS dupliqué = fichiers plus légers

### ✅ Réutilisabilité
Copier-coller simplement les classes dans de nouvelles pages

### ✅ Scalabilité
Facile d'ajouter de nouvelles variantes

---

## 🚀 Prochaines Étapes

### Pour Créer une Nouvelle Page

1. **Étendre base.html** :
```html
{% extends "layouts/base.html" %}
{% block title %}Ma Page{% endblock %}
```

2. **Utiliser les classes** :
```html
{% block content %}
<div class="page-grid">
  <div class="card">
    <!-- Contenu -->
  </div>
</div>
{% endblock %}
```

3. **Ajouter styles spécifiques si besoin** :
```html
{% block styles %}
<style>
/* Styles spécifiques à cette page seulement */
.ma-classe-custom {
  /* ... */
}
</style>
{% endblock %}
```

---

## 📝 Checklist Migration d'une Page

- [ ] Remplacer la grille custom par `.page-grid`
- [ ] Remplacer les cards custom par `.card`
- [ ] Utiliser `.stats-cards` pour les statistiques
- [ ] Utiliser `.data-table` pour les tableaux
- [ ] Utiliser `.btn-primary`, `.btn-back` pour les boutons
- [ ] Utiliser `.badge-*` pour les badges
- [ ] Supprimer les styles CSS dupliqués
- [ ] Garder seulement les styles vraiment spécifiques

---

**🎉 Application maintenant uniformisée !**

