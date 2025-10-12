# 📸 Système de Photos de Profil

## Vue d'ensemble

Le système de photos de profil permet aux administrateurs d'ajouter des photos pour chaque utilisateur. Les photos sont stockées dans le dossier `/uploads/profiles/`.

## 📊 Modèle de données

### Champ ajouté au modèle User

```python
class User(SQLModel, table=True):
    ...
    profile_picture: Optional[str] = Field(default=None, max_length=500)
    # Stocke le chemin relatif: "profiles/profile_1_20241010_120000.jpg"
```

**Type:** VARCHAR(500) - Peut être NULL  
**Format:** `profiles/{filename}`  
**Exemple:** `profiles/profile_5_20241010_153045.jpg`

## 🛣️ Routes API

### POST `/api/v1/admin/users/{user_id}/upload-photo`

Upload une photo de profil pour un utilisateur.

**Permissions:** Admin uniquement

**Form Data:**
- `photo` (file) - Image à uploader

**Validation:**
- ✅ Formats acceptés: JPG, JPEG, PNG, GIF, WEBP
- ✅ Taille max: 2MB
- ✅ Utilisateur doit exister

**Réponse succès:**
```json
{
    "success": true,
    "message": "Photo de profil uploadée avec succès",
    "photo_url": "/uploads/profiles/profile_5_20241010_153045.jpg"
}
```

**Réponse erreur:**
```json
{
    "success": false,
    "message": "Format non supporté (JPG, PNG, GIF, WEBP uniquement)"
}
```

## 📁 Stockage des fichiers

### Structure des dossiers

```
mppeep/
└── uploads/
    └── profiles/
        ├── profile_1_20241010_120000.jpg
        ├── profile_2_20241010_120530.png
        ├── profile_5_20241010_153045.jpg
        └── ...
```

### Nom des fichiers

Format: `profile_{user_id}_{timestamp}{extension}`

**Composants:**
- `profile_` - Préfixe fixe
- `{user_id}` - ID de l'utilisateur
- `{timestamp}` - Date et heure (format: YYYYMMDD_HHMMSS)
- `{extension}` - Extension du fichier (.jpg, .png, etc.)

**Exemple:** `profile_5_20241010_153045.jpg`
- User ID: 5
- Date: 2024-10-10
- Heure: 15:30:45
- Format: JPG

### Montage dans l'application

```python
# app/main.py
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
```

**Accès:** `http://localhost:8000/uploads/profiles/profile_5_20241010_153045.jpg`

## 🔄 Flux d'upload

### Étape par étape

```
1. Admin clique sur 📸 dans la ligne de l'utilisateur
   ↓
2. Modal s'ouvre avec:
   - Photo actuelle (ou placeholder)
   - Bouton "Choisir une photo"
   ↓
3. Admin sélectionne un fichier
   ↓
4. Validation côté client:
   - Taille < 2MB ?
   ↓
5. Upload vers /api/v1/admin/users/{id}/upload-photo
   ↓
6. Validation côté serveur:
   - Format accepté ?
   - Taille < 2MB ?
   - Utilisateur existe ?
   ↓
7. Sauvegarde du fichier:
   - Génération nom unique
   - Écriture dans uploads/profiles/
   - Suppression ancienne photo (si existe)
   ↓
8. Mise à jour DB:
   - UPDATE user SET profile_picture = 'profiles/...' WHERE id = X
   ↓
9. Réponse au client:
   - Succès + URL de la photo
   ↓
10. Rechargement de la page
    - Nouvelle photo affichée dans le tableau ✅
```

## 🎨 Affichage des photos

### Dans le tableau de gestion

```html
<!-- Si photo existe -->
<img src="/uploads/{{ user.profile_picture }}" 
     alt="Photo {{ user.full_name }}" 
     class="user-photo">

<!-- Si pas de photo -->
<div class="user-photo-placeholder">👤</div>
```

**Styles:**
```css
.user-photo {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid var(--gray-300);
}

.user-photo-placeholder {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background-color: var(--gray-200);
    font-size: 1.5rem;
}
```

### Dans la navbar (utilisateur connecté)

