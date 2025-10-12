# 🎨 Système de Couleurs Dynamiques - Flux Complet

## 📊 Vue d'ensemble du système

Le système de couleurs utilise une architecture à **3 couches** avec cache et fallback automatique :

```
┌─────────────────────────────────────────────────────────────┐
│  COUCHE 1: Base de données (system_settings table)         │
│  ├─ Valeurs personnalisées par l'admin                      │
│  ├─ Cache de 5 minutes pour performance                     │
│  └─ Priorité HAUTE                                          │
└─────────────────────────────────────────────────────────────┘
                          ↓ (si erreur ou vide)
┌─────────────────────────────────────────────────────────────┐
│  COUCHE 2: Configuration (config.py + .env)                 │
│  ├─ Variables d'environnement                               │
│  ├─ APP_NAME, DEBUG, etc.                                   │
│  └─ Priorité MOYENNE                                        │
└─────────────────────────────────────────────────────────────┘
                          ↓ (si pas défini)
┌─────────────────────────────────────────────────────────────┐
│  COUCHE 3: Valeurs hardcodées (theme.css)                  │
│  ├─ Valeurs CSS par défaut                                  │
│  ├─ #ffd300, #036c1d, etc.                                  │
│  └─ Priorité BASSE (fallback final)                        │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Flux complet - De la base de données à l'affichage

### ÉTAPE 1 : Démarrage de l'application 🚀

```
┌─────────────────────────────────────────────────────────────┐
│  app/main.py - Événement startup                            │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│  scripts/init_db.py::initialize_database()                  │
│  1. Créer les tables                                        │
│  2. initialize_system_settings() ─┐                         │
│     └─ SystemSettingsService.get_settings()                 │
│        └─ Si table vide: INSERT avec APP_NAME depuis config │
│        └─ Sinon: Utiliser valeurs existantes               │
│  3. Créer admin si besoin                                   │
└─────────────────────────────────────────────────────────────┘

Résultat: 
✅ Table system_settings existe avec ID=1
✅ company_name = "MPPEEP Dashboard" (depuis config.py)
✅ primary_color = "#ffd300"
✅ secondary_color = "#036c1d"
✅ accent_color = "#e63600"
```

### ÉTAPE 2 : Requête HTTP arrive 📨

```
┌─────────────────────────────────────────────────────────────┐
│  Utilisateur visite: http://localhost:8000/accueil          │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│  app/main.py::accueil(request)                              │
│  return templates.TemplateResponse(                         │
│      "pages/accueil.html",                                  │
│      get_template_context(request, ...)  ←─────┐            │
│  )                                              │            │
└─────────────────────────────────────────────────┼───────────┘
                                                  │
                  ┌───────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│  app/templates/__init__.py::get_template_context()         │
