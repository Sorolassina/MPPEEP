# 🔐 Routes d'Administration

Ce fichier documente toutes les routes d'administration de l'application.

## 📁 Fichier: `admin.py`

### Routes disponibles

| Route | Méthode | Nom | Rôle requis | Description |
|-------|---------|-----|-------------|-------------|
| `/api/v1/admin/gestion-utilisateurs` | GET | `gestion_utilisateurs` | Admin | Page de gestion des utilisateurs |
| `/api/v1/admin/parametres-systeme` | GET | `parametres_systeme` | Admin | Paramètres système |
| `/api/v1/admin/rapports` | GET | `rapports` | Admin, Moderator | Page des rapports |

## 🔒 Sécurité

Toutes les routes admin utilisent le système d'authentification et de rôles :

```python
@router.get("/route-admin")
def ma_route(
    request: Request,
    current_user: User = Depends(require_roles("admin"))
):
    # Seuls les admins peuvent accéder
    ...
```

### Rôles disponibles

- **admin** : Accès complet à toutes les fonctionnalités
- **moderator** : Accès aux rapports et modération
- **user** : Utilisateur standard (pas d'accès admin)
- **guest** : Invité (accès limité)

## 📋 Fonctionnalités

### Gestion des Utilisateurs
- ✅ Liste complète des utilisateurs
- ✅ Statistiques (total, actifs, admins)
- ✅ Filtrage par statut et rôle
- 🚧 Modification d'utilisateur (à venir)
- 🚧 Suppression d'utilisateur (à venir)
- 🚧 Création d'utilisateur (à venir)

### Paramètres Système
- 🚧 Configuration globale
- 🚧 Gestion des emails
- 🚧 Paramètres de sécurité

### Rapports
- 🚧 Statistiques d'utilisation
- 🚧 Export de données
- 🚧 Logs système

## 🎯 Utilisation

### Accéder à une route admin

```python
# Dans un template
<a href="{{ url_for('gestion_utilisateurs') }}">Gérer les utilisateurs</a>

# Dans un endpoint
return RedirectResponse(url=str(request.url_for("gestion_utilisateurs")))
```

### Ajouter une nouvelle route admin

1. Ouvrir `app/api/v1/endpoints/admin.py`
2. Ajouter la nouvelle route :

```python
@router.get("/ma-nouvelle-route", response_class=HTMLResponse, name="ma_route")
def ma_route(
    request: Request,
    current_user: User = Depends(require_roles("admin"))
):
    logger.info(f"Accès ma route par {current_user.email}")
    
    return templates.TemplateResponse(
        "pages/ma_page.html",
        get_template_context(request, data=...)
    )
```

3. Créer le template correspondant dans `app/templates/pages/`
4. Mettre à jour ce README

## 📊 Logs

Toutes les routes admin génèrent des logs :

```
👤 Accès page gestion utilisateurs par admin@example.com
📊 5 utilisateurs récupérés
⚙️  Accès paramètres système par admin@example.com
```

## 🔗 Liens utiles

- [Documentation Auth](./auth.py)
- [Documentation Users](./users.py)
- [Templates Admin](../../../templates/pages/)

