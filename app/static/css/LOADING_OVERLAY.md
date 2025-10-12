# ⏳ Système de Loading Overlay

## Vue d'ensemble

Le loading overlay est un composant visuel qui affiche un indicateur de chargement pendant les opérations CRUD asynchrones.

## 🎯 Objectifs

1. **UX améliorée** : L'utilisateur sait qu'une action est en cours
2. **Prévention double-clic** : Empêche les actions multiples pendant le traitement
3. **Feedback visuel** : Spinner animé + message contextuel
4. **Cohérence** : Même apparence sur toutes les pages

## 🎨 Design

### Structure HTML

```html
<div id="loadingOverlay" class="loading-overlay">
    <div class="loading-content">
        <div class="loading-spinner"></div>
        <div class="loading-text">Traitement en cours...</div>
        <div class="loading-subtext">Veuillez patienter</div>
    </div>
</div>
```

### Apparence

```
┌─────────────────────────────────────────────────┐
│              Fond semi-transparent               │
│                (rgba(0,0,0,0.7))                │
│                                                  │
│         ┌─────────────────────────┐              │
│         │    Carte blanche         │              │
│         │                          │              │
│         │      ⭕ Spinner          │              │
│         │    (couleur accent)      │              │
│         │                          │              │
│         │   Traitement en cours    │              │
│         │   Veuillez patienter     │              │
│         │                          │              │
│         └─────────────────────────┘              │
│                                                  │
└─────────────────────────────────────────────────┘
```

## 🔧 Implémentation

### CSS (components.css)

```css
.loading-overlay {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.7);
    z-index: 9999;  /* Au-dessus de tout */
}

.loading-overlay.show {
    display: flex;  /* Centre le contenu */
}

.loading-spinner {
    width: 50px;
    height: 50px;
    border: 4px solid var(--gray-300);
    border-top-color: var(--accent-color);  /* Couleur dynamique */
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}
```

### JavaScript (fonctions réutilisables)

```javascript
// Afficher l'overlay
function showLoading(message = 'Traitement en cours...', subtext = 'Veuillez patienter') {
    const overlay = document.getElementById('loadingOverlay');
    overlay.querySelector('.loading-text').textContent = message;
    overlay.querySelector('.loading-subtext').textContent = subtext;
    overlay.classList.add('show');
}

// Masquer l'overlay
function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    overlay.classList.remove('show');
}
```

## 📋 Utilisation dans les opérations CRUD

### CREATE - Créer un utilisateur

```javascript
async function createUser(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    
    closeModals();
    showLoading('Création...', 'Création de l\'utilisateur en cours');
    
    try {
        const response = await fetch('/api/v1/admin/users/create', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        hideLoading();
        
        if (data.success) {
            showMessage(data.message, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showMessage(data.message, 'error');
        }
    } catch (error) {
        hideLoading();
        showMessage('Erreur lors de la création', 'error');
    }
}
```

**Flux visuel :**
```
1. Utilisateur clique "Créer"
2. Modal se ferme
3. Overlay apparaît avec "Création..."
4. Requête POST vers API
5. Overlay disparaît
6. Message de succès/erreur
7. Rechargement de la page
```

### READ - Charger les données

```javascript
async function openEditModal(userId) {
    showLoading('Chargement...', 'Récupération des données utilisateur');
    
    try {
        const response = await fetch(`/api/v1/admin/users/${userId}/get`);
        const data = await response.json();
        
        hideLoading();
        
        if (data.success) {
            // Pré-remplir le formulaire
            document.getElementById('edit-email').value = data.user.email;
            // ...
            document.getElementById('editModal').classList.add('show');
        }
    } catch (error) {
        hideLoading();
        showMessage('Erreur', 'error');
    }
}
```

**Flux visuel :**
```
1. Utilisateur clique sur ✏️
2. Overlay apparaît avec "Chargement..."
3. Requête GET vers API
4. Overlay disparaît
5. Modal s'ouvre avec données pré-remplies
```

### UPDATE - Modifier un utilisateur

