# 🎨 Templates Jinja2

## 📁 Structure

```
templates/
├── __init__.py                 ← Configuration Jinja2 + Filtres personnalisés
├── base.html                   ← Template de base (layout principal)
├── index.html                  ← Page d'accueil
├── login.html                  ← Page de connexion
└── recovery_password/          ← Workflow récupération mot de passe
    ├── forgot_password.html    ← Étape 1 : Demande de récupération
    ├── verify_code.html        ← Étape 2 : Vérification du code
    └── reset_password.html     ← Étape 3 : Nouveau mot de passe
```

---

## 🎯 Principe des Templates

### Template de Base (base.html)

C'est le **squelette** de toutes vos pages :

```html
<!doctype html>
<html>
<head>
    <title>{{ app_name }}</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <header>
        <h1>{{ app_name }}</h1>
        <nav><!-- Navigation --></nav>
    </header>
    
    <main>
        {% block content %}{% endblock %}  ← Contenu variable
    </main>
    
    <script src="/static/js/app.js"></script>
</body>
</html>
```

### Template Enfant (index.html)

**Hérite** du template de base et **remplit** le bloc content :

```html
{% extends "base.html" %}

{% block content %}
    <h2>Bienvenue</h2>
    <p>Contenu spécifique de cette page</p>
{% endblock %}
```

**Résultat :** Votre page aura le header/footer de `base.html` + le contenu de `index.html`

---

## 🛠️ Filtres Personnalisés Disponibles

### Dates et Heures

```jinja2
{# Formater une date #}
{{ ma_date|format_date }}
→ 15/12/2023

{# Formater une date avec heure #}
{{ ma_datetime|format_datetime }}
→ 15/12/2023 à 14:30

{# Formater juste l'heure #}
{{ mon_heure|format_time }}
→ 14:30
```

### Nombres

```jinja2
{# Format français des nombres #}
{{ 1234.56|format_number_french }}
→ 1 234,56

{# Sans décimales #}
{{ 1234.56|format_number_french(0) }}
→ 1 235
```

### Texte

```jinja2
{# Tronquer intelligemment #}
{{ "Texte très long..."|truncate_smart(20) }}
→ Texte très long...

{# Tronquer avec suffix personnalisé #}
{{ "Texte très long..."|truncate_smart(15, " (...)") }}
→ Texte très (...) 
```

---

## 🌍 Variables Globales

Ces variables sont disponibles **partout** dans tous les templates :

```jinja2
{# Année actuelle #}
© {{ current_year() }}
→ © 2025

{# Date/heure actuelle #}
{{ now() }}
→ 2025-01-08 14:30:00

{# Module datetime complet #}
{{ datetime.now().strftime("%A") }}
→ Mercredi
```

---

## 🎨 Bonnes Pratiques

### ✅ DO (À Faire)

1. **Utiliser l'héritage de templates**
   ```jinja2
   {% extends "base.html" %}
   ```

2. **Externaliser les styles**
   ```html
   <!-- ❌ Éviter -->
   <style>
       .classe { color: red; }
   </style>
   
   <!-- ✅ Faire -->
   <link rel="stylesheet" href="/static/css/ma-page.css">
   ```

3. **Organiser par fonctionnalité**
   ```
   auth/           ← Tout ce qui est authentification
   admin/          ← Tout ce qui est admin
   user/           ← Tout ce qui est utilisateur
   ```

4. **Utiliser les blocs pour la flexibilité**
   ```jinja2
   {% block head_extra %}{% endblock %}  ← Scripts/CSS additionnels
   {% block content %}{% endblock %}      ← Contenu principal
   {% block scripts %}{% endblock %}      ← Scripts JS
   ```

### ❌ DON'T (À Éviter)

1. **❌ Logique métier dans les templates**
   ```jinja2
   <!-- ❌ Mauvais -->
   {% for user in all_users %}
       {% if user.is_active and user.role == 'admin' %}
           <!-- Logique trop complexe -->
       {% endif %}
   {% endfor %}
   
   <!-- ✅ Bon : Filtrer dans le backend -->
   {% for user in active_admin_users %}
       {{ user.name }}
   {% endfor %}
   ```

2. **❌ Styles inline massifs**
   ```html
   <!-- ❌ 500 lignes de CSS dans le template -->
   <style>
       /* Trop de styles... */
   </style>
   ```

3. **❌ Duplication de code**
   ```jinja2
   <!-- ❌ Copier-coller le même header partout -->
   
   <!-- ✅ Créer un composant réutilisable -->
   {% include "components/header.html" %}
   ```

---

## 📝 Créer un Nouveau Template

