# 🎨 Dossier Static - Fichiers Statiques

## 🤔 C'est Quoi ?

Le dossier `static/` contient tous les **fichiers qui ne changent pas** : CSS, JavaScript, images, fonts, etc.

### 🏗️ Analogie Simple

Imaginez un magasin :

- 🏪 **L'application** = Le magasin
- 🎨 **Static** = La décoration du magasin (logo, couleurs, musique)
- 📦 **Dynamic** = Les produits (changent selon le stock)

**Fichiers statiques = Toujours les mêmes, servis tels quels**

---

## 📁 Structure

```
app/static/
├── css/              ← Feuilles de style
│   └── style.css
│
├── js/               ← Scripts JavaScript
│   └── app.js
│
├── images/           ← Images (logos, icons, etc.)
│   └── (à créer)
│
└── fonts/            ← Polices personnalisées
    └── (à créer)
```

---

## 🎯 Structure Recommandée

### Organisation Idéale

```
static/
├── css/
│   ├── base.css           ← Reset, typography
│   ├── theme.css          ← Variables CSS, couleurs
│   ├── components/        ← Styles des composants
│   │   ├── navbar.css
│   │   ├── footer.css
│   │   ├── buttons.css
│   │   └── forms.css
│   ├── pages/             ← Styles par page
│   │   ├── home.css
│   │   ├── dashboard.css
│   │   └── login.css
│   └── auth.css           ← Styles authentification
│
├── js/
│   ├── app.js             ← JavaScript principal
│   ├── utils.js           ← Fonctions utilitaires
│   ├── api.js             ← Appels API
│   └── components/        ← Scripts par composant
│       ├── navbar.js
│       └── forms.js
│
├── images/
│   ├── logo.png           ← Logo principal
│   ├── logo-white.png     ← Logo version blanche
│   ├── favicon.ico        ← Icône navigateur
│   ├── og-image.png       ← Image Open Graph (réseaux sociaux)
│   └── icons/             ← Icônes
│       ├── user.svg
│       ├── settings.svg
│       └── logout.svg
│
├── fonts/
│   ├── custom-font.woff2
│   └── custom-font.woff
│
└── vendor/                ← Bibliothèques externes
    ├── bootstrap.min.css
    └── jquery.min.js
```

---

## 🌐 Accès aux Fichiers Statiques

### Configuration dans main.py

```python
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="app/static"), name="static")
```

**Résultat :**
```
URL                                    Fichier Physique
────────────────────────────────────────────────────────────
/static/css/style.css              → app/static/css/style.css
/static/js/app.js                  → app/static/js/app.js
/static/images/logo.png            → app/static/images/logo.png
```

---

## 🎨 CSS - Feuilles de Style

### Organisation Modulaire

#### `base.css` - Styles de Base

```css
/* Reset CSS */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

/* Typography */
body {
    font-family: 'Segoe UI', Tahoma, sans-serif;
    font-size: 16px;
    line-height: 1.6;
    color: #333;
}

h1, h2, h3, h4, h5, h6 {
    margin-bottom: 1rem;
    font-weight: 600;
}

/* Utilitaires */
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

.text-center { text-align: center; }
.mt-1 { margin-top: 0.5rem; }
.mb-1 { margin-bottom: 0.5rem; }
```

---

#### `theme.css` - Variables et Thème

```css
:root {
    /* Couleurs principales */
    --primary-color: #3b82f6;      /* Bleu */
    --secondary-color: #1f2937;    /* Gris foncé */
    --accent-color: #f59e0b;       /* Orange */
    
    /* Couleurs fonctionnelles */
    --success-color: #10b981;      /* Vert */
    --error-color: #ef4444;        /* Rouge */
    --warning-color: #f59e0b;      /* Orange */
    --info-color: #3b82f6;         /* Bleu */
    
    /* Couleurs de fond */
    --bg-primary: #ffffff;
    --bg-secondary: #f3f4f6;
    --bg-dark: #1f2937;
    
    /* Texte */
    --text-primary: #1f2937;
    --text-secondary: #6b7280;
    --text-light: #9ca3af;
    
    /* Espacement */
    --spacing-xs: 0.25rem;
    --spacing-sm: 0.5rem;
    --spacing-md: 1rem;
    --spacing-lg: 1.5rem;
    --spacing-xl: 2rem;
    
    /* Bordures */
    --border-radius: 0.375rem;
    --border-color: #e5e7eb;
    
    /* Ombres */
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
    --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
}

/* Mode sombre (optionnel) */
[data-theme="dark"] {
    --bg-primary: #1f2937;
    --bg-secondary: #111827;
    --text-primary: #f3f4f6;
    --text-secondary: #9ca3af;
}
```