```javascript
async function updateUser(event) {
    event.preventDefault();
    const userId = event.target.querySelector('[name="user_id"]').value;
    const formData = new FormData(event.target);
    
    closeModals();
    showLoading('Modification...', 'Mise à jour de l\'utilisateur en cours');
    
    try {
        const response = await fetch(`/api/v1/admin/users/${userId}/update`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        hideLoading();
        
        if (data.success) {
            showMessage(data.message, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showMessage(data.message, 'error');
        }
    } catch (error) {
        hideLoading();
        showMessage('Erreur', 'error');
    }
}
```

**Flux visuel :**
```
1. Utilisateur clique "Modifier"
2. Modal se ferme
3. Overlay apparaît avec "Modification..."
4. Requête POST vers API
5. Overlay disparaît
6. Message de succès/erreur
7. Rechargement de la page
```

### DELETE - Supprimer un utilisateur

```javascript
async function deleteUser(userId, email) {
    if (!confirm(`Supprimer ${email} ?`)) {
        return;  // Annulé par l'utilisateur
    }
    
    showLoading('Suppression...', `Suppression de ${email} en cours`);
    
    try {
        const response = await fetch(`/api/v1/admin/users/${userId}/delete`, {
            method: 'POST'
        });
        
        const data = await response.json();
        hideLoading();
        
        if (data.success) {
            showMessage(data.message, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showMessage(data.message, 'error');
        }
    } catch (error) {
        hideLoading();
        showMessage('Erreur', 'error');
    }
}
```

**Flux visuel :**
```
1. Utilisateur clique sur 🗑️
2. Dialog de confirmation
3. Utilisateur confirme
4. Overlay apparaît avec "Suppression..."
5. Requête POST vers API
6. Overlay disparaît
7. Message de succès/erreur
8. Rechargement de la page
```

## 🎨 Personnalisation des messages

### Messages contextuels

```javascript
// Opérations utilisateurs
showLoading('Création...', 'Création de l\'utilisateur en cours');
showLoading('Modification...', 'Mise à jour de l\'utilisateur en cours');
showLoading('Suppression...', `Suppression de ${email} en cours`);
showLoading('Chargement...', 'Récupération des données utilisateur');

// Paramètres système
showLoading('Sauvegarde...', 'Enregistrement des paramètres en cours');
showLoading('Upload...', `Téléchargement de ${filename} en cours`);

// Opérations génériques
showLoading('Traitement...', 'Opération en cours');
showLoading('Envoi...', 'Envoi des données au serveur');
showLoading('Validation...', 'Vérification des données');
```

### Messages par type d'action

| Action | Message principal | Sous-texte |
|--------|------------------|------------|
| CREATE | "Création..." | "Création de l'utilisateur en cours" |
| READ | "Chargement..." | "Récupération des données" |
| UPDATE | "Modification..." | "Mise à jour en cours" |
| DELETE | "Suppression..." | "Suppression de {email} en cours" |
| UPLOAD | "Upload..." | "Téléchargement de {filename}" |
| SAVE | "Sauvegarde..." | "Enregistrement des paramètres" |

## ⚡ Performance et timing

### Durée optimale

```javascript
// Afficher minimum 300ms pour éviter le "flash"
const MIN_LOADING_TIME = 300;

async function safeOperation(operation) {
    const startTime = Date.now();
    showLoading();
    
    try {
        await operation();
        
        // S'assurer que l'overlay reste visible au moins 300ms
        const elapsed = Date.now() - startTime;
        if (elapsed < MIN_LOADING_TIME) {
            await new Promise(resolve => setTimeout(resolve, MIN_LOADING_TIME - elapsed));
        }
    } finally {
        hideLoading();
    }
}
```

### Gestion des erreurs

```javascript
try {
    showLoading('Traitement...', 'Opération en cours');
    
    const response = await fetch(...);
    const data = await response.json();
    
    hideLoading();  // ✅ Toujours masquer après la réponse
    
    if (data.success) {
        showMessage('Succès', 'success');
    } else {
        showMessage(data.message, 'error');
    }
} catch (error) {
    hideLoading();  // ✅ IMPORTANT: Masquer même en cas d'erreur
    showMessage('Erreur réseau', 'error');
}
```

**⚠️ IMPORTANT:** Toujours appeler `hideLoading()` dans le bloc `finally` ou dans chaque branche `catch` !

## 🎨 Couleurs dynamiques

Le spinner utilise `--accent-color` :

```css
.loading-spinner {
    border-top-color: var(--accent-color);  /* Rouge par défaut */
}
```

