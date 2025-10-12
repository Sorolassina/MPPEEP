# 📁 Path Config - Gestion Centralisée des Chemins

## 🤔 C'est Quoi ?

`path_config.py` est un **gestionnaire centralisé** de tous les chemins (dossiers et fichiers) de votre application.

### 🏗️ Analogie Simple

Imaginez une bibliothèque :

- 📚 **Sans path_config** = Chercher un livre au hasard dans toute la bibliothèque
- 🗺️ **Avec path_config** = Avoir un **plan précis** de où se trouve chaque livre

**path_config = Le plan de rangement de vos fichiers**

---

## 🎯 Pourquoi C'est Utile ?

### ❌ Problème Sans path_config

```python
# Dans auth.py
logo_path = "../../static/images/logo.png"

# Dans users.py  
logo_path = "../../../static/images/logo.png"  # Différent !

# Dans main.py
logo_path = "app/static/images/logo.png"  # Encore différent !

# Problèmes :
# 1. Chemins relatifs fragiles
# 2. Duplication de code
# 3. Erreurs si on déplace un fichier
# 4. Difficile à maintenir
```

### ✅ Solution Avec path_config

```python
# Partout dans l'application
from app.core.path_config import path_config

logo_path = path_config.get_file_url("static", "images/logo.png")
# → "/static/images/logo.png"

# Toujours le même !
# Centralisé !
# Facile à maintenir !
```

---

## 📁 Chemins Disponibles

### Chemins de Base

```python
from app.core.path_config import path_config

# Dossier racine du projet
path_config.BASE_DIR
# → /path/to/mppeep

# Dossier static
path_config.STATIC_DIR
# → /path/to/mppeep/app/static

# Dossier templates
path_config.TEMPLATES_DIR
# → /path/to/mppeep/app/templates

# Dossier uploads
path_config.UPLOADS_DIR
# → /path/to/mppeep/uploads

# Dossier media
path_config.MEDIA_DIR
# → /path/to/mppeep/media
```

### Chemins Spécifiques

```python
# CSS
path_config.STATIC_CSS_DIR
# → /path/to/mppeep/app/static/css

# JavaScript
path_config.STATIC_JS_DIR
# → /path/to/mppeep/app/static/js

# Images
path_config.STATIC_IMAGES_DIR
# → /path/to/mppeep/app/static/images

# Fonts
path_config.STATIC_FONTS_DIR
# → /path/to/mppeep/app/static/fonts
```

---

## 🛠️ Fonctions Utilitaires

### 1️⃣ `get_file_url()` - Obtenir l'URL d'un Fichier

**Rôle :** Génère l'URL web d'un fichier

```python
from app.core.path_config import path_config

# Exemple 1 : Logo
url = path_config.get_file_url("static", "images/logo.png")
# → "/static/images/logo.png"

# Exemple 2 : Fichier uploadé
url = path_config.get_file_url("uploads", "documents/facture.pdf")
# → "/uploads/documents/facture.pdf"

# Exemple 3 : Image utilisateur
url = path_config.get_file_url("media", "avatars/user123.jpg")
# → "/media/avatars/user123.jpg"
```

**Usage dans template :**
```html
<img src="{{ logo_url }}" alt="Logo">
```

---

### 2️⃣ `get_physical_path()` - Obtenir le Chemin Physique

**Rôle :** Obtient le chemin complet sur le disque

```python
from app.core.path_config import path_config

# Exemple 1 : Vérifier si un fichier existe
path = path_config.get_physical_path("static", "images/logo.png")
# → Path("/path/to/mppeep/app/static/images/logo.png")

if path.exists():
    print("✅ Logo trouvé")

# Exemple 2 : Lire un fichier
path = path_config.get_physical_path("uploads", "document.txt")
with open(path, "r") as f:
    content = f.read()

# Exemple 3 : Sauvegarder un fichier
path = path_config.get_physical_path("uploads", "new_file.pdf")
with open(path, "wb") as f:
    f.write(content)
```

---

### 3️⃣ `ensure_directory_exists()` - Créer un Dossier

**Rôle :** Crée un dossier s'il n'existe pas