```html
{% if current_user.profile_picture %}
    <img src="/uploads/{{ current_user.profile_picture }}" 
         alt="Photo profil" 
         class="nav-user-photo">
{% else %}
    👤
{% endif %}
```

**Styles:**
```css
.nav-user-photo {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid var(--white-color);
}
```

### Dans le modal d'upload

```html
<img id="current-photo-preview" 
     src="/uploads/profiles/..." 
     alt="Photo actuelle" 
     class="photo-preview">
```

**Styles:**
```css
.photo-preview {
    width: 150px;
    height: 150px;
    border-radius: 50%;
    object-fit: cover;
    border: 3px solid var(--gray-300);
}
```

## 🔐 Sécurité

### Validation côté client

```javascript
// Vérifier la taille
if (file.size > 2 * 1024 * 1024) {
    showMessage('Fichier trop volumineux (max 2MB)', 'error');
    return;
}
```

### Validation côté serveur

```python
# Vérifier le format
allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
if file_ext not in allowed_extensions:
    return error("Format non supporté")

# Vérifier la taille
if len(content) > 2 * 1024 * 1024:
    return error("Fichier trop volumineux")
```

### Nettoyage des anciennes photos

```python
# Supprimer l'ancienne photo avant de sauvegarder la nouvelle
if user.profile_picture:
    old_path = path_config.UPLOADS_DIR / user.profile_picture
    if old_path.exists():
        old_path.unlink()  # Suppression fichier
```

**Avantage:** Évite l'accumulation de fichiers inutilisés

## 📊 Migration de la base de données

### Pour les installations existantes

Si la table `user` existe déjà sans la colonne `profile_picture` :

```bash
# Exécuter le script de migration
cd mppeep
python scripts/add_profile_picture_column.py
```

**Le script:**
- ✅ Vérifie si la colonne existe déjà
- ✅ Ajoute la colonne si nécessaire
- ✅ Compatible SQLite et PostgreSQL
- ✅ Logs détaillés

**SQL généré (SQLite):**
```sql
ALTER TABLE user ADD COLUMN profile_picture VARCHAR(500);
```

**SQL généré (PostgreSQL):**
```sql
ALTER TABLE "user" ADD COLUMN profile_picture VARCHAR(500);
```

### Pour les nouvelles installations

La colonne est automatiquement créée lors de l'initialisation :

```python
# scripts/init_db.py
SQLModel.metadata.create_all(engine)
# ✅ Crée la table user avec profile_picture
```

## 💾 Gestion du stockage

### Espace disque

**Par utilisateur:** ~50-500 KB (photo compressée)  
**Pour 1000 utilisateurs:** ~50-500 MB maximum

### Nettoyage automatique

Quand une nouvelle photo est uploadée:
```python
# L'ancienne photo est automatiquement supprimée
if user.profile_picture:
    old_path.unlink()  # Supprime le fichier

# Puis la nouvelle est sauvegardée
user.profile_picture = new_path
```

### Nettoyage manuel (si besoin)

```python
# Script pour nettoyer les photos orphelines
from pathlib import Path
from app.models.user import User

profiles_dir = Path("uploads/profiles")
db_photos = [u.profile_picture for u in session.exec(select(User)).all()]

for file in profiles_dir.glob("*.jpg"):
    if f"profiles/{file.name}" not in db_photos:
        file.unlink()  # Photo orpheline supprimée
```

## 🎨 Interface utilisateur

### Modal d'upload

```
┌──────────────────────────────────────────────┐
│  📸 Photo de Profil                    ×     │
├──────────────────────────────────────────────┤
│                                               │
│  ┌─────────────┐     ┌─────────────┐        │
│  │Photo actuelle│     │Nouvelle photo│        │
│  │             │     │              │        │
│  │   ⭕       │     │  📁 Choisir  │        │
│  │   Photo    │     │  une photo   │        │
│  │             │     │              │        │
│  │  John Doe   │     │JPG,PNG,GIF   │        │
│  │             │     │Max 2MB       │        │
│  └─────────────┘     └─────────────┘        │
│                                               │
└──────────────────────────────────────────────┘
```

### Tableau des utilisateurs