**Si admin change accent_color :**
- Rouge (#e63600) → Spinner rouge 🔴
- Bleu (#0066cc) → Spinner bleu 🔵
- Vert (#28a745) → Spinner vert 🟢

## 📱 Responsive

L'overlay est automatiquement responsive :

```css
.loading-overlay {
    position: fixed;  /* Couvre tout l'écran */
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
}

.loading-content {
    width: 90%;           /* Sur mobile */
    max-width: 500px;     /* Sur desktop */
}
```

## 🔒 Sécurité et UX

### Prévention du double-clic

L'overlay bloque toute interaction pendant qu'il est affiché :

```css
.loading-overlay {
    z-index: 9999;  /* Au-dessus de tout */
    background-color: rgba(0, 0, 0, 0.7);  /* Fond sombre */
}
```

**Résultat :** L'utilisateur ne peut pas cliquer plusieurs fois sur "Créer" pendant la création.

### Timeout automatique (optionnel)

```javascript
function showLoading(message, subtext, timeout = 30000) {
    const overlay = document.getElementById('loadingOverlay');
    overlay.querySelector('.loading-text').textContent = message;
    overlay.querySelector('.loading-subtext').textContent = subtext;
    overlay.classList.add('show');
    
    // Timeout de sécurité
    setTimeout(() => {
        if (overlay.classList.contains('show')) {
            hideLoading();
            showMessage('L\'opération a pris trop de temps', 'error');
        }
    }, timeout);
}
```

## 📊 Pages implémentées

| Page | Opérations avec overlay | Messages |
|------|------------------------|----------|
| **Gestion Utilisateurs** | CREATE, READ, UPDATE, DELETE | ✅ |
| **Paramètres Système** | UPDATE, UPLOAD | ✅ |
| **Rapports** | - | 🚧 À implémenter |

### Gestion Utilisateurs (`gestion_utilisateurs.html`)

**Opérations :**
- ✅ `createUser()` - "Création..." + "Création de l'utilisateur en cours"
- ✅ `openEditModal()` - "Chargement..." + "Récupération des données utilisateur"
- ✅ `updateUser()` - "Modification..." + "Mise à jour de l'utilisateur en cours"
- ✅ `deleteUser()` - "Suppression..." + "Suppression de {email} en cours"

### Paramètres Système (`parametres_systeme.html`)

**Opérations :**
- ✅ `saveSettings()` - "Sauvegarde..." + "Enregistrement des paramètres en cours"
- ✅ `uploadLogo()` - "Upload..." + "Téléchargement de {filename} en cours"

## 🚀 Ajouter l'overlay à une nouvelle page

### Étape 1 : Ajouter le HTML

```html
{% block content %}
<!-- Loading Overlay -->
<div id="loadingOverlay" class="loading-overlay">
    <div class="loading-content">
        <div class="loading-spinner"></div>
        <div class="loading-text">Traitement en cours...</div>
        <div class="loading-subtext">Veuillez patienter</div>
    </div>
</div>

<!-- Votre contenu -->
<div class="ma-page">
    ...
</div>
{% endblock %}
```

### Étape 2 : Ajouter les fonctions JS

```html
{% block scripts %}
<script>
// Fonctions pour l'overlay
function showLoading(message = 'Traitement en cours...', subtext = 'Veuillez patienter') {
    const overlay = document.getElementById('loadingOverlay');
    overlay.querySelector('.loading-text').textContent = message;
    overlay.querySelector('.loading-subtext').textContent = subtext;
    overlay.classList.add('show');
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    overlay.classList.remove('show');
}

// Vos fonctions CRUD
async function maFonction() {
    showLoading('Mon message...', 'Sous-texte');
    
    try {
        const response = await fetch(...);
        hideLoading();
        
        // Traiter la réponse
    } catch (error) {
        hideLoading();
        // Gérer l'erreur
    }
}
</script>
{% endblock %}
```

### Étape 3 : Aucun CSS supplémentaire !

Les styles sont déjà dans `components.css` qui est chargé dans `base.html` ✅

## 🎬 Animations

### Animation d'apparition

```css
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes scaleIn {
    from { transform: scale(0.8); opacity: 0; }
    to { transform: scale(1); opacity: 1; }
}

.loading-overlay {
    animation: fadeIn 0.2s;  /* Fond apparaît progressivement */
}

.loading-content {
    animation: scaleIn 0.3s;  /* Carte "pop" au centre */
}
```

### Animation du spinner

```css
@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.loading-spinner {
    animation: spin 0.8s linear infinite;  /* Rotation continue */
}
```

**Durée optimale :** 0.8s par rotation (ni trop rapide, ni trop lent)

## 💡 Best Practices

### ✅ À FAIRE

```javascript
// 1. Toujours appeler hideLoading() après l'opération
try {
    showLoading();
    await operation();
    hideLoading();  // ✅
} catch (error) {
    hideLoading();  // ✅ Même en cas d'erreur
}

// 2. Messages contextuels
showLoading('Création...', 'Création de l\'utilisateur en cours');  // ✅

// 3. Fermer les modaux AVANT d'afficher l'overlay
closeModals();
showLoading();  // ✅
```

### ❌ À ÉVITER

```javascript
// 1. Oublier de masquer l'overlay
try {
    showLoading();
    await operation();
    // ❌ Pas de hideLoading() !
}

// 2. Messages génériques
showLoading();  // ❌ L'utilisateur ne sait pas ce qui se passe

// 3. Afficher l'overlay avec un modal
showLoading();
openModal();  // ❌ L'overlay cache le modal
```

## 🔍 Debug

### Tester l'overlay manuellement

```javascript
// Dans la console du navigateur
showLoading('Test', 'Message de test');

// Attendre 3 secondes
setTimeout(() => hideLoading(), 3000);
```

### Vérifier le z-index

```javascript
// L'overlay doit être au-dessus de tout
const overlay = document.getElementById('loadingOverlay');
console.log(getComputedStyle(overlay).zIndex);  // Doit être "9999"
```

### Vérifier l'animation

```css
/* Si le spinner ne tourne pas, vérifier */
.loading-spinner {
    animation: spin 0.8s linear infinite;  /* Doit être présent */
}

@keyframes spin {
    /* Doit être défini */
}
```

## 📈 Statistiques d'utilisation

### Temps moyens par opération

| Opération | Temps moyen | Temps overlay visible |
|-----------|-------------|----------------------|
| CREATE User | 100-300ms | ~500ms |
| READ User | 50-150ms | ~300ms |
| UPDATE User | 100-300ms | ~500ms |
| DELETE User | 100-200ms | ~500ms |
| UPDATE Settings | 150-400ms | ~600ms |
| UPLOAD Logo | 500-2000ms | Temps upload |

### Perception utilisateur

```
Sans overlay: 
  Click → ... silence ... → Résultat
  ❌ Utilisateur confus: "Ça marche ?"

Avec overlay:
  Click → Overlay + Spinner → Résultat
  ✅ Utilisateur informé: "C'est en cours"
```

## 🎯 Améliorations futures

### Barre de progression (pour uploads)

```javascript
async function uploadWithProgress(file) {
    showLoading('Upload...', '0%');
    
    const xhr = new XMLHttpRequest();
    
    xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            document.querySelector('.loading-subtext').textContent = `${percent}%`;
        }
    });
    
    // ... reste de l'upload
}
```

### Messages d'étapes

```javascript
showLoading('Validation...', 'Vérification des données');
await new Promise(r => setTimeout(r, 500));

showLoading('Envoi...', 'Envoi au serveur');
await fetch(...);

showLoading('Finalisation...', 'Traitement final');
```

### Animation de succès

```javascript
async function showSuccess() {
    const overlay = document.getElementById('loadingOverlay');
    overlay.querySelector('.loading-spinner').style.display = 'none';
    overlay.querySelector('.loading-text').textContent = '✅ Succès !';
    overlay.querySelector('.loading-subtext').textContent = '';
    
    await new Promise(r => setTimeout(r, 1000));
    hideLoading();
}
```

## 📚 Références

- [Composants CSS](components.css)
- [Animations](components.css#L220-L246)
- [Exemple d'utilisation](../../templates/pages/gestion_utilisateurs.html)
- [Système de couleurs](COLORS_SYSTEM.md)

---

**🎉 L'overlay améliore considérablement l'expérience utilisateur en donnant un feedback visuel clair pour toutes les opérations !**