**Utilisation :**
```css
.button-primary {
    background-color: var(--primary-color);
    color: white;
    border-radius: var(--border-radius);
    box-shadow: var(--shadow-md);
}
```

---

## 💻 JavaScript

### `app.js` - Script Principal

```javascript
// app/static/js/app.js

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ Application initialisée');
    
    // Initialiser les composants
    initNavbar();
    initForms();
    initModals();
});

// Fonctions globales
function initNavbar() {
    // Mobile menu toggle
    const menuButton = document.querySelector('.mobile-menu-button');
    const mobileMenu = document.querySelector('.mobile-menu');
    
    if (menuButton && mobileMenu) {
        menuButton.addEventListener('click', () => {
            mobileMenu.classList.toggle('hidden');
        });
    }
}

function initForms() {
    // Validation des formulaires
    const forms = document.querySelectorAll('form[data-validate]');
    
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            if (!validateForm(form)) {
                e.preventDefault();
            }
        });
    });
}

function validateForm(form) {
    // Logique de validation
    return true;
}
```

---

### `api.js` - Appels API

```javascript
// app/static/js/api.js

// Fonction helper pour les appels API
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Exemples d'utilisation
async function getUsers() {
    return await apiCall('/api/v1/users');
}

async function createUser(userData) {
    return await apiCall('/api/v1/users', {
        method: 'POST',
        body: JSON.stringify(userData)
    });
}
```

---

## 🖼️ Images

### Organisation

```
static/images/
├── logo.png              ← Logo principal
├── logo-white.png        ← Variante blanche
├── favicon.ico           ← Icône navigateur
├── og-image.png          ← Open Graph (réseaux sociaux)
├── default-avatar.png    ← Avatar par défaut
│
├── icons/                ← Icônes SVG
│   ├── user.svg
│   ├── settings.svg
│   └── logout.svg
│
└── illustrations/        ← Illustrations
    ├── 404.svg
    └── empty-state.svg
```

### Utilisation dans Templates

```html
<!-- Logo -->
<img src="/static/images/logo.png" alt="Logo">

<!-- Favicon -->
<link rel="icon" href="/static/images/favicon.ico">

<!-- Open Graph (partage réseaux sociaux) -->
<meta property="og:image" content="/static/images/og-image.png">

<!-- Avatar par défaut -->
<img src="/static/images/default-avatar.png" alt="Avatar">
```

---

## 🔤 Fonts (Polices)

### Fonts Locales

```
static/fonts/
├── roboto-regular.woff2
├── roboto-bold.woff2
└── custom-font.woff2
```

### Dans CSS

```css
/* Déclarer la police */
@font-face {
    font-family: 'Roboto';
    src: url('/static/fonts/roboto-regular.woff2') format('woff2');
    font-weight: 400;
    font-style: normal;
}

@font-face {
    font-family: 'Roboto';
    src: url('/static/fonts/roboto-bold.woff2') format('woff2');
    font-weight: 700;
    font-style: normal;
}

/* Utiliser */
body {
    font-family: 'Roboto', sans-serif;
}
```

---

## 🔗 Utilisation dans Templates

### URL Helper Jinja2

```html
<!-- Méthode 1 : Chemin direct -->
<link rel="stylesheet" href="/static/css/style.css">
<script src="/static/js/app.js"></script>

<!-- Méthode 2 : url_for (recommandé) -->
<link rel="stylesheet" href="{{ url_for('static', path='css/style.css') }}">
<script src="{{ url_for('static', path='js/app.js') }}"></script>

<!-- Méthode 3 : Via path_config -->
{% set logo = path_config.get_file_url('static', 'images/logo.png') %}
<img src="{{ logo }}" alt="Logo">
```

**Avantage de `url_for` :** Si vous changez le préfixe `/static`, tout est mis à jour automatiquement.

---

## 📦 Bibliothèques Externes

### Option 1 : CDN (Recommandé pour Démarrer)

```html
<!-- Tailwind CSS -->
<script src="https://cdn.tailwindcss.com"></script>

<!-- Font Awesome -->
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">

<!-- Alpine.js -->
<script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
```

### Option 2 : Fichiers Locaux

```
static/vendor/
├── bootstrap/
│   ├── bootstrap.min.css
│   └── bootstrap.min.js
├── jquery/
│   └── jquery.min.js
└── fontawesome/
    └── all.min.css
```

```html
<link rel="stylesheet" href="/static/vendor/bootstrap/bootstrap.min.css">
<script src="/static/vendor/jquery/jquery.min.js"></script>
```

---

## ⚡ Performance

### Bonnes Pratiques

1. **Minifier les fichiers**
   ```
   style.css (100KB) → style.min.css (30KB)
   app.js (50KB) → app.min.js (15KB)
   ```

2. **Optimiser les images**
   ```
   logo.png (500KB) → logo.webp (50KB)
   → Format WebP = -90% de taille
   ```

