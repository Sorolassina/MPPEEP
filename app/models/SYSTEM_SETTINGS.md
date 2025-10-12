# ⚙️ Système de Paramètres

## Vue d'ensemble

Le système de paramètres permet de configurer l'application via une interface web sans toucher au code.

## 📊 Modèle de données

### Table : `system_settings`

| Champ | Type | Description | Par défaut |
|-------|------|-------------|------------|
| `id` | int | ID (toujours 1 - singleton) | 1 |
| `company_name` | str | Nom de l'entreprise | "MPPEEP Dashboard" |
| `company_description` | str | Description entreprise | NULL |
| `company_email` | str | Email de contact | NULL |
| `company_phone` | str | Téléphone | NULL |
| `company_address` | str | Adresse | NULL |
| `logo_path` | str | Chemin du logo | "images/logo.jpg" |
| `primary_color` | str | Couleur principale (hex) | "#ffd300" |
| `secondary_color` | str | Couleur secondaire (hex) | "#036c1d" |
| `accent_color` | str | Couleur accent (hex) | "#e63600" |
| `footer_text` | str | Texte du footer | "Tous droits réservés" |
| `maintenance_mode` | bool | Mode maintenance | False |
| `allow_registration` | bool | Autoriser inscriptions | False |
| `max_upload_size_mb` | int | Taille max uploads (MB) | 10 |
| `session_timeout_minutes` | int | Durée session (min) | 30 |
| `updated_at` | datetime | Dernière modification | now() |
| `updated_by_user_id` | int | ID utilisateur | NULL |

## 🔧 Service SystemSettingsService

### Méthodes disponibles

#### `get_settings(db_session)`
Récupère les paramètres (crée avec valeurs par défaut si inexistant)

```python
from app.services.system_settings_service import SystemSettingsService

settings = SystemSettingsService.get_settings(db_session)
print(settings.company_name)  # "MPPEEP Dashboard"
```

#### `update_settings(db_session, user_id, **kwargs)`
Met à jour les paramètres

```python
SystemSettingsService.update_settings(
    db_session=session,
    user_id=current_user.id,
    company_name="Ma Société",
    primary_color="#ff0000"
)
```

#### `get_settings_as_dict(db_session)`
Récupère sous forme de dictionnaire (pratique pour les templates)

```python
settings = SystemSettingsService.get_settings_as_dict(db_session)
# Retourne: {"company_name": "...", "primary_color": "...", ...}
```

## 🛣️ Routes API

### GET `/api/v1/admin/parametres-systeme`
Affiche la page de gestion des paramètres

**Permissions:** Admin uniquement

### POST `/api/v1/admin/settings/update`
Met à jour les paramètres système

**Permissions:** Admin uniquement

**Form Data:**
- company_name (required)
- company_description
- company_email
- company_phone
- company_address
- primary_color
- secondary_color
- accent_color
- footer_text
- maintenance_mode (checkbox)
- allow_registration (checkbox)
- max_upload_size_mb
- session_timeout_minutes

**Réponse:**
```json
{
    "success": true,
    "message": "Paramètres système mis à jour avec succès"
}
```

### POST `/api/v1/admin/settings/upload-logo`
Upload un nouveau logo

**Permissions:** Admin uniquement

**Form Data:**
- logo (file)

**Formats acceptés:** JPG, JPEG, PNG, GIF, WEBP (max 5MB)

**Réponse:**
```json
{
    "success": true,
    "message": "Logo uploadé avec succès",
    "logo_url": "/static/images/logo_20241010_120000.jpg"
}
```

## 🎨 Interface Web

### Page de gestion

**URL:** `/api/v1/admin/parametres-systeme`

**Fonctionnalités:**
- ✅ Formulaire avec tous les champs
- ✅ Color pickers pour les couleurs
- ✅ Upload de logo avec prévisualisation
- ✅ Checkboxes pour options booléennes
- ✅ Validation en temps réel
- ✅ Messages de succès/erreur
- ✅ Sauvegarde AJAX sans rechargement

### Sections du formulaire

1. **🏢 Informations Entreprise**
   - Nom, description, email, téléphone, adresse

2. **🎨 Logo**
   - Aperçu du logo actuel
   - Upload de nouveau logo

3. **🎨 Palette de Couleurs**
   - Couleur principale (jaune par défaut)
   - Couleur secondaire (vert par défaut)
   - Couleur d'accent (rouge par défaut)

4. **✨ Personnalisation**
   - Texte personnalisé du footer

5. **🔧 Paramètres Système**
   - Taille max des uploads
   - Durée des sessions
   - Mode maintenance
   - Autoriser inscriptions

## 📝 Exemple d'utilisation dans un template

```html
<!-- Récupérer les paramètres dans une route -->
@router.get("/ma-page")
def ma_page(request: Request, session: Session = Depends(get_session)):
    settings = SystemSettingsService.get_settings_as_dict(session)
    return templates.TemplateResponse(
        "ma_page.html",
        {"request": request, "settings": settings}
    )

<!-- Utiliser dans le template -->
<h1>{{ settings.company_name }}</h1>
<p>{{ settings.company_description }}</p>
<img src="{{ static_url(settings.logo_path) }}" alt="Logo">
```

## 🔄 Initialisation

Les paramètres sont créés automatiquement au démarrage de l'application via `scripts/init_db.py` :

```
Étape 2: Initialiser les paramètres système
✅ Paramètres système initialisés/vérifiés
   Entreprise: MPPEEP Dashboard
```

## 🔐 Sécurité

- ✅ Toutes les routes nécessitent le rôle "admin"
- ✅ Upload de logo : vérification du type de fichier
- ✅ Upload de logo : limite de taille (5MB)
- ✅ Traçabilité : chaque modification est loguée avec l'utilisateur
- ✅ Timestamp de modification automatique

## 📊 Logs

```
⚙️  Accès paramètres système par admin@example.com
⚙️  Paramètres système mis à jour par admin@example.com
📁 Logo uploadé: logo_20241010_120000.jpg par admin@example.com
```

## 🚀 Fonctionnalités futures

- [ ] Thèmes prédéfinis (dark mode, light mode)
- [ ] Export/Import de configuration
- [ ] Historique des modifications
- [ ] Prévisualisation en temps réel des couleurs
- [ ] Gestion multi-langues

