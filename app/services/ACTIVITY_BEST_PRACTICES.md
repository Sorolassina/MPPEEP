# 📊 Bonnes Pratiques - Système d'Activités

## 🎯 Objectif

Créer des descriptions d'activités **claires et détaillées** pour que les utilisateurs comprennent exactement ce qui s'est passé.

---

## ✅ Bonnes Descriptions (À FAIRE)

### Exemples de descriptions détaillées

```python
# ❌ MAUVAIS - Trop vague
ActivityService.log_activity(
    db_session=session,
    user_id=user.id,
    user_email=user.email,
    action_type="update",
    target_type="user",
    description="Mise à jour"  # ❌ On ne sait pas quoi !
)

# ✅ BON - Détails précis
ActivityService.log_activity(
    db_session=session,
    user_id=user.id,
    user_email=user.email,
    action_type="update",
    target_type="user",
    target_id=updated_user.id,
    description=f"Modification du profil de {updated_user.full_name} : changement de l'email de {old_email} vers {new_email}",
    icon="✏️"
)
```

---

## 📋 Templates de Descriptions par Action

### Utilisateurs

```python
# Création
description = f"Création d'un nouvel utilisateur : {user.full_name} ({user.email})"

# Mise à jour
description = f"Modification du profil de {user.full_name} : {changed_fields}"

# Suppression
description = f"Suppression de l'utilisateur {user.full_name} ({user.email})"

# Activation/Désactivation
description = f"{'Activation' if user.is_active else 'Désactivation'} du compte de {user.full_name}"

# Changement de rôle
description = f"Changement de rôle de {user.full_name} : {old_role} → {new_role}"
```

### Fichiers

```python
# Upload
description = f"Upload du fichier '{file.title}' (type: {file.file_type}, programme: {file.program}, période: {file.period})"

# Traitement réussi
description = f"Traitement terminé du fichier '{file.title}' : {file.rows_processed} lignes traitées avec succès"

# Erreur de traitement
description = f"Échec du traitement du fichier '{file.title}' : {error_message}"

# Suppression
description = f"Suppression du fichier '{file.title}' (période: {file.period})"

# Archive
description = f"Archivage du fichier '{file.title}' (type: {file.file_type})"
```

### Paramètres système

```python
# Modification couleur
description = f"Modification de la couleur principale : {old_color} → {new_color}"

# Modification logo
description = f"Changement du logo de l'entreprise"

# Modification nom
description = f"Changement du nom de l'entreprise : '{old_name}' → '{new_name}'"
```

### Authentification

```python
# Connexion
description = f"Connexion réussie depuis {device_info} ({ip_address})"

# Déconnexion
description = f"Déconnexion ({device_info})"

# Mot de passe oublié
description = f"Demande de réinitialisation de mot de passe envoyée à {email}"

# Réinitialisation
description = f"Réinitialisation du mot de passe effectuée avec succès"
```

---

## 🎨 Format Recommandé

### Structure de base

```
[Action] [Objet] : [Détails]
```

### Exemples

```
✅ "Création du rapport budgétaire : Budget Education Q1-2024, 150 lignes"
✅ "Modification du profil : Jean Dupont - Changement email"
✅ "Suppression de l'utilisateur : marie@example.com (Compte inactif)"
✅ "Upload du fichier 'Dépenses Janvier' : Programme Santé, 245 lignes"
```

---

## 🔧 Intégration dans le Code

### Exemple complet : Upload de fichier

```python
# Dans app/api/v1/endpoints/files.py

@router.post("/upload")
async def upload_file(...):
    # ... code d'upload ...
    
    # Sauvegarder le fichier
    db_file = await FileService.save_file(session, file, metadata, current_user.id)
    
    # ✅ Logger l'activité avec détails
    ActivityService.log_activity(
        db_session=session,
        user_id=current_user.id,
        user_email=current_user.email,
        action_type="upload",
        target_type="file",
        target_id=db_file.id,
        description=(
            f"Upload du fichier '{db_file.title}' "
            f"(type: {db_file.file_type}, "
            f"programme: {db_file.program}, "
            f"période: {db_file.period}, "
            f"taille: {db_file.file_size_mb} MB)"
        ),
        icon="📤"
    )
    
    return db_file
```

### Exemple : Traitement terminé

```python
# Dans process_file_background() après traitement réussi

if success:
    # Mettre à jour le statut
    FileService.update_file_status(...)
    
    # ✅ Logger l'activité
    ActivityService.log_activity(
        db_session=session,
        user_id=db_file.uploaded_by,
        user_email="système",  # Ou l'email de l'uploader
        action_type="process",
        target_type="file",
        target_id=file_id,
        description=(
            f"Traitement terminé du fichier '{metadata.get('title')}' : "
            f"{rows_processed} lignes traitées, "
            f"{rows_failed} échecs"
        ),
        icon="✅"
    )
```

---

## 📊 Affichage dans l'Interface

Avec les nouvelles descriptions détaillées, l'affichage sera :

```
┌─────────────────────────────────────────────┐
│ 📋 Activité Récente (7 derniers jours)      │
├─────────────────────────────────────────────┤
│ 📤  admin@mppeep.com         [UPLOAD]       │
│     Upload du fichier 'Budget Education'    │
│     🎯 file    🕐 Il y a 2 heures           │
├─────────────────────────────────────────────┤
│ ✅  system                   [PROCESS]      │
│     Traitement terminé : 150 lignes OK      │
│     🎯 file    🕐 Il y a 2 heures           │
├─────────────────────────────────────────────┤
│ ✏️  admin@mppeep.com         [UPDATE]       │
│     Modification du profil : Jean Dupont    │
│     🎯 user    🕐 Il y a 5 heures           │
└─────────────────────────────────────────────┘
         ↕️ Scroll si > 500px
```

---

## 🚀 Mise en Œuvre

### 1. Améliorer les logs existants

Parcourez votre code et remplacez les logs d'activité vagues par des descriptions détaillées.

**Fichiers à vérifier :**
- `app/api/v1/endpoints/files.py` - Activités fichiers
- `app/api/v1/endpoints/users.py` - Activités utilisateurs
- `app/api/v1/endpoints/auth.py` - Activités authentification
- `app/api/v1/endpoints/admin.py` - Activités admin

### 2. Ajouter des logs pour les nouvelles actions

Chaque fois qu'une action importante est effectuée, loguez-la :

```python
# Après chaque opération importante
ActivityService.log_activity(
    db_session=session,
    user_id=current_user.id,
    user_email=current_user.email,
    action_type="action",  # create, update, delete, etc.
    target_type="type",    # file, user, settings, etc.
    target_id=obj.id,
    description="Description détaillée de ce qui s'est passé",
    icon="🎯"
)
```

---

## 💡 Conseils

### ✅ À faire
- Inclure le nom de l'objet modifié
- Mentionner les changements effectués
- Ajouter des métriques (nombre de lignes, taille, etc.)
- Utiliser des emojis pertinents
- Être précis mais concis

### ❌ À éviter
- Descriptions vagues : "Mise à jour", "Création"
- Trop de détails techniques : "UPDATE table SET..."
- Informations sensibles : mots de passe, tokens
- Descriptions trop longues (> 200 caractères)

---

## 🎯 Résultat

Avec ces améliorations, les utilisateurs sauront **exactement** :
- ✅ **Qui** a fait l'action
- ✅ **Quoi** a été fait
- ✅ **Sur quoi** (type et ID)
- ✅ **Quand** ça s'est passé
- ✅ **Détails** de l'opération

---

**📈 Interface améliorée avec hauteur fixe (500px) et scroll !**