```
┌────────┬────┬──────────┬───────────┬───────┬────────┬─────────────┬─────────┐
│ Photo  │ ID │   Nom    │   Email   │ Type  │ Statut │  Créé le    │ Actions │
├────────┼────┼──────────┼───────────┼───────┼────────┼─────────────┼─────────┤
│  ⭕   │ #1 │ John Doe │ john@...  │ Admin │ Actif  │ 10/10/2024  │ 📸✏️🗑️ │
│  👤   │ #2 │ Jane Doe │ jane@...  │ User  │ Actif  │ 10/10/2024  │ 📸✏️🗑️ │
└────────┴────┴──────────┴───────────┴───────┴────────┴─────────────┴─────────┘
```

## 🚀 Utilisation

### Pour l'administrateur

1. **Aller dans Gestion Utilisateurs**
2. **Cliquer sur 📸** dans la ligne de l'utilisateur
3. **Modal s'ouvre** avec la photo actuelle
4. **Cliquer "Choisir une photo"**
5. **Sélectionner un fichier** (JPG, PNG, etc.)
6. **Upload automatique** avec overlay de chargement
7. **Page se recharge** avec la nouvelle photo ✅

### Pour afficher la photo dans un template

```html
<!-- Photo de profil ou placeholder -->
{% if user.profile_picture %}
    <img src="/uploads/{{ user.profile_picture }}" alt="Photo">
{% else %}
    <img src="{{ static_url('images/default-avatar.svg') }}" alt="Avatar par défaut">
{% endif %}
```

## 📝 Logs

### Logs générés

```
📸 Photo de profil uploadée pour john@example.com par admin@mppeep.com
```

**Information tracée:**
- Email de l'utilisateur concerné
- Email de l'admin qui a fait l'upload
- Timestamp automatique (dans les logs)

## 🔧 Configuration

### Taille maximale

Modifier dans `admin.py` :

```python
# Actuellement: 2MB
MAX_PROFILE_PICTURE_SIZE = 2 * 1024 * 1024

# Pour changer en 5MB:
MAX_PROFILE_PICTURE_SIZE = 5 * 1024 * 1024
```

### Formats acceptés

Modifier dans `admin.py` :

```python
allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']

# Pour ajouter SVG:
allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
```

### Dossier de stockage

Modifier dans `admin.py` :

```python
# Actuellement: uploads/profiles/
profiles_dir = path_config.UPLOADS_DIR / "profiles"

# Pour changer:
profiles_dir = path_config.UPLOADS_DIR / "avatars"
```

## ⚡ Performance

### Optimisations

1. **Compression automatique** (future)
```python
from PIL import Image

# Redimensionner et compresser
img = Image.open(file_path)
img.thumbnail((400, 400))
img.save(file_path, optimize=True, quality=85)
```

2. **Formats WebP** (meilleure compression)
```python
# Convertir en WebP
img.save(file_path.with_suffix('.webp'), 'WEBP', quality=85)
```

3. **CDN** (production)
```python
# Upload vers S3/Cloudflare
upload_to_cdn(file_path)
user.profile_picture = cdn_url
```

## 🔄 Workflow complet

### Scénario: Admin upload photo pour John Doe (ID=5)

```
1. Admin clique 📸 sur ligne de John
   ↓
2. GET /api/v1/admin/users/5/get
   Response: {user: {id: 5, profile_picture: null}}
   ↓
3. Modal s'ouvre
   Photo actuelle: 👤 (placeholder)
   ↓
4. Admin clique "Choisir une photo"
   Sélectionne: john_photo.jpg (500KB)
   ↓
5. JavaScript uploadUserPhoto()
   - Vérification taille: 500KB < 2MB ✅
   - FormData: {photo: john_photo.jpg}
   ↓
6. POST /api/v1/admin/users/5/upload-photo
   ↓
7. Serveur valide:
   - Extension: .jpg ✅
   - Taille: 500KB < 2MB ✅
   - User existe: ID=5 ✅
   ↓
8. Serveur sauvegarde:
   - Nom généré: profile_5_20241010_153045.jpg
   - Sauvegarde dans: uploads/profiles/
   - Chemin DB: profiles/profile_5_20241010_153045.jpg
   ↓
9. UPDATE user
   SET profile_picture = 'profiles/profile_5_20241010_153045.jpg'
   WHERE id = 5;
   ↓
10. Response: {success: true, photo_url: "/uploads/..."}
    ↓
11. Page se recharge
    ↓
12. Tableau affiche:
    ⭕ Photo de John au lieu de 👤 ✅
```

