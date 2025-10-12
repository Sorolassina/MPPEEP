# ⚙️ Utilisation des Paramètres Système

## 🎯 Vue d'ensemble

Le système de paramètres permet de personnaliser l'application via l'interface web. Les valeurs sont stockées en base de données et s'appliquent automatiquement à toute l'application.

## 📊 Hiérarchie des valeurs

```
1. Paramètres en Base de Données (priorité haute)
   ↓ (si pas de valeur en DB ou erreur)
2. Variables d'environnement / config.py (fallback)
   ↓ (si pas de config)
3. Valeurs par défaut hardcodées
```

## 🔄 Flux de chargement

```
┌─────────────────────────────────────────────────────────┐
│ 1. Requête HTTP arrive                                  │
└─────────────────┬───────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────┐
│ 2. get_template_context() est appelé                    │
│    (dans templates/__init__.py)                         │
└─────────────────┬───────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────┐
│ 3. Vérifier le cache (5 minutes)                        │
│    Cache valide ? → Utiliser les valeurs du cache      │
│    Cache expiré ? → Continuer                          │
└─────────────────┬───────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────┐
│ 4. Charger depuis la DB                                 │
│    SELECT * FROM system_settings WHERE id = 1           │
│    Existe ? → Utiliser ces valeurs + mettre en cache   │
│    Pas de row ? → Créer avec valeurs par défaut        │
└─────────────────┬───────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────┐
│ 5. En cas d'erreur (DB down, etc.)                      │
│    → Fallback sur get_default_settings()                │
│    → Utilise APP_NAME depuis config.py                 │
└─────────────────┬───────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────┐
│ 6. Injecter dans le contexte du template                │
│    system_settings: {...}                               │
│    app_name: system_settings.company_name               │
└─────────────────┬───────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────┐
│ 7. Template utilise les valeurs                         │
│    {{ app_name }}                                       │
│    {{ system_settings.company_email }}                  │
│    {{ system_settings.primary_color }}                  │
└─────────────────────────────────────────────────────────┘
```

## 💾 Cache automatique

### Fonctionnement
- **Durée:** 5 minutes
- **Invalidation:** Automatique lors d'une mise à jour
- **Avantage:** 1 seule requête DB toutes les 5 minutes au lieu de 1 par requête HTTP

### Code
```python
# Automatique dans get_settings_as_dict()
cached = settings_cache.get()
if cached is not None:
    return cached  # ✅ Retour immédiat depuis le cache
```

## 🎨 Variables disponibles dans tous les templates

### Informations entreprise
```html
{{ system_settings.company_name }}         <!-- Ex: "MPPEEP Dashboard" -->
{{ system_settings.company_description }}  <!-- Ex: "Notre solution de gestion" -->
{{ system_settings.company_email }}        <!-- Ex: "contact@mppeep.com" -->
{{ system_settings.company_phone }}        <!-- Ex: "+33 1 23 45 67 89" -->
{{ system_settings.company_address }}      <!-- Ex: "Paris, France" -->
```

### Apparence
```html
<!-- Logo -->
<img src="{{ static_url(system_settings.logo_path) }}" alt="Logo">

<!-- Couleurs (injectées automatiquement dans :root) -->
{{ system_settings.primary_color }}    <!-- Ex: "#ffd300" -->
{{ system_settings.secondary_color }}  <!-- Ex: "#036c1d" -->
{{ system_settings.accent_color }}     <!-- Ex: "#e63600" -->
```

### Personnalisation
```html
{{ system_settings.footer_text }}  <!-- Ex: "Tous droits réservés" -->
```

### Paramètres système
```html
{{ system_settings.maintenance_mode }}        <!-- true/false -->
{{ system_settings.allow_registration }}      <!-- true/false -->
{{ system_settings.max_upload_size_mb }}      <!-- Ex: 10 -->
{{ system_settings.session_timeout_minutes }} <!-- Ex: 30 -->
```

## 🎨 Couleurs dynamiques

Les couleurs sont automatiquement injectées dans le CSS via `base.html` :

```html
<style>
    :root {
        --primary-color: {{ system_settings.primary_color }};
        --secondary-color: {{ system_settings.secondary_color }};
        --accent-color: {{ system_settings.accent_color }};
    }
</style>
```

Ces variables CSS écrasent les valeurs par défaut de `theme.css` et sont utilisables partout :

