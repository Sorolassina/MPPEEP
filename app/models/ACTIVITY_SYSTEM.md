# 📊 Système d'Activités Récentes

## Vue d'ensemble

Le système d'activités enregistre toutes les actions importantes des utilisateurs et les affiche sur la page d'accueil.

## 🎯 Objectifs

1. **Transparence** : Voir qui a fait quoi et quand
2. **Audit** : Tracer les modifications importantes
3. **Dashboard vivant** : Page d'accueil dynamique avec activités récentes
4. **Sécurité** : Détecter les actions suspectes

## 📊 Modèle de données

### Table : `activity`

| Champ | Type | Description | Exemple |
|-------|------|-------------|---------|
| `id` | int | ID unique | 1 |
| `user_id` | int | ID utilisateur | 5 |
| `user_email` | str | Email utilisateur | admin@mppeep.com |
| `action_type` | str | Type d'action | create, update, delete, login |
| `target_type` | str | Type de cible | user, settings, session |
| `target_id` | int | ID de la cible | 12 |
| `description` | str | Description | "Création de l'utilisateur John Doe" |
| `icon` | str | Icône emoji | 🔐, ➕, ✏️, 🗑️ |
| `created_at` | datetime | Date/heure | 2024-10-10 15:30:45 |

### Types d'actions

| action_type | Icône | Description | Exemple |
|-------------|-------|-------------|---------|
| `login` | 🔐 | Connexion utilisateur | "Connexion de John Doe" |
| `logout` | 🚪 | Déconnexion | "Déconnexion de John Doe" |
| `create` | ➕ | Création | "Création de l'utilisateur Jane Doe" |
| `update` | ✏️ | Modification | "Modification de l'utilisateur John Doe" |
| `delete` | 🗑️ | Suppression | "Suppression de l'utilisateur test@..." |
| `upload` | 📤 | Upload fichier | "Upload de la photo de profil pour John" |
| `settings` | ⚙️ | Paramètres système | "Mise à jour des paramètres système" |

## 🔧 Service ActivityService

### Méthodes disponibles

#### `log_activity()`

Enregistre une nouvelle activité.

```python
from app.services.activity_service import ActivityService

ActivityService.log_activity(
    db_session=session,
    user_id=current_user.id,
    user_email=current_user.email,
    action_type="create",
    target_type="user",
    target_id=new_user.id,
    description="Création de l'utilisateur John Doe (john@example.com)",
    icon="➕"  # Optionnel, auto-détecté si None
)
```

#### `get_recent_activities()`

Récupère les activités récentes.

```python
activities = ActivityService.get_recent_activities(
    db_session=session,
    limit=10,    # 10 dernières activités
    days=7       # Sur les 7 derniers jours
)

# Retourne: [
#     {
#         "user_email": "admin@mppeep.com",
#         "description": "Création de l'utilisateur John Doe",
#         "icon": "➕",
#         "time": datetime(2024, 10, 10, 15, 30, 45)
#     },
#     ...
# ]
```

#### `get_user_activities()`

Activités d'un utilisateur spécifique.

```python
user_activities = ActivityService.get_user_activities(
    db_session=session,
    user_id=5,
    limit=20
)
```

#### `cleanup_old_activities()`

Nettoie les activités anciennes.

```python
# Supprimer les activités de plus de 30 jours
deleted_count = ActivityService.cleanup_old_activities(
    db_session=session,
    days=30
)
# Retourne: nombre d'activités supprimées
```

## 📍 Où les activités sont loguées

### 1. Gestion des utilisateurs (`admin.py`)

**CREATE User:**
```python
ActivityService.log_activity(
    action_type="create",
    target_type="user",
    description=f"Création de l'utilisateur {full_name} ({email})"
)
```

**UPDATE User:**
```python
ActivityService.log_activity(
    action_type="update",
    target_type="user",
    description=f"Modification de l'utilisateur {full_name} ({email})"
)
```