```python
from app.core.path_config import path_config

# Créer le dossier uploads/documents
upload_dir = path_config.UPLOADS_DIR / "documents"
path_config.ensure_directory_exists(upload_dir)

# Le dossier existe maintenant, même s'il n'existait pas avant
```

---

### 4️⃣ `get_mount_path()` - Obtenir le Chemin de Montage

**Rôle :** Obtient le préfixe URL d'un montage

```python
# Chemin de montage pour "static"
mount_path = path_config.get_mount_path("static")
# → "/static"

# Pour "uploads"
mount_path = path_config.get_mount_path("uploads")
# → "/uploads"
```

---

## 💡 Cas d'Usage Pratiques

### Cas 1 : Upload de Fichier

```python
from fastapi import UploadFile
from app.core.path_config import path_config

@router.post("/upload")
async def upload_file(file: UploadFile):
    # 1. Créer le dossier s'il n'existe pas
    upload_dir = path_config.UPLOADS_DIR / "documents"
    path_config.ensure_directory_exists(upload_dir)
    
    # 2. Sauvegarder le fichier
    file_path = upload_dir / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # 3. Retourner l'URL
    file_url = path_config.get_file_url("uploads", f"documents/{file.filename}")
    
    return {
        "filename": file.filename,
        "url": file_url
    }
```

---

### Cas 2 : Générer une Image Dynamique

```python
from app.core.path_config import path_config
from PIL import Image

@router.get("/generate-thumbnail/{image_id}")
async def generate_thumbnail(image_id: int):
    # 1. Chemin de l'image originale
    original_path = path_config.get_physical_path(
        "uploads", 
        f"images/image_{image_id}.jpg"
    )
    
    # 2. Générer la miniature
    img = Image.open(original_path)
    img.thumbnail((200, 200))
    
    # 3. Sauvegarder
    thumb_path = path_config.get_physical_path(
        "uploads", 
        f"thumbnails/image_{image_id}_thumb.jpg"
    )
    
    # Créer le dossier thumbnails
    path_config.ensure_directory_exists(thumb_path.parent)
    
    img.save(thumb_path)
    
    # 4. Retourner l'URL
    return {
        "url": path_config.get_file_url("uploads", f"thumbnails/image_{image_id}_thumb.jpg")
    }
```

---

### Cas 3 : Vérifier l'Existence d'un Logo

```python
from app.core.path_config import path_config

@router.get("/company-info")
async def get_company_info():
    # Vérifier si le logo existe
    logo_path = path_config.get_physical_path("static", "images/logo.png")
    
    if logo_path.exists():
        logo_url = path_config.get_file_url("static", "images/logo.png")
    else:
        logo_url = path_config.get_file_url("static", "images/default-logo.png")
    
    return {
        "name": "Mon Entreprise",
        "logo": logo_url
    }
```

---

### Cas 4 : Lister les Fichiers d'un Dossier

```python
from app.core.path_config import path_config

@router.get("/documents")
async def list_documents():
    # Chemin physique du dossier
    docs_dir = path_config.UPLOADS_DIR / "documents"
    
    # S'assurer que le dossier existe
    path_config.ensure_directory_exists(docs_dir)
    
    # Lister tous les PDF
    documents = []
    for file_path in docs_dir.glob("*.pdf"):
        # Générer l'URL
        url = path_config.get_file_url("uploads", f"documents/{file_path.name}")
        
        documents.append({
            "name": file_path.name,
            "size": file_path.stat().st_size,
            "url": url
        })
    
    return documents
```

---

## 🗺️ Configuration des Montages

### Qu'est-ce qu'un Montage ?

Un **montage** (mount) est un dossier accessible via HTTP.

```python
# Configuration dans path_config.py
MOUNT_CONFIGS = {
    "static": {
        "path": "/static",              # ← URL
        "directory": "/path/to/static", # ← Dossier physique
        "name": "static"                # ← Nom FastAPI
    },
    "uploads": {
        "path": "/uploads",
        "directory": "/path/to/uploads",
        "name": "uploads"
    },
    "media": {
        "path": "/media",
        "directory": "/path/to/media",
        "name": "media"
    }
}
```

### Utilisation dans main.py