```css
.mon-element {
    background-color: var(--primary-color);
    color: var(--secondary-color);
    border: 1px solid var(--accent-color);
}
```

## 🔄 Mise à jour des paramètres

### Via l'interface web

1. Se connecter en tant qu'admin
2. Aller sur **Paramètres Système**
3. Modifier les valeurs
4. Cliquer sur **💾 Enregistrer**
5. Le cache est automatiquement vidé
6. Rechargez la page pour voir les changements

### Via le code

```python
from app.services.system_settings_service import SystemSettingsService

# Mettre à jour
SystemSettingsService.update_settings(
    db_session=session,
    user_id=current_user.id,
    company_name="Ma Nouvelle Entreprise",
    primary_color="#ff0000"
)
# ✅ Cache automatiquement vidé
```

## 🏗️ Architecture

```
┌──────────────────────────────────────────┐
│  HTTP Request                             │
└──────────────┬───────────────────────────┘
               ↓
┌──────────────────────────────────────────┐
│  get_template_context()                   │
│  ├─ Charge current_user                   │
│  └─ Charge system_settings (avec cache)   │
└──────────────┬───────────────────────────┘
               ↓
┌──────────────────────────────────────────┐
│  SystemSettingsService.get_settings()     │
│  ├─ Cache hit? → Return cached           │
│  ├─ Cache miss? → Load from DB           │
│  └─ DB error? → get_default_settings()   │
└──────────────┬───────────────────────────┘
               ↓
┌──────────────────────────────────────────┐
│  Template reçoit:                         │
│  {                                        │
│    "app_name": "...",                     │
│    "current_user": {...},                 │
│    "system_settings": {                   │
│      "company_name": "...",               │
│      "primary_color": "#ffd300",          │
│      ...                                  │
│    }                                      │
│  }                                        │
└───────────────────────────────────────────┘
```

## 📝 Exemples d'utilisation

### Exemple 1: Afficher le nom de l'entreprise

```html
<!-- navbar.html -->
<span>{{ system_settings.company_name }}</span>

<!-- Rendu: "MPPEEP Dashboard" ou la valeur en DB -->
```

### Exemple 2: Email de contact conditionnel

```html
<!-- footer.html -->
{% if system_settings.company_email %}
    <a href="mailto:{{ system_settings.company_email }}">Contact</a>
{% endif %}

<!-- N'affiche le lien que si un email est configuré -->
```

### Exemple 3: Mode maintenance

```python
# Dans une route
@router.get("/")
def home(request: Request):
    context = get_template_context(request)
    
    if context["system_settings"].get("maintenance_mode"):
        return templates.TemplateResponse(
            "maintenance.html",
            context
        )
    
    return templates.TemplateResponse("home.html", context)
```

### Exemple 4: Logo personnalisé

```html
<!-- navbar.html -->
<img src="{{ static_url(system_settings.logo_path) }}" alt="Logo">

<!-- Utilise le logo uploadé par l'admin -->
```

## ⚡ Performance

### Sans cache
```
100 requêtes/sec × 1 query DB = 100 queries DB/sec ❌
```

### Avec cache (5 minutes)
```
100 requêtes/sec × 0 query (cache) = 0 queries DB/sec ✅
Recharge: 1 query tous les 5 minutes
```

**Gain:** ~99.99% de requêtes DB évitées ! 🚀

## 🔧 Configuration du cache

Pour modifier la durée du cache :

```python
# app/core/settings_cache.py
class SettingsCache:
    _cache_duration: int = 300  # 5 minutes (300 secondes)
    
    # Modifier selon vos besoins:
    # 60 = 1 minute
    # 300 = 5 minutes (recommandé)
    # 600 = 10 minutes
    # 3600 = 1 heure
```

## 🔐 Sécurité

- ✅ Seuls les admins peuvent modifier les paramètres
- ✅ Validation des couleurs (format hex)
- ✅ Validation des fichiers logo
- ✅ Traçabilité (updated_by_user_id)
- ✅ Fallback automatique en cas de problème

## 📚 Références

- [Modèle SystemSettings](app/models/system_settings.py)
- [Service](app/services/system_settings_service.py)
- [Cache](app/core/settings_cache.py)
- [Routes Admin](app/api/v1/endpoints/admin.py)
- [Documentation complète](app/models/SYSTEM_SETTINGS.md)