**DELETE User:**
```python
ActivityService.log_activity(
    action_type="delete",
    target_type="user",
    description=f"Suppression de l'utilisateur {full_name} ({email})"
)
```

**UPLOAD Photo:**
```python
ActivityService.log_activity(
    action_type="upload",
    target_type="profile_picture",
    description=f"Upload de la photo de profil pour {user.full_name}",
    icon="📸"
)
```

### 2. Paramètres système (`admin.py`)

**UPDATE Settings:**
```python
ActivityService.log_activity(
    action_type="settings",
    target_type="system",
    description="Mise à jour des paramètres système",
    icon="⚙️"
)
```

**UPLOAD Logo:**
```python
ActivityService.log_activity(
    action_type="upload",
    target_type="logo",
    description=f"Upload du logo entreprise ({filename})",
    icon="🖼️"
)
```

### 3. Authentification (`auth.py`)

**LOGIN:**
```python
ActivityService.log_activity(
    action_type="login",
    target_type="session",
    description=f"Connexion de {user.full_name or user.email}",
    icon="🔐"
)
```

**LOGOUT:**
```python
ActivityService.log_activity(
    action_type="logout",
    target_type="session",
    description=f"Déconnexion de {user.full_name or user.email}",
    icon="🚪"
)
```

## 🖥️ Affichage sur la page d'accueil

### Route `/accueil`

```python
# app/main.py
@app.get("/accueil")
def accueil(request: Request):
    # Charger les activités récentes
    recent_activity = ActivityService.get_recent_activities(db, limit=10, days=7)
    
    return templates.TemplateResponse(
        "pages/accueil.html",
        get_template_context(request, recent_activity=recent_activity)
    )
```

### Template `accueil.html`

```html
<div class="activity-section">
    <h3>Activité Récente</h3>
    <div class="activity-list">
        {% if recent_activity %}
            {% for activity in recent_activity %}
                <div class="activity-item">
                    <div class="activity-icon">{{ activity.icon }}</div>
                    <div class="activity-content">
                        <div class="activity-title">{{ activity.description }}</div>
                        <div class="activity-time">{{ activity.time|format_datetime }}</div>
                    </div>
                </div>
            {% endfor %}
        {% else %}
            <p class="empty-state">Aucune activité récente</p>
        {% endif %}
    </div>
</div>
```

### Rendu visuel

```
┌──────────────────────────────────────────────┐
│  Activité Récente                             │
├──────────────────────────────────────────────┤
│  ➕  Création de l'utilisateur John Doe      │
│      10/10/2024 à 15:30                       │
│                                               │
│  ✏️  Modification de l'utilisateur Jane Doe  │
│      10/10/2024 à 14:15                       │
│                                               │
│  🔐  Connexion de admin@mppeep.com           │
│      10/10/2024 à 13:45                       │
│                                               │
│  ⚙️  Mise à jour des paramètres système      │
│      10/10/2024 à 12:00                       │
│                                               │
│  🗑️  Suppression de l'utilisateur test@...   │
│      09/10/2024 à 18:22                       │
└──────────────────────────────────────────────┘
```

## 📊 Statistiques mises à jour

La page d'accueil affiche aussi des stats calculées en temps réel :

```python
stats = {
    "users_count": total_users,           # Total utilisateurs
    "items_count": active_users,          # Utilisateurs actifs
    "completed_count": admin_count,       # Nombre d'admins
    "growth": 0                           # Croissance (à implémenter)
}
```

## 🧹 Maintenance

### Nettoyage automatique (recommandé)

Créer un job cron ou tâche planifiée :

```python
# Script de nettoyage hebdomadaire
from app.services.activity_service import ActivityService

# Garder 30 jours d'activités
deleted = ActivityService.cleanup_old_activities(db, days=30)
print(f"{deleted} activités supprimées")
```

### Nettoyage manuel

```sql
-- Supprimer les activités de plus de 30 jours
DELETE FROM activity 
WHERE created_at < datetime('now', '-30 days');

-- SQLite
DELETE FROM activity 
WHERE created_at < datetime('now', '-30 days');

-- PostgreSQL
DELETE FROM activity 
WHERE created_at < NOW() - INTERVAL '30 days';
```