## 🎨 Affichage par défaut

### Avatar par défaut

Fichier: `app/static/images/default-avatar.svg`

**SVG simple:**
```svg
<svg viewBox="0 0 100 100">
  <!-- Cercle gris -->
  <circle cx="50" cy="50" r="50" fill="#e9ecef"/>
  <!-- Icône utilisateur -->
  <circle cx="50" cy="35" r="15" fill="#6c757d"/>
  <path d="M 20 85 Q 20 60 50 60 Q 80 60 80 85 Z" fill="#6c757d"/>
</svg>
```

**Utilisation:**
```html
{% if not user.profile_picture %}
    <img src="{{ static_url('images/default-avatar.svg') }}" alt="Avatar">
{% endif %}
```

## 📱 Responsive

### Sur mobile

```css
@media (max-width: 768px) {
    .photo-upload-container {
        grid-template-columns: 1fr;  /* 1 colonne */
    }
    
    .users-table {
        min-width: 900px;  /* Scroll horizontal */
    }
}
```

## 🔍 Debug

### Vérifier les photos uploadées

```bash
# Liste des photos
ls -lh uploads/profiles/

# Exemple de sortie:
# profile_1_20241010_120000.jpg  (250K)
# profile_5_20241010_153045.jpg  (500K)
# profile_12_20241010_160000.png (350K)
```

### Vérifier en base de données

```sql
-- SQLite
SELECT id, email, profile_picture FROM user WHERE profile_picture IS NOT NULL;

-- PostgreSQL
SELECT id, email, profile_picture FROM "user" WHERE profile_picture IS NOT NULL;
```

### Vérifier l'accessibilité

```bash
# La photo doit être accessible
curl http://localhost:8000/uploads/profiles/profile_5_20241010_153045.jpg

# Doit retourner l'image (pas 404)
```

## 🔧 Maintenance

### Supprimer une photo

```python
# Via l'interface (future fonctionnalité)
DELETE /api/v1/admin/users/{id}/delete-photo

# Manuellement
from app.models.user import User

user = session.get(User, 5)
if user.profile_picture:
    # Supprimer le fichier
    (path_config.UPLOADS_DIR / user.profile_picture).unlink()
    # Mettre à jour la DB
    user.profile_picture = None
    session.commit()
```

### Migrer les photos vers un CDN

```python
# Script de migration
for user in session.exec(select(User)).all():
    if user.profile_picture:
        local_path = path_config.UPLOADS_DIR / user.profile_picture
        cdn_url = upload_to_cdn(local_path)
        user.profile_picture = cdn_url
        session.commit()
```

## 📚 Checklist d'implémentation

- ✅ Modèle User mis à jour (profile_picture field)
- ✅ Route d'upload créée (/upload-photo)
- ✅ Dossier uploads/profiles créé automatiquement
- ✅ Modal d'upload dans l'interface
- ✅ Validation format et taille
- ✅ Suppression ancienne photo automatique
- ✅ Affichage dans le tableau
- ✅ Affichage dans la navbar
- ✅ Styles CSS pour les photos
- ✅ Loading overlay pendant l'upload
- ✅ Messages de succès/erreur
- ✅ Logs complets
- ✅ Script de migration pour DB existantes
- ✅ Avatar par défaut (SVG)
- ✅ Responsive design

## 🎯 Améliorations futures

- [ ] Crop/redimensionnement côté client avant upload
- [ ] Compression automatique des images
- [ ] Support du drag & drop
- [ ] Prévisualisation avant upload
- [ ] Suppression de photo (bouton dédié)
- [ ] Galerie de photos pour choisir
- [ ] Filtres et effets (noir & blanc, etc.)
- [ ] Miniatures automatiques (thumbnails)

---

**🎉 Le système de photos de profil est maintenant opérationnel !**