```python
from fastapi.staticfiles import StaticFiles
from app.core.path_config import path_config

# Monter les dossiers
for mount_name, config in path_config.MOUNT_CONFIGS.items():
    app.mount(
        config["path"],
        StaticFiles(directory=config["directory"]),
        name=config["name"]
    )

# Résultat :
# http://localhost:8000/static/css/style.css  ✅
# http://localhost:8000/uploads/doc.pdf       ✅
# http://localhost:8000/media/avatar.jpg      ✅
```

---

## 🔧 Fonctions Avancées

### `get_mount_path()` - Chemin URL

```python
path = path_config.get_mount_path("static")
# → "/static"

path = path_config.get_mount_path("uploads")
# → "/uploads"
```

### `get_mount_directory()` - Dossier Physique

```python
directory = path_config.get_mount_directory("static")
# → "/path/to/mppeep/app/static"
```

---

## 🎨 Templates Jinja2

### Utiliser dans les Templates

```python
# Dans un endpoint
from app.core.path_config import path_config

@router.get("/profile")
async def profile(request: Request):
    logo_url = path_config.get_file_url("static", "images/logo.png")
    
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "logo_url": logo_url
        }
    )
```

```html
<!-- Dans le template -->
<img src="{{ logo_url }}" alt="Logo">
```

### Créer un Filtre Global

```python
# Dans app/templates/__init__.py

from app.core.path_config import path_config

def static_url(file_path: str) -> str:
    """Filtre pour générer une URL static"""
    return path_config.get_file_url("static", file_path)

# Enregistrer le filtre
templates.env.filters["static_url"] = static_url

# Dans le template
<img src="{{ 'images/logo.png'|static_url }}">
```

---

## 📊 Différence URL vs Chemin Physique

### URL (pour le navigateur)

```python
url = path_config.get_file_url("static", "css/style.css")
# → "/static/css/style.css"

# Usage : Dans HTML, liens, redirections
<link href="{{ url }}" rel="stylesheet">
```

### Chemin Physique (pour Python)

```python
path = path_config.get_physical_path("static", "css/style.css")
# → Path("/path/to/mppeep/app/static/css/style.css")

# Usage : Lire, écrire, vérifier existence
if path.exists():
    with open(path) as f:
        content = f.read()
```

---

## 🔄 Workflow Complet : Upload Avatar

```python
from fastapi import UploadFile
from app.core.path_config import path_config
import uuid

@router.post("/upload-avatar")
async def upload_avatar(file: UploadFile, user_id: int):
    # 1. Générer un nom unique
    file_ext = file.filename.split(".")[-1]
    unique_name = f"user_{user_id}_{uuid.uuid4().hex[:8]}.{file_ext}"
    
    # 2. S'assurer que le dossier existe
    avatars_dir = path_config.UPLOADS_DIR / "avatars"
    path_config.ensure_directory_exists(avatars_dir)
    
    # 3. Sauvegarder le fichier
    file_path = path_config.get_physical_path("uploads", f"avatars/{unique_name}")
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # 4. Générer l'URL publique
    avatar_url = path_config.get_file_url("uploads", f"avatars/{unique_name}")
    
    # 5. Sauvegarder l'URL en base de données
    user.avatar_url = avatar_url
    session.add(user)
    session.commit()
    
    return {
        "filename": unique_name,
        "url": avatar_url,
        "size": len(content)
    }
```

---

## 🗂️ Structure des Dossiers

### Organisation Recommandée

```
mppeep/
├── app/
│   ├── static/              ← Fichiers statiques (CSS, JS, images)
│   │   ├── css/
│   │   ├── js/
│   │   ├── images/
│   │   └── fonts/
│   └── templates/           ← Templates HTML
│
├── uploads/                 ← Fichiers uploadés par les utilisateurs
│   ├── avatars/
│   ├── documents/
│   └── temp/
│
└── media/                   ← Fichiers médias (images, vidéos)
    ├── products/
    └── gallery/
```

### Montages Correspondants

```
URL                                 Dossier Physique
───────────────────────────────────────────────────────────
/static/css/style.css           → app/static/css/style.css
/uploads/avatars/user1.jpg      → uploads/avatars/user1.jpg
/media/products/item.png        → media/products/item.png
```

---