## 🔍 Requêtes utiles

### Activités d'un utilisateur

```sql
SELECT description, icon, created_at 
FROM activity 
WHERE user_id = 5 
ORDER BY created_at DESC 
LIMIT 20;
```

### Activités par type

```sql
SELECT action_type, COUNT(*) as count
FROM activity
GROUP BY action_type
ORDER BY count DESC;
```

### Activités récentes (7 derniers jours)

```sql
SELECT * FROM activity
WHERE created_at >= datetime('now', '-7 days')
ORDER BY created_at DESC
LIMIT 10;
```

## 🚀 Installation

### Pour nouvelle installation

```bash
# Les tables sont créées automatiquement
uvicorn app.main:app --reload
# ✅ Table activity créée
```

### Pour installation existante

```bash
# Exécuter le script de migration
cd mppeep
python scripts/create_activity_table.py
```

## 📈 Exemples d'activités

```
🔐 Connexion de Admin User
   10/10/2024 à 15:30

➕ Création de l'utilisateur John Doe (john@example.com)
   10/10/2024 à 15:32

📸 Upload de la photo de profil pour John Doe
   10/10/2024 à 15:33

✏️ Modification de l'utilisateur Jane Smith (jane@example.com)
   10/10/2024 à 14:15

⚙️ Mise à jour des paramètres système
   10/10/2024 à 12:00

🖼️ Upload du logo entreprise (logo_20241010_120000.jpg)
   10/10/2024 à 12:01

🗑️ Suppression de l'utilisateur test@example.com
   09/10/2024 à 18:22

🚪 Déconnexion de Admin User
   09/10/2024 à 17:00
```

## 🎨 Personnalisation des icônes

Dans `ActivityService` :

```python
ACTION_ICONS = {
    "create": "➕",
    "update": "✏️",
    "delete": "🗑️",
    "login": "🔐",
    "logout": "🚪",
    "upload": "📤",
    "download": "📥",
    "view": "👁️",
    "settings": "⚙️",
}
```

Pour ajouter un nouveau type:

```python
ACTION_ICONS["export"] = "📊"
ACTION_ICONS["import"] = "📥"
ACTION_ICONS["backup"] = "💾"
```

## 🔐 Sécurité et vie privée

### Données sensibles

**NE PAS logger:**
- ❌ Mots de passe
- ❌ Tokens de session
- ❌ Données personnelles sensibles

**OK à logger:**
- ✅ Actions (create, update, delete)
- ✅ Qui a fait l'action
- ✅ Quand
- ✅ Sur quelle entité (user, settings)

### Rétention des données

**Recommandé:** 30-90 jours

```python
# Supprimer les activités de plus de 30 jours chaque semaine
ActivityService.cleanup_old_activities(db, days=30)
```

## 📚 Intégration future

### Page d'audit complète

```python
@router.get("/admin/audit")
def audit_page(request: Request):
    activities = ActivityService.get_recent_activities(db, limit=100, days=30)
    return templates.TemplateResponse("pages/audit.html", {...})
```

### Filtrage par utilisateur

```python
user_activities = ActivityService.get_user_activities(db, user_id=5)
```

### Filtrage par type

```python
statement = select(Activity).where(
    Activity.action_type == "delete"
).order_by(Activity.created_at.desc())
```

### Export CSV

```python
import csv

activities = ActivityService.get_recent_activities(db, limit=1000)
with open('audit.csv', 'w') as f:
    writer = csv.DictWriter(f, fieldnames=['user_email', 'action_type', 'description', 'time'])
    writer.writeheader()
    writer.writerows(activities)
```

## 🔄 Flux complet