### Étape 1 : Créer le fichier

```bash
touch app/templates/ma_page.html
```

### Étape 2 : Structure de base

```html
{% extends "base.html" %}

{% block content %}
    <h1>Ma Nouvelle Page</h1>
    <p>Contenu de ma page</p>
{% endblock %}
```

### Étape 3 : Créer la route

```python
# app/api/v1/endpoints/ma_route.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.templates import templates

router = APIRouter()

@router.get("/ma-page", response_class=HTMLResponse)
async def ma_page(request: Request):
    return templates.TemplateResponse(
        "ma_page.html",
        {
            "request": request,
            "app_name": "Mon App",
            "data": "Mes données"
        }
    )
```

### Étape 4 : Utiliser dans le template

```html
{% extends "base.html" %}

{% block content %}
    <h1>{{ app_name }}</h1>
    <p>{{ data }}</p>
{% endblock %}
```

---

## 🔧 Ajouter un Filtre Personnalisé

### Dans `__init__.py`

```python
def mon_filtre(value, param="default"):
    """Description du filtre"""
    # Logique de transformation
    return value.upper()

# Enregistrer le filtre
templates.env.filters["mon_filtre"] = mon_filtre
```

### Utiliser dans un template

```jinja2
{{ "hello"|mon_filtre }}
→ HELLO

{{ "hello"|mon_filtre("param") }}
→ HELLO (avec paramètre)
```

---

## 📚 Organisation pour Projets Complexes

Pour les gros projets, utilisez cette structure :

```
templates/
├── layouts/              ← Templates de base
│   ├── base.html        ← Layout principal
│   ├── auth.html        ← Layout authentification
│   └── dashboard.html   ← Layout dashboard
│
├── components/          ← Composants réutilisables
│   ├── navbar.html     
│   ├── footer.html
│   └── alerts.html
│
├── auth/                ← Pages authentification
│   ├── login.html
│   └── register.html
│
├── user/                ← Pages utilisateur
│   ├── profile.html
│   └── settings.html
│
└── admin/               ← Pages admin
    ├── dashboard.html
    └── users_list.html
```

### Utiliser les layouts

```jinja2
<!-- auth/login.html -->
{% extends "layouts/auth.html" %}

<!-- user/profile.html -->
{% extends "layouts/dashboard.html" %}
```

### Inclure des composants

```jinja2
{% include "components/navbar.html" %}
<main>
    {% block content %}{% endblock %}
</main>
{% include "components/footer.html" %}
```

---

## 🎯 Templates vs API

### Quand utiliser des Templates HTML ?

✅ **Pages web traditionnelles**
- Formulaires de connexion
- Pages d'administration
- Pages statiques (CGU, mentions légales)

### Quand utiliser l'API JSON ?

✅ **Applications SPA (React, Vue, Angular)**
✅ **API pour mobile**
✅ **Intégrations externes**

### Approche Hybride (Recommandé)

```python
# Routes templates pour les pages d'auth
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {...})

# Routes API pour le reste
@router.get("/api/v1/users")
async def get_users():
    return {"users": [...]}  # JSON
```

---

## 🔍 Debug des Templates

### Afficher une variable

```jinja2
{{ ma_variable }}

{# Voir le type #}
{{ ma_variable.__class__.__name__ }}

{# Voir tous les attributs #}
{{ ma_variable|pprint }}
```

### Mode debug

```python
# Dans __init__.py
templates.env.auto_reload = True  # Reload automatique
```

### Erreurs courantes

| Erreur | Cause | Solution |
|--------|-------|----------|
| `UndefinedError` | Variable non passée | Ajouter la variable dans le context |
| `TemplateNotFound` | Chemin incorrect | Vérifier le chemin du template |
| `FilterArgumentError` | Mauvais argument au filtre | Vérifier la signature du filtre |

---

## 📖 Ressources

- [Documentation Jinja2](https://jinja.palletsprojects.com/)
- [FastAPI Templates](https://fastapi.tiangolo.com/advanced/templates/)
- [Guide Jinja2 (français)](https://jinja.palletsprojects.com/en/3.0.x/)

---

## ✨ Résumé

| Aspect | Explication |
|--------|-------------|
| **Rôle** | Générer le HTML côté serveur |
| **Langage** | Jinja2 (similaire à Python) |
| **Héritage** | `{% extends %}` pour réutiliser |
| **Inclusion** | `{% include %}` pour composants |
| **Variables** | `{{ ma_variable }}` |
| **Filtres** | `{{ value\|filtre }}` |

**💡 Les templates = Le "frontend" de votre application web traditionnelle !**