## 🎯 Exemples Pratiques

### Exemple 1 : Logo Dynamique

```python
from app.core.path_config import path_config

@router.get("/")
async def home(request: Request):
    # Logo par défaut
    logo = "images/logo.png"
    
    # Logo de Noël si période de fêtes
    from datetime import datetime
    if datetime.now().month == 12:
        logo = "images/logo-christmas.png"
    
    logo_url = path_config.get_file_url("static", logo)
    
    return templates.TemplateResponse(
        "pages/index.html",
        {"request": request, "logo": logo_url}
    )
```

### Exemple 2 : Export CSV

```python
from app.core.path_config import path_config
import csv

@router.get("/export-users")
async def export_users(session: Session):
    # 1. Créer le dossier exports
    exports_dir = path_config.UPLOADS_DIR / "exports"
    path_config.ensure_directory_exists(exports_dir)
    
    # 2. Générer le fichier
    filename = f"users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    file_path = exports_dir / filename
    
    # 3. Écrire le CSV
    users = session.exec(select(User)).all()
    
    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Email", "Nom"])
        
        for user in users:
            writer.writerow([user.id, user.email, user.full_name])
    
    # 4. Retourner l'URL de téléchargement
    download_url = path_config.get_file_url("uploads", f"exports/{filename}")
    
    return {
        "message": "Export créé",
        "url": download_url,
        "filename": filename
    }
```

### Exemple 3 : Servir des Fichiers PDF

```python
from fastapi.responses import FileResponse
from app.core.path_config import path_config

@router.get("/download-invoice/{invoice_id}")
async def download_invoice(invoice_id: int):
    # Chemin physique du PDF
    pdf_path = path_config.get_physical_path(
        "uploads", 
        f"invoices/invoice_{invoice_id}.pdf"
    )
    
    # Vérifier l'existence
    if not pdf_path.exists():
        raise HTTPException(404, detail="Facture non trouvée")
    
    # Servir le fichier
    return FileResponse(
        path=pdf_path,
        filename=f"facture_{invoice_id}.pdf",
        media_type="application/pdf"
    )
```

---

## 🔐 Sécurité

### ⚠️ Attention aux Path Traversal

```python
# ❌ DANGEREUX - Injection de chemin
user_input = "../../etc/passwd"
path = path_config.UPLOADS_DIR / user_input
# → Peut accéder à /etc/passwd !

# ✅ SÉCURISÉ - Nettoyer l'input
from pathlib import Path

user_input = "../../etc/passwd"
safe_name = Path(user_input).name  # → "passwd"
path = path_config.UPLOADS_DIR / safe_name
# → Seulement uploads/passwd
```

### ✅ Validation Recommandée

```python
import os
from pathlib import Path

def is_safe_path(base_dir: Path, file_path: str) -> bool:
    """Vérifie qu'un chemin ne sort pas du dossier de base"""
    try:
        full_path = (base_dir / file_path).resolve()
        return str(full_path).startswith(str(base_dir.resolve()))
    except:
        return False

# Usage
if not is_safe_path(path_config.UPLOADS_DIR, user_filename):
    raise HTTPException(400, detail="Nom de fichier invalide")
```

---

## 🎨 Personnaliser pour Vos Projets

### Ajouter un Nouveau Montage

```python
# Dans path_config.py

class PathConfig:
    def __init__(self):
        # ...
        
        # Nouveau dossier
        self.DOWNLOADS_DIR = BASE_DIR / "downloads"
        
        # Nouveau montage
        self.MOUNT_CONFIGS["downloads"] = {
            "path": "/downloads",
            "directory": str(self.DOWNLOADS_DIR),
            "name": "downloads"
        }

# Dans main.py
for mount_name, config in path_config.MOUNT_CONFIGS.items():
    app.mount(
        config["path"],
        StaticFiles(directory=config["directory"]),
        name=config["name"]
    )
```

### Ajouter des Chemins Spécifiques

```python
class PathConfig:
    def __init__(self):
        # ...
        
        # Chemins métier
        self.INVOICES_DIR = self.UPLOADS_DIR / "invoices"
        self.REPORTS_DIR = self.UPLOADS_DIR / "reports"
        self.TEMP_DIR = self.UPLOADS_DIR / "temp"
```