```
┌─────────────────────────────────────────────────────────┐
│  Admin crée un utilisateur                              │
└─────────────────┬───────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────┐
│  admin.py::create_user()                                │
│  1. Valider les données                                 │
│  2. Créer l'utilisateur en DB                           │
│  3. ActivityService.log_activity(                       │
│       action_type="create",                             │
│       target_type="user",                               │
│       description="Création de John Doe"                │
│    )                                                     │
│  4. INSERT INTO activity VALUES (...)                   │
└─────────────────┬───────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────┐
│  Admin va sur la page d'accueil                         │
└─────────────────┬───────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────┐
│  main.py::accueil()                                     │
│  1. ActivityService.get_recent_activities(limit=10)     │
│  2. SELECT * FROM activity                              │
│      WHERE created_at >= NOW() - 7 days                 │
│      ORDER BY created_at DESC                           │
│      LIMIT 10                                           │
│  3. Return [                                            │
│       {description: "Création de John Doe", icon: "➕"},│
│       {description: "Connexion de Admin", icon: "🔐"},  │
│       ...                                               │
│     ]                                                   │
└─────────────────┬───────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────┐
│  Template accueil.html affiche la liste                │
│  ➕ Création de l'utilisateur John Doe                  │
│     10/10/2024 à 15:30                                  │
│                                                         │
│  🔐 Connexion de Admin User                            │
│     10/10/2024 à 13:45                                  │
└─────────────────────────────────────────────────────────┘
```

## 📝 Exemples de code

### Exemple 1: Logger une connexion

```python
# Dans auth.py après connexion réussie
ActivityService.log_activity(
    db_session=session,
    user_id=user.id,
    user_email=user.email,
    action_type="login",
    target_type="session",
    description=f"Connexion de {user.full_name or user.email}"
)
```

### Exemple 2: Logger une modification

```python
# Dans admin.py après modification utilisateur
ActivityService.log_activity(
    db_session=session,
    user_id=current_user.id,
    user_email=current_user.email,
    action_type="update",
    target_type="user",
    target_id=modified_user.id,
    description=f"Modification de l'utilisateur {modified_user.full_name}"
)
```

### Exemple 3: Logger avec icône personnalisée

```python
ActivityService.log_activity(
    db_session=session,
    user_id=current_user.id,
    user_email=current_user.email,
    action_type="export",
    target_type="data",
    description="Export des données utilisateurs en CSV",
    icon="📊"  # Icône personnalisée
)
```

## 📊 Statistiques d'utilisation

### Moyenne d'activités par jour

```sql
SELECT DATE(created_at) as date, COUNT(*) as count
FROM activity
GROUP BY DATE(created_at)
ORDER BY date DESC
LIMIT 30;
```

### Utilisateurs les plus actifs

```sql
SELECT user_email, COUNT(*) as activity_count
FROM activity
GROUP BY user_email
ORDER BY activity_count DESC
LIMIT 10;
```

### Actions les plus fréquentes

```sql
SELECT action_type, COUNT(*) as count
FROM activity
GROUP BY action_type
ORDER BY count DESC;
```

## 🎯 Best Practices

### ✅ À FAIRE

1. Logger toutes les actions administratives (CRUD)
2. Nettoyer régulièrement les anciennes activités
3. Utiliser des descriptions claires et concises
4. Inclure le nom de l'utilisateur dans la description
5. Utiliser try/except pour ne pas bloquer l'action principale

```python
try:
    ActivityService.log_activity(...)
except Exception as e:
    logger.warning(f"Impossible de logger l'activité: {e}")
    # L'action continue quand même
```

### ❌ À ÉVITER

1. Logger des informations sensibles (mots de passe, tokens)
2. Logger chaque lecture (trop verbeux)
3. Garder les activités indéfiniment (problème d'espace disque)
4. Bloquer l'action principale si le log échoue

## 📚 Références

- [Modèle Activity](activity.py)
- [Service ActivityService](../../services/activity_service.py)
- [Routes Admin](../../api/v1/endpoints/admin.py)
- [Routes Auth](../../api/v1/endpoints/auth.py)
- [Script de migration](../../scripts/create_activity_table.py)

---

**🎉 Le système d'activités rend votre dashboard vivant et transparent !**