│                                                              │
│  1. Charger current_user (depuis cookie session)            │
│  2. Charger system_settings ─────────┐                      │
│                                       ↓                      │
│     SystemSettingsService.get_settings_as_dict(db)          │
│     ├─ Vérifier cache ─────────┐                            │
│     │                           ↓                            │
│     │  ┌──────────────────────────────────────┐             │
│     │  │ settings_cache.get()                  │             │
│     │  │ Cache valide (< 5 min) ?             │             │
│     │  │ OUI → Return cached data ✅          │             │
│     │  │ NON → Continue ↓                     │             │
│     │  └──────────────────────────────────────┘             │
│     │                                                        │
│     ├─ Charger depuis DB ───────┐                           │
│     │                            ↓                           │
│     │  SELECT * FROM system_settings WHERE id = 1           │
│     │  ├─ Existe → Utiliser ces valeurs                     │
│     │  │   ├─ primary_color: "#ffd300"                      │
│     │  │   ├─ Calculer primary_dark (10% darker)            │
│     │  │   ├─ Calculer primary_light (20% lighter)          │
│     │  │   └─ Mettre en cache ✅                           │
│     │  └─ Erreur → get_default_settings()                   │
│     │              └─ Utilise APP_NAME depuis config.py     │
│     │                                                        │
│     └─ Return dict avec toutes les valeurs                  │
│                                                              │
│  3. Construire contexte:                                    │
│     {                                                        │
│       "request": request,                                    │
│       "app_name": system_settings["company_name"],          │
│       "current_user": {...},                                │
│       "system_settings": {                                  │
│         "company_name": "MPPEEP Dashboard",                 │
│         "primary_color": "#ffd300",                         │
│         "secondary_color": "#036c1d",                       │
│         "accent_color": "#e63600",                          │
│         "primary_dark": "#e6be00",   ← Calculé             │
│         "primary_light": "#ffe664",  ← Calculé             │
│         "logo_path": "images/logo.jpg",                     │
│         ...                                                  │
│       }                                                      │
│     }                                                        │
└─────────────────────────────────────────────────────────────┘
```

### ÉTAPE 3 : Rendu du template 🎨

```
┌─────────────────────────────────────────────────────────────┐
│  Jinja2 Template Engine                                     │
│                                                              │
│  1. Étend layouts/base.html                                 │
│     └─ Charge CSS dans <head>:                              │
│        ├─ base.css (reset)                                  │
│        ├─ theme.css (variables par défaut)                  │
│        └─ components.css (composants)                       │
│                                                              │
│  2. Injection dynamique des couleurs:                       │
│     {% if system_settings %}                                │
│     <style>                                                  │
│         :root {                                              │
│             --primary-color: #ffd300;     ← Depuis DB       │
│             --secondary-color: #036c1d;   ← Depuis DB       │
│             --accent-color: #e63600;      ← Depuis DB       │
│             --primary-dark: #e6be00;      ← Calculé         │
│             --primary-light: #ffe664;     ← Calculé         │
│         }                                                    │
│     </style>                                                 │
│     {% endif %}                                              │
│                                                              │
│     ⚠️  IMPORTANT: Ce <style> vient APRÈS theme.css        │
│         donc il ÉCRASE les valeurs par défaut !             │
│                                                              │
│  3. Rendu du contenu:                                       │
│     <nav class="navbar">                                    │
│       <!-- background: var(--secondary-color) -->           │
│       <!-- Utilise #036c1d depuis DB -->                    │
│     </nav>                                                   │
│                                                              │
│     <div class="action-button">                             │
│       <!-- background: var(--secondary-color) -->           │
│       <!-- hover: var(--primary-dark) -->                   │
│       <!-- Utilise couleurs calculées ! -->                 │
│     </div>                                                   │
└─────────────────────────────────────────────────────────────┘
```

### ÉTAPE 4 : Affichage dans le navigateur 🖥️

```
┌─────────────────────────────────────────────────────────────┐
│  Navigateur reçoit le HTML                                  │
│                                                              │
│  1. Parse le CSS:                                           │
│     /* theme.css - Valeurs par défaut */                    │
│     :root {                                                  │
│       --primary-color: #ffd300;                             │
│       --secondary-color: #036c1d;                           │
│     }                                                        │
│                                                              │
│     /* Ensuite, le <style> inline */                        │
│     :root {                                                  │
│       --primary-color: #ffd300;      ← ÉCRASE défaut        │
│       --secondary-color: #036c1d;    ← ÉCRASE défaut        │
│       --primary-dark: #e6be00;       ← NOUVELLE valeur      │
│       --primary-light: #ffe664;      ← NOUVELLE valeur      │
│     }                                                        │
│                                                              │
│  2. Calcule les styles finaux:                              │
│     .navbar {                                                │
│       background-color: var(--secondary-color);             │
│       /* Résolu: #036c1d */                                 │
│     }                                                        │
│                                                              │
│     .action-button:hover {                                  │
│       background-color: var(--accent-color);                │
│       /* Résolu: #e63600 (Rouge accent) */                  │
│     }                                                        │
│                                                              │
│  3. Applique les styles:                                    │
│     ✅ Navbar verte (#036c1d)                               │
│     ✅ Boutons avec fond secondaire (#036c1d)               │
│     ✅ Hover ROUGE ACCENT (#e63600) 🔥                      │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Flux de modification par l'admin

### Scénario : Admin change la couleur principale en rouge

```
ÉTAPE 1: Admin ouvre Paramètres Système
├─ GET /api/v1/admin/parametres-systeme
├─ Charge system_settings depuis cache/DB
└─ Affiche formulaire avec color picker

ÉTAPE 2: Admin sélectionne rouge (#ff0000)
├─ Color picker mis à jour
└─ Affichage du code hex à côté

ÉTAPE 3: Admin clique "Enregistrer"
├─ POST /api/v1/admin/settings/update
│  FormData: { primary_color: "#ff0000" }
│
├─ admin.py::update_system_settings()
│  ├─ SystemSettingsService.update_settings(
│  │    db_session=session,
│  │    user_id=current_user.id,
│  │    primary_color="#ff0000"
│  │  )
│  │
│  ├─ UPDATE system_settings 
│  │   SET primary_color = '#ff0000',
│  │       updated_at = NOW(),
│  │       updated_by_user_id = 1
│  │   WHERE id = 1;
│  │
│  └─ settings_cache.clear()  ← CACHE VIDÉ !
│
└─ Response: {"success": true, "message": "..."}

ÉTAPE 4: Admin recharge la page /accueil
├─ GET /accueil
│
├─ get_template_context(request)
│  └─ SystemSettingsService.get_settings_as_dict(db)
│     ├─ Cache vide (car vidé à l'étape 3)
│     │
│     ├─ SELECT * FROM system_settings WHERE id = 1
│     │  └─ primary_color = "#ff0000"  ✅ Nouvelle valeur !
│     │
│     ├─ Calculer couleurs dérivées:
│     │  ├─ primary_dark = darken("#ff0000", 0.1)
│     │  │  └─ Résultat: "#e60000"
│     │  └─ primary_light = lighten("#ff0000", 0.2)
│     │     └─ Résultat: "#ff3333"
│     │
│     └─ Mettre en cache pour 5 minutes
│
├─ Template reçoit:
│  system_settings = {
│    "primary_color": "#ff0000",      ← ROUGE !
│    "primary_dark": "#e60000",       ← ROUGE FONCÉ
│    "primary_light": "#ff3333",      ← ROUGE CLAIR
│    ...
│  }
│
└─ Rendu HTML avec injection:
   <style>
       :root {
           --primary-color: #ff0000;    ← ROUGE !
           --primary-dark: #e60000;
           --primary-light: #ff3333;
       }
   </style>

ÉTAPE 5: Navigateur affiche avec nouvelles couleurs
├─ Navbar: couleur secondaire (inchangée)
├─ Boutons: background secondaire (vert #036c1d)
├─ Hover: background ACCENT COLOR (#e63600) 🔥
│  └─ TOUS les boutons ont le même hover avec accent-color
└─ Cohérence visuelle parfaite sur toute l'application ! ✨
```

## 📁 Architecture des fichiers

### 1. Base de données (Stockage)

**Fichier:** `app/models/system_settings.py`

```python
class SystemSettings(SQLModel, table=True):
    id: int = 1  # Singleton
    primary_color: str = "#ffd300"
    secondary_color: str = "#036c1d"
    accent_color: str = "#e63600"
    ...
```

**Table SQL:**
```sql
CREATE TABLE system_settings (
    id INTEGER PRIMARY KEY,
    primary_color VARCHAR(7),
    secondary_color VARCHAR(7),
    accent_color VARCHAR(7),
    ...
);

-- Exemple de données
INSERT INTO system_settings VALUES (
    1,                    -- id
    '#ffd300',           -- primary_color (jaune)
    '#036c1d',           -- secondary_color (vert)
    '#e63600',           -- accent_color (rouge)
    ...
);
```

### 2. Service (Logique métier)

**Fichier:** `app/services/system_settings_service.py`

```python
class SystemSettingsService:
    
    # Récupère depuis DB (ou crée si vide)
    def get_settings(db_session) -> SystemSettings
    
    # Met à jour et vide le cache
    def update_settings(db_session, user_id, **kwargs) -> SystemSettings
    
    # Convertit en dict + cache (5 min)
    def get_settings_as_dict(db_session) -> Dict
    
    # Fallback si DB inaccessible
    def get_default_settings() -> Dict
    
    # Calcule couleurs dérivées
    def lighten_color(hex, percent) -> str
    def darken_color(hex, percent) -> str
```

**Flux dans get_settings_as_dict() :**
```python
def get_settings_as_dict(db_session):
    # 1. Vérifier cache
    cached = settings_cache.get()
    if cached:
        return cached  # ⚡ Retour immédiat
    
    # 2. Charger depuis DB
    try:
        settings = get_settings(db_session)
        
        result = {
            "primary_color": settings.primary_color,
            "primary_dark": darken_color(settings.primary_color, 0.1),
            "primary_light": lighten_color(settings.primary_color, 0.2),
            ...
        }
        
        # 3. Mettre en cache
        settings_cache.set(result)
        return result
        
    except Exception:
        # 4. Fallback
        return get_default_settings()
```

### 3. Cache (Performance)

**Fichier:** `app/core/settings_cache.py`

```python
class SettingsCache:
    _settings: Dict = None
    _last_update: datetime = None
    _cache_duration: int = 300  # 5 minutes
    
    def get() -> Dict | None
    def set(settings: Dict)
    def clear()
```

**Timeline du cache:**
```
T=0s    → Requête 1: Cache vide → SELECT DB → Met en cache
T=10s   → Requête 2: Cache HIT → Return cache (pas de SELECT)
T=60s   → Requête 3: Cache HIT → Return cache
T=120s  → Requête 4: Cache HIT → Return cache
T=300s  → Requête 5: Cache EXPIRÉ → SELECT DB → Met en cache
T=Admin → Modification → Cache VIDÉ → Prochaine requête charge de DB
```

### 4. Context Processor (Distribution)

**Fichier:** `app/templates/__init__.py`

```python
def get_template_context(request, **kwargs):
    # Charge system_settings
    system_settings = SystemSettingsService.get_settings_as_dict(db)
    
    return {
        "request": request,
        "app_name": system_settings["company_name"],  # ← Utilise DB !
        "system_settings": system_settings,            # ← Dict complet
        "current_user": {...},
        **kwargs
    }
```

**Résultat:** Toutes les routes qui utilisent `get_template_context()` ont accès à `system_settings`.

### 5. Template de base (Injection CSS)

**Fichier:** `app/templates/layouts/base.html`

```html
<!-- Ordre de chargement des CSS -->
<link rel="stylesheet" href="/static/css/base.css">     <!-- Priorité 1 -->
<link rel="stylesheet" href="/static/css/theme.css">    <!-- Priorité 2 -->
<link rel="stylesheet" href="/static/css/components.css"> <!-- Priorité 3 -->

<!-- Override dynamique (PRIORITÉ MAXIMALE) -->
{% if system_settings %}
<style>
    :root {
        --primary-color: {{ system_settings.primary_color }};      ← ÉCRASE theme.css
        --secondary-color: {{ system_settings.secondary_color }};  ← ÉCRASE theme.css
        --accent-color: {{ system_settings.accent_color }};        ← ÉCRASE theme.css
        --primary-dark: {{ system_settings.primary_dark }};        ← NOUVEAU
        --primary-light: {{ system_settings.primary_light }};      ← NOUVEAU
    }
</style>
{% endif %}
```

**Ordre de priorité CSS (spécificité):**
```
1. theme.css:        :root { --primary-color: #ffd300; }
2. <style> inline:   :root { --primary-color: #ff0000; }  ← GAGNE !

Résultat final: --primary-color = #ff0000
```

### 6. Fichiers CSS (Utilisation)

**theme.css** - Variables par défaut
```css
:root {
  --primary-color: #ffd300;     /* Défaut jaune */
  --secondary-color: #036c1d;   /* Défaut vert */
  --accent-color: #e63600;      /* Défaut rouge */
  --primary-dark: #e6be00;      /* Défaut jaune foncé */
  --primary-light: #ffe664;     /* Défaut jaune clair */
}

/* Utilisation dans les composants */
.action-button {
  background-color: var(--secondary-color);  /* Vert */
}

.action-button:hover {
  background-color: var(--accent-color);     /* Rouge accent ✨ */
  color: var(--white-color);
}

.stat-value {
  color: var(--secondary-color);             /* Vert */
}
```

**components.css** - Composants réutilisables
```css
.alert-success {
  background-color: var(--success-light);
  color: var(--success-dark);
}

.badge-admin {
  background-color: var(--danger-color);
}

.modal {
  /* Utilise les variables partout */
}
```

## 🎯 Résolution CSS finale dans le navigateur

```
1. Le navigateur parse tous les CSS dans l'ordre
2. Pour chaque variable, la DERNIÈRE définition gagne
3. Cascade de résolution:

   Exemple pour --primary-color:
   
   theme.css définit:      --primary-color: #ffd300
   <style> override:       --primary-color: #ff0000  ← GAGNE !
   
   Quand CSS utilise:      background: var(--primary-color);
   Résolution finale:      background: #ff0000;  ✅

4. Les var() sont résolues dynamiquement:
   - Changement de --primary-color dans DevTools → Tout change !
   - C'est le principe des Custom Properties CSS
```

## 🔍 Debugging - Vérifier les couleurs

### Dans le navigateur (Console DevTools)

```javascript
// Récupérer les couleurs actives
const root = document.documentElement;
const styles = getComputedStyle(root);

console.log('PRIMARY:', styles.getPropertyValue('--primary-color'));
// Résultat: " #ff0000" (avec espace)

console.log('SECONDARY:', styles.getPropertyValue('--secondary-color'));
console.log('PRIMARY DARK:', styles.getPropertyValue('--primary-dark'));
console.log('PRIMARY LIGHT:', styles.getPropertyValue('--primary-light'));
```

### Vérifier la source (HTML)

```html
<!-- Inspecter l'élément <head> -->
<style>
    :root {
        --primary-color: #ff0000;     ← Doit être la couleur DB
        --secondary-color: #036c1d;
        --accent-color: #e63600;
        --primary-dark: #e60000;      ← Doit être calculée
        --primary-light: #ff3333;     ← Doit être calculée
    }
</style>
```

### Vérifier la base de données

```bash
# SQLite
sqlite3 mppeep/app.db
SELECT primary_color, secondary_color, accent_color FROM system_settings WHERE id = 1;

# PostgreSQL
psql -d mppeep_db
SELECT primary_color, secondary_color, accent_color FROM system_settings WHERE id = 1;
```

### Vérifier le cache

```python
# Dans la console Python (pour debug)
from app.core.settings_cache import settings_cache

# Voir le cache actuel
print(settings_cache.get())

# Vider le cache manuellement
settings_cache.clear()
```

## ⚡ Performance et optimisation

### Métriques

**Sans cache:**
```
100 requêtes/sec
× 1 SELECT system_settings par requête
= 100 queries DB/sec ❌
```

**Avec cache (5 minutes):**
```
100 requêtes/sec
× 0 queries (cache hit)
= 0 queries DB/sec ✅

Recharge: 1 query toutes les 5 minutes
= 0.0033 queries/sec
```

**Gain:** ~99.99% de requêtes en moins ! 🚀

### Timeline typique

```
09:00:00 - Requête 1  → Cache MISS → SELECT DB → primary_color: #ffd300
09:00:01 - Requête 2  → Cache HIT  → Return #ffd300
09:00:02 - Requête 3  → Cache HIT  → Return #ffd300
...
09:04:59 - Requête N  → Cache HIT  → Return #ffd300
09:05:00 - Requête N+1 → Cache EXPIRÉ → SELECT DB → primary_color: #ffd300

09:03:30 - Admin modifie → Cache VIDÉ
09:03:31 - Requête suivante → Cache MISS → SELECT DB → primary_color: #ff0000 ✅
```

## 🛡️ Robustesse et fallback

### Scénario 1: Base de données inaccessible

```python
try:
    settings = get_settings(db_session)
    # SUCCESS: Utilise valeurs DB
except Exception:
    # FALLBACK: Utilise valeurs par défaut
    return {
        "company_name": settings.APP_NAME,  # ← Depuis .env
        "primary_color": "#ffd300",         # ← Hardcodé
        ...
    }
```

### Scénario 2: Table vide (première installation)

```python
settings = db_session.get(SystemSettings, 1)
if not settings:
    # Créer avec valeurs depuis config
    settings = SystemSettings(
        id=1,
        company_name=app_settings.APP_NAME  # ← Depuis .env
    )
    db_session.add(settings)
    db_session.commit()
```

### Scénario 3: Corruption des données

```python
def lighten_color(hex_color, percent):
    try:
        # Calcul de la couleur
        ...
    except:
        return hex_color  # ← Retourne couleur originale
```

## 📝 Checklist - S'assurer que tout fonctionne

### ✅ Vérifications à faire

1. **DB initialisée**
   ```bash
   sqlite3 mppeep/app.db ".tables"
   # Doit afficher: system_settings, user, user_sessions
   ```

2. **Paramètres en DB**
   ```bash
   sqlite3 mppeep/app.db "SELECT * FROM system_settings;"
   # Doit afficher 1 ligne avec ID=1
   ```

3. **Cache fonctionne**
   - Modifier une couleur
   - Recharger immédiatement → Nouvelle couleur ✅
   - Attendre 6 minutes sans modification
   - Recharger → Même couleur (depuis DB) ✅

4. **Fallback fonctionne**
   - Renommer app.db temporairement
   - Recharger la page
   - Doit afficher avec couleurs par défaut ✅
   - Restaurer app.db

5. **Toutes les pages utilisent les couleurs**
   - `/accueil` → Boutons jaunes/rouges selon config ✅
   - `/api/v1/admin/gestion-utilisateurs` → Badges colorés ✅
   - `/api/v1/admin/parametres-systeme` → Form avec preview ✅
   - `/api/v1/login` → Bouton primary-color ✅

## 🎨 Système des Hovers avec Accent Color

### Philosophie du design

**Tous les boutons utilisent `--accent-color` au hover pour une cohérence visuelle maximale.**

### Mapping des couleurs par type de bouton

| Type de bouton | État normal | État hover | Texte hover |
|----------------|-------------|------------|-------------|
| `.btn-primary` | `--white-color` (blanc) | `--accent-color` (rouge) | `--white-color` |
| `.btn-secondary` | `--secondary-color` (vert) | `--accent-color` (rouge) | `--white-color` |
| `.btn-outline` | Transparent | `--accent-color` (rouge) | `--white-color` |
| `.action-button` | `--secondary-color` (vert) | `--accent-color` (rouge) | `--white-color` |
| `.btn-recovery` | `--primary-color` (jaune) | `--accent-color` (rouge) | `--white-color` |
| `.btn-verify` | `--primary-color` (jaune) | `--accent-color` (rouge) | `--white-color` |
| `.btn-reset` | `--primary-color` (jaune) | `--accent-color` (rouge) | `--white-color` |

### Avantages de ce système

1. **🎯 Cohérence** : Tous les hovers ont la même couleur
2. **🎨 Personnalisable** : Changez `accent_color` en DB → Tous les hovers changent
3. **👀 Visibilité** : La couleur d'accent attire l'attention sur l'interaction
4. **♿ Accessibilité** : Feedback visuel clair pour les utilisateurs

### Exemple de code

```css
/* theme.css */
.btn-primary {
    background-color: var(--white-color);      /* Blanc */
    color: var(--secondary-color);             /* Vert */
}

.btn-primary:hover {
    background-color: var(--accent-color);     /* Rouge (DB) */
    color: var(--white-color);                 /* Blanc */
}

.action-button {
    background-color: var(--secondary-color);  /* Vert */
    color: var(--white-color);                 /* Blanc */
}

.action-button:hover {
    background-color: var(--accent-color);     /* Rouge (DB) */
    color: var(--white-color);                 /* Blanc */
}
```

### Résultat visuel

**Configuration par défaut :**
```
Bouton normal:  Fond vert (#036c1d) + Texte blanc
                     ↓ (hover)
Bouton hover:   Fond rouge (#e63600) + Texte blanc 🔥
```

**Si admin change accent_color en orange (#ff6600) :**
```
Bouton normal:  Fond vert (#036c1d) + Texte blanc
                     ↓ (hover)
Bouton hover:   Fond orange (#ff6600) + Texte blanc 🧡
```

## 🎨 Variables CSS complètes

### Variables personnalisables (depuis DB)

| Variable CSS | Source | Calcul |
|--------------|--------|--------|
| `--primary-color` | `system_settings.primary_color` | Direct | Couleur principale (boutons, textes importants) |
| `--primary-dark` | Calculé | `darken(primary, 10%)` | Variante sombre de la couleur principale |
| `--primary-light` | Calculé | `lighten(primary, 20%)` | Variante claire de la couleur principale |
| `--secondary-color` | `system_settings.secondary_color` | Direct | Couleur secondaire (navbar, titres) |
| `--accent-color` | `system_settings.accent_color` | Direct | **Couleur d'accent (HOVERS de tous les boutons)** |

### Variables système (fixes)

| Variable | Valeur | Usage |
|----------|--------|-------|
| `--success-color` | #28a745 | Messages de succès |
| `--error-color` | #dc3545 | Messages d'erreur |
| `--warning-color` | #ffc107 | Avertissements |
| `--info-color` | #17a2b8 | Informations |
| `--gray-xxx` | Palette grise | Textes, bordures, fonds |

## 🔧 Modification des couleurs

### Via l'interface (recommandé)

```
1. Login en tant qu'admin
2. Aller dans "Paramètres Système"
3. Section "Palette de Couleurs"
4. Utiliser les color pickers
5. Cliquer "Enregistrer"
6. Recharger n'importe quelle page
7. ✅ Nouvelles couleurs partout !
```

### Via la base de données

```sql
-- Modifier directement en DB
UPDATE system_settings 
SET primary_color = '#ff6600',      -- Orange
    secondary_color = '#0066cc',    -- Bleu
    accent_color = '#cc0066'        -- Magenta
WHERE id = 1;

-- Ensuite, vider le cache (redémarrer l'app ou attendre 5 min)
```

### Via le code (programmation)

```python
from app.services.system_settings_service import SystemSettingsService

# Dans une route ou un script
SystemSettingsService.update_settings(
    db_session=db,
    user_id=admin.id,
    primary_color="#ff6600",
    secondary_color="#0066cc"
)
# ✅ Cache vidé automatiquement
```

## 🚀 Exemples d'utilisation avancée

### Exemple 1: Mode sombre dynamique

```python
# Ajouter dans system_settings
dark_mode: bool = Field(default=False)

# Dans get_settings_as_dict()
if settings.dark_mode:
    result["secondary_color"] = "#1a1a1a"  # Fond sombre
    result["primary_color"] = "#ffd700"    # Jaune plus vif
```

### Exemple 2: Thèmes prédéfinis

```python
THEMES = {
    "default": {"primary": "#ffd300", "secondary": "#036c1d"},
    "ocean": {"primary": "#00bcd4", "secondary": "#0097a7"},
    "sunset": {"primary": "#ff6f00", "secondary": "#e65100"},
}

# Appliquer un thème
theme = THEMES["ocean"]
SystemSettingsService.update_settings(
    db_session=db,
    user_id=admin.id,
    **theme
)
```

### Exemple 3: Branding par client

```python
# Pour une app multi-tenant
client_settings = {
    "client_a": {"company_name": "Entreprise A", "primary_color": "#ff0000"},
    "client_b": {"company_name": "Entreprise B", "primary_color": "#0000ff"},
}

# Charger selon le client
settings = client_settings[current_client]
```

## 📊 Schéma récapitulatif

```
┌─────────────────────────────────────────────────────────────┐
│                    REQUÊTE HTTP                              │
└────────────────────┬────────────────────────────────────────┘
                     ↓
    ┌────────────────────────────────────────────┐
    │      get_template_context()                │
    └───────────────┬────────────────────────────┘
                    ↓
    ┌────────────────────────────────────────────┐
    │  SystemSettingsService.get_settings_as_dict│
    └───────────────┬────────────────────────────┘
                    ↓
         ┌──────────┴──────────┐
         │   Cache valide ?     │
         └──────┬────────┬──────┘
               OUI      NON
                │        │
                │        ↓
                │  ┌─────────────────┐
                │  │  SELECT DB       │
                │  │  + Calculer      │
                │  │  + Mettre cache  │
                │  └────────┬─────────┘
                │           │
                ↓           ↓
         ┌──────────────────────┐
         │  Return dict avec:   │
         │  - primary_color     │
         │  - primary_dark      │
         │  - primary_light     │
         │  - ...               │
         └──────────┬───────────┘
                    ↓
         ┌──────────────────────┐
         │  Template reçoit     │
         │  system_settings     │
         └──────────┬───────────┘
                    ↓
         ┌──────────────────────┐
         │  base.html injecte   │
         │  <style> avec        │
         │  nouvelles valeurs   │
         └──────────┬───────────┘
                    ↓
         ┌──────────────────────┐
         │  CSS appliqué avec   │
         │  var(--primary-color)│
         └──────────┬───────────┘
                    ↓
         ┌──────────────────────┐
         │  AFFICHAGE FINAL     │
         │  avec couleurs DB    │
         └──────────────────────┘
```

## 🔬 Tests et validation

### Test 1: Vérifier l'injection

```bash
# Démarrer l'app
uvicorn app.main:app --reload

# Ouvrir http://localhost:8000/accueil
# Inspecter <head>
# Chercher <style> avec :root
# Vérifier que les couleurs sont présentes
```

### Test 2: Modifier et vérifier

```bash
1. Aller dans Paramètres Système
2. Changer primary_color en #ff0000 (rouge)
3. Sauvegarder
4. Ouvrir console navigateur:
   > getComputedStyle(document.documentElement).getPropertyValue('--primary-color')
   " #ff0000"  ✅
5. Recharger /accueil
6. Les boutons doivent être ROUGES
```

### Test 3: Performance du cache

```python
# Dans un script Python
import time
from app.services.system_settings_service import SystemSettingsService
from app.db.session import Session, engine

with Session(engine) as db:
    # 1er appel - DB
    start = time.time()
    s1 = SystemSettingsService.get_settings_as_dict(db)
    print(f"1er appel: {time.time() - start:.4f}s")  # ~0.0100s
    
    # 2ème appel - Cache
    start = time.time()
    s2 = SystemSettingsService.get_settings_as_dict(db)
    print(f"2ème appel: {time.time() - start:.4f}s")  # ~0.0001s
    
    # Cache 100x plus rapide ! ⚡
```

## 📚 Références

- [Modèle](../../../models/system_settings.py)
- [Service](../../../services/system_settings_service.py)
- [Cache](../../../core/settings_cache.py)
- [Context Processor](../../../templates/__init__.py)
- [Routes Admin](../../../api/v1/endpoints/admin.py)

---

**🎉 Le système est conçu pour être robuste, performant et facile à utiliser !**