3. **Ordre de chargement**
   ```html
   <head>
       <!-- CSS en premier (rendu) -->
       <link rel="stylesheet" href="/static/css/style.css">
   </head>
   <body>
       <!-- Contenu -->
       
       <!-- JS à la fin (ne bloque pas le rendu) -->
       <script src="/static/js/app.js"></script>
   </body>
   ```

4. **Cache navigateur**
   ```python
   # Dans middleware.py (déjà configuré)
   Cache-Control: public, max-age=31536000
   # → Fichiers static mis en cache 1 an
   ```

---

## 🎨 CSS - Organisation Recommandée

### Fichiers à Créer

```css
/* base.css - Fondations */
- Reset CSS
- Typography
- Utilitaires génériques

/* theme.css - Thème */
- Variables CSS (couleurs, espacements)
- Mode clair/sombre
- Tokens de design

/* components/ - Composants */
- navbar.css
- footer.css
- buttons.css
- forms.css
- cards.css
- modals.css

/* pages/ - Pages spécifiques */
- home.css
- login.css
- dashboard.css
- profile.css

/* auth.css - Authentification */
- Styles communs pour login, register, recovery
```

### Ordre d'Import

```html
<head>
    <!-- 1. Base -->
    <link rel="stylesheet" href="/static/css/base.css">
    
    <!-- 2. Thème -->
    <link rel="stylesheet" href="/static/css/theme.css">
    
    <!-- 3. Composants -->
    <link rel="stylesheet" href="/static/css/components/navbar.css">
    <link rel="stylesheet" href="/static/css/components/buttons.css">
    
    <!-- 4. Page spécifique -->
    <link rel="stylesheet" href="/static/css/pages/login.css">
</head>
```

---

## 💻 JavaScript - Organisation Recommandée

### Modules Recommandés

```javascript
// app.js - Point d'entrée
import { initNavbar } from './components/navbar.js';
import { apiCall } from './utils/api.js';

document.addEventListener('DOMContentLoaded', () => {
    initNavbar();
});

// utils/api.js - Appels API
export async function apiCall(url, options) {
    // ...
}

// components/navbar.js - Composant navbar
export function initNavbar() {
    // ...
}

// components/forms.js - Gestion des formulaires
export function validateForm(form) {
    // ...
}
```

---

## 🖼️ Images - Bonnes Pratiques

### Formats Recommandés

| Type | Format | Quand |
|------|--------|-------|
| **Photos** | WebP, JPEG | Photos, illustrations |
| **Logos** | SVG, PNG | Logos, icônes |
| **Icônes** | SVG | Icônes, pictogrammes |
| **Favicon** | ICO, PNG | Icône navigateur |

### Tailles Optimales

```
Logo :         200x50px   (petit)
               400x100px  (moyen)
               800x200px  (grand)

Avatar :       48x48px    (petit)
               96x96px    (moyen)
               256x256px  (grand)

OG Image :     1200x630px (Open Graph)
Favicon :      32x32px, 16x16px
```

### Optimisation

```bash
# Convertir en WebP (meilleure compression)
# Nécessite : pip install Pillow

from PIL import Image

img = Image.open("logo.png")
img.save("logo.webp", "WEBP", quality=85)
# → -70% de taille !
```

---

## 📂 Utilisation depuis Python

### Servir un Fichier Statique

```python
from fastapi.responses import FileResponse
from app.core.path_config import path_config

@router.get("/download-logo")
async def download_logo():
    logo_path = path_config.get_physical_path("static", "images/logo.png")
    
    return FileResponse(
        path=logo_path,
        filename="logo.png",
        media_type="image/png"
    )
```

### Vérifier l'Existence

```python
from app.core.path_config import path_config

@router.get("/has-logo")
async def has_logo():
    logo_path = path_config.get_physical_path("static", "images/logo.png")
    
    return {
        "exists": logo_path.exists(),
        "url": "/static/images/logo.png" if logo_path.exists() else None
    }
```

---

## 🎯 Exemples Pratiques

### Exemple 1 : Page avec CSS et JS

```html
<!-- templates/pages/dashboard.html -->
{% extends "layouts/base.html" %}

{% block styles %}
    <!-- CSS spécifique au dashboard -->
    <link rel="stylesheet" href="/static/css/pages/dashboard.css">
{% endblock %}

{% block content %}
    <div class="dashboard">
        <h1>Dashboard</h1>
        <!-- Contenu -->
    </div>
{% endblock %}

{% block scripts %}
    <!-- JS spécifique au dashboard -->
    <script src="/static/js/dashboard.js"></script>
{% endblock %}
```

---

### Exemple 2 : Composant avec Styles