---

## 📚 Comparaison avec Chemins en Dur

### ❌ Sans path_config

```python
# Partout dans le code
logo_path = "app/static/images/logo.png"
upload_path = "uploads/documents/file.pdf"
temp_path = "app/static/temp/data.json"

# Problèmes :
# - Chemins dupliqués partout
# - Erreurs de frappe
# - Difficile de changer la structure
# - Chemins relatifs fragiles
```

### ✅ Avec path_config

```python
# Centralisé
from app.core.path_config import path_config

logo_path = path_config.get_physical_path("static", "images/logo.png")
upload_path = path_config.get_physical_path("uploads", "documents/file.pdf")
temp_path = path_config.STATIC_DIR / "temp" / "data.json"

# Avantages :
# - Un seul endroit à modifier
# - Autocomplete IDE
# - Pas d'erreurs de frappe
# - Chemins absolus fiables
```

---

## 🔄 Migration de Structure

Si vous changez la structure de vos dossiers :

### Avant

```python
# Ancienne structure
uploads/
└── files/
    ├── document1.pdf
    └── document2.pdf
```

### Après

```python
# Nouvelle structure
uploads/
├── documents/
│   ├── document1.pdf
│   └── document2.pdf
└── images/
    ├── image1.jpg
    └── image2.jpg
```

### Mise à Jour

```python
# Vous changez SEULEMENT dans path_config.py
self.DOCUMENTS_DIR = self.UPLOADS_DIR / "documents"
self.IMAGES_DIR = self.UPLOADS_DIR / "images"

# Tous les appels sont automatiquement mis à jour !
path_config.get_file_url("uploads", "documents/doc.pdf")
# → Fonctionne automatiquement avec la nouvelle structure
```

---

## ✅ Checklist d'Utilisation

- [ ] Importer `path_config` au lieu de chemins en dur
- [ ] Utiliser `get_file_url()` pour les URLs web
- [ ] Utiliser `get_physical_path()` pour les opérations fichiers
- [ ] Appeler `ensure_directory_exists()` avant d'écrire
- [ ] Valider les chemins utilisateurs (sécurité)
- [ ] Utiliser les constantes (STATIC_DIR, UPLOADS_DIR, etc.)

---

## 🆘 Problèmes Courants

### FileNotFoundError

```python
# ❌ Erreur
path = path_config.UPLOADS_DIR / "documents" / "file.pdf"
with open(path) as f:  # → FileNotFoundError !

# ✅ Solution
path = path_config.UPLOADS_DIR / "documents" / "file.pdf"

# Vérifier l'existence
if not path.exists():
    raise HTTPException(404, detail="Fichier non trouvé")

with open(path) as f:
    content = f.read()
```

### Dossier n'existe pas

```python
# ❌ Erreur
path = path_config.UPLOADS_DIR / "new_folder" / "file.txt"
with open(path, "w") as f:  # → FileNotFoundError (dossier n'existe pas)

# ✅ Solution
folder = path_config.UPLOADS_DIR / "new_folder"
path_config.ensure_directory_exists(folder)

path = folder / "file.txt"
with open(path, "w") as f:
    f.write("contenu")
```

---

## 📊 Résumé

| Aspect | Valeur |
|--------|--------|
| **Rôle** | 📁 Gestionnaire centralisé des chemins |
| **Avantages** | Centralisation, cohérence, maintenance |
| **Fonctions** | `get_file_url()`, `get_physical_path()`, `ensure_directory_exists()` |
| **Montages** | static, uploads, media |
| **Usage** | `from app.core.path_config import path_config` |

---

## 🎯 Pour Votre Boilerplate

### ✅ Inclus dans le Boilerplate

```bash
# Copiez ce fichier dans vos nouveaux projets
cp app/core/path_config.py nouveau_projet/app/core/

# Personnalisez selon vos besoins
# - Ajouter des dossiers
# - Modifier les montages
# - Adapter les chemins
```

### ✅ Personnalisation Facile

```python
# Un seul fichier à modifier pour changer toute la structure !
# path_config.py
```

---

**📁 path_config = Le GPS de vos fichiers dans l'application !**