```css
/* static/css/components/card.css */

.card {
    background: var(--bg-primary);
    border-radius: var(--border-radius);
    box-shadow: var(--shadow-md);
    padding: var(--spacing-lg);
    margin-bottom: var(--spacing-md);
}

.card-title {
    font-size: 1.5rem;
    font-weight: 600;
    margin-bottom: var(--spacing-sm);
    color: var(--text-primary);
}

.card-body {
    color: var(--text-secondary);
}
```

```html
<!-- Utilisation dans template -->
<link rel="stylesheet" href="/static/css/components/card.css">

<div class="card">
    <h3 class="card-title">Titre de la Carte</h3>
    <div class="card-body">Contenu de la carte</div>
</div>
```

---

### Exemple 3 : JavaScript Interactif

```javascript
// static/js/components/modal.js

export function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }
}

export function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

// Fermer avec Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.add('hidden');
        });
    }
});
```

---

## 🔐 Sécurité

### ⚠️ Ne PAS Mettre dans Static

```
❌ .env                  ← Secrets
❌ app.db                ← Base de données
❌ *.py                  ← Code Python
❌ config.yaml           ← Configuration
❌ private_keys/         ← Clés privées
```

**Pourquoi ?** Tout dans `static/` est **accessible publiquement** !

### ✅ Ce Qui Va dans Static

```
✅ CSS                   ← Styles publics
✅ JS                    ← Scripts publics
✅ Images                ← Images publiques
✅ Fonts                 ← Polices publiques
✅ Bibliothèques         ← Vendor (Bootstrap, etc.)
```

---

## 📊 Différence Static vs Uploads vs Media

| Dossier | Contenu | Modifiable | Exemple |
|---------|---------|------------|---------|
| **static/** | Fichiers de l'app | ❌ Non (déployé avec le code) | CSS, JS, logo |
| **uploads/** | Fichiers utilisateurs | ✅ Oui (créés à l'exécution) | Avatars, documents |
| **media/** | Fichiers médias | ✅ Oui (générés/uploadés) | Photos, vidéos |

---

## 🆘 Problèmes Courants

### Fichier 404 Not Found

```
GET /static/css/style.css → 404
```

**Causes possibles :**
1. ❌ Fichier n'existe pas
2. ❌ Chemin incorrect
3. ❌ Static pas monté dans main.py

**Solution :**
```python
# Vérifier le montage dans main.py
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Vérifier que le fichier existe
ls -la app/static/css/style.css
```

---

### CSS ne s'applique pas

```html
<link rel="stylesheet" href="/static/css/style.css">
<!-- Styles ne s'appliquent pas -->
```

**Causes possibles :**
1. ❌ Cache navigateur
2. ❌ Ordre de chargement (autre CSS écrase)
3. ❌ Sélecteurs CSS trop faibles

**Solutions :**
```bash
# 1. Vider le cache
Ctrl + Shift + R (Chrome)

# 2. Vérifier l'ordre
# Dernier CSS chargé = prioritaire

# 3. Augmenter la spécificité
.button { color: red; }           # Faible
.navbar .button { color: red; }  # Plus fort
```

---

### JavaScript ne se charge pas

```html
<script src="/static/js/app.js"></script>
<!-- Erreur dans la console -->
```

**Causes possibles :**
1. ❌ Erreur de syntaxe JS
2. ❌ Chemin incorrect
3. ❌ Module ES6 sans type="module"

**Solutions :**
```html
<!-- Si modules ES6 -->
<script type="module" src="/static/js/app.js"></script>

<!-- Vérifier la console navigateur -->
F12 → Console → Voir les erreurs
```

---

## ✨ Résumé

| Aspect | Valeur |
|--------|--------|
| **Rôle** | 🎨 Fichiers qui ne changent pas (CSS, JS, images) |
| **Organisation** | css/, js/, images/, fonts/ |
| **Accès** | `/static/chemin/fichier` |
| **Cache** | Oui (1 an) pour performance |
| **Public** | ✅ Tout est accessible publiquement |
| **Optimisation** | Minification, compression, WebP |

---

## 🎯 Pour Votre Boilerplate

### ✅ À Créer

```bash
# Dossiers manquants
mkdir -p app/static/images
mkdir -p app/static/fonts
mkdir -p app/static/css/components
mkdir -p app/static/css/pages
mkdir -p app/static/js/components

# Fichiers de base
touch app/static/css/base.css
touch app/static/css/theme.css
touch app/static/images/logo.png
touch app/static/images/favicon.ico
```

### 🚀 Réutilisation

```bash
# Copier dans nouveau projet
cp -r app/static/ nouveau_projet/app/static/

# Personnaliser
# - Remplacer logo
# - Modifier theme.css (couleurs)
# - Adapter base.css
```

---

**🎨 Le dossier static = La vitrine visuelle de votre application !**

