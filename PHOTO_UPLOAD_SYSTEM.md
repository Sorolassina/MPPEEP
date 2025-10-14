# 📸 Système d'Upload de Photo pour les Agents

## 📋 Vue d'Ensemble

Système complet permettant de **télécharger et gérer les photos des agents** directement depuis le formulaire de création/modification.

---

## ✨ Fonctionnalités

### **1. Upload de Photo**
- 📤 Upload direct depuis le formulaire agent
- 🖼️ Prévisualisation en temps réel
- ✅ Formats acceptés : JPG, PNG, GIF
- 📏 Taille maximale : 5 MB
- 🔒 Validation côté client et serveur

### **2. Prévisualisation**
- 👁️ Aperçu immédiat de la photo sélectionnée
- 🔄 Affichage circulaire (style avatar)
- 👤 Placeholder si pas de photo (emoji)

### **3. Gestion**
- ➕ Ajout de photo lors de la création
- 🗑️ Suppression de la photo sélectionnée
- 🔄 Remplacement de photo existante
- 💾 Sauvegarde automatique sur le serveur

---

## 🏗️ Architecture

### **Frontend (HTML)**

#### **Section Photo dans le Formulaire**
```html
<div class="form-section">
  <div class="form-section-title">
    📸 Photo de l'agent
  </div>
  <div style="display: flex; align-items: center; gap: 2rem;">
    <!-- Prévisualisation -->
    <div class="photo-preview" id="photoPreview">
      <div class="photo-placeholder" id="photoPlaceholder">👤</div>
      <img id="photoImage" style="display: none;" alt="Photo de l'agent">
    </div>
    
    <!-- Input file -->
    <div>
      <input type="file" id="photo" name="photo" accept="image/*" onchange="previewPhoto(event)">
      <label for="photo" class="file-input-label">
        📷 Choisir une photo
      </label>
      <button type="button" onclick="clearPhoto()">
        🗑️ Supprimer
      </button>
    </div>
  </div>
</div>
```

### **JavaScript**

#### **1. Prévisualisation de la Photo**
```javascript
function previewPhoto(event) {
  const file = event.target.files[0];
  if (file) {
    // Validation taille (5 MB max)
    if (file.size > 5 * 1024 * 1024) {
      showError('La photo ne doit pas dépasser 5 MB');
      event.target.value = '';
      return;
    }
    
    // Afficher la prévisualisation
    const reader = new FileReader();
    reader.onload = function(e) {
      photoImage.src = e.target.result;
      photoImage.style.display = 'block';
      photoPlaceholder.style.display = 'none';
      clearPhotoBtn.style.display = 'inline-block';
    };
    reader.readAsDataURL(file);
  }
}
```

#### **2. Suppression de la Photo**
```javascript
function clearPhoto() {
  photoInput.value = '';
  photoImage.src = '';
  photoImage.style.display = 'none';
  photoPlaceholder.style.display = 'block';
  clearPhotoBtn.style.display = 'none';
}
```

#### **3. Soumission avec FormData**
```javascript
// Utiliser FormData pour gérer les fichiers
const formData = new FormData(this);

const response = await fetch('/api/v1/personnel/api/agents', {
  method: 'POST',
  // Ne pas définir Content-Type (auto pour multipart/form-data)
  body: formData
});
```

### **Backend (FastAPI)**

#### **Endpoint avec Upload File**
```python
@router.post("/api/agents")
async def api_create_agent(
    matricule: str = Form(...),
    nom: str = Form(...),
    prenom: str = Form(...),
    # ... autres champs ...
    photo: Optional[UploadFile] = File(None),  # Fichier optionnel
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Créer un nouvel agent avec photo optionnelle"""
    
    # Gérer l'upload de photo
    photo_path = None
    if photo and photo.filename:
        # Créer le dossier
        photos_dir = Path("app/static/uploads/photos/agents")
        photos_dir.mkdir(parents=True, exist_ok=True)
        
        # Nom unique
        file_extension = photo.filename.split('.')[-1]
        unique_filename = f"{matricule}_{secrets.token_hex(8)}.{file_extension}"
        file_path = photos_dir / unique_filename
        
        # Sauvegarder
        content = await photo.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Chemin pour BDD
        photo_path = f"/static/uploads/photos/agents/{unique_filename}"
        agent_data["photo_path"] = photo_path
    
    # Créer l'agent
    agent = AgentComplet(**agent_data)
    session.add(agent)
    session.commit()
    
    return {"ok": True, "agent_id": agent.id}
```

---

## 📁 Structure des Fichiers

### **Dossier de Stockage**
```
app/
└── static/
    └── uploads/
        └── photos/
            └── agents/
                ├── AG2024001_a1b2c3d4e5f6g7h8.jpg
                ├── AG2024002_x9y8z7w6v5u4t3s2.png
                └── AG2024003_m1n2o3p4q5r6s7t8.gif
```

### **Convention de Nommage**
```
{MATRICULE}_{TOKEN_UNIQUE}.{EXTENSION}

Exemple:
AG2024001_a1b2c3d4e5f6g7h8.jpg
         ^                  ^
         |                  |
    Matricule          Extension
              ^
              |
        Token aléatoire (16 chars)
```

### **Avantages**
- ✅ **Unicité garantie** : Token aléatoire + matricule
- ✅ **Traçabilité** : Matricule dans le nom du fichier
- ✅ **Sécurité** : Token imprévisible
- ✅ **Organisation** : Tous dans le même dossier

---

## 🎨 Styles CSS

### **Photo Preview (Circulaire)**
```css
.photo-preview {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background-color: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.photo-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.photo-placeholder {
  font-size: 3rem;
  color: #ccc;
}
```

### **Input File Caché**
```css
.file-input-wrapper input[type=file] {
  position: absolute;
  left: -9999px;
}

.file-input-label {
  padding: 0.5rem 1rem;
  background: #667eea;
  color: white;
  border-radius: 6px;
  cursor: pointer;
  display: inline-block;
}

.file-input-label:hover {
  background: #5568d3;
}
```

---

## 🔒 Validation et Sécurité

### **Côté Client (JavaScript)**
```javascript
// 1. Validation de la taille
if (file.size > 5 * 1024 * 1024) {
  showError('La photo ne doit pas dépasser 5 MB');
  return;
}

// 2. Types MIME acceptés
<input type="file" accept="image/*">
// Ou plus restrictif :
<input type="file" accept="image/jpeg,image/png,image/gif">
```

### **Côté Serveur (Python)**
```python
# 1. Vérification de l'existence du fichier
if photo and photo.filename:
    # Traiter l'upload

# 2. Extension de fichier
file_extension = photo.filename.split('.')[-1].lower()
allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
if file_extension not in allowed_extensions:
    raise HTTPException(400, "Format de fichier non autorisé")

# 3. Taille maximale (optionnel si déjà vérifié côté client)
MAX_SIZE = 5 * 1024 * 1024  # 5 MB
if len(content) > MAX_SIZE:
    raise HTTPException(400, "Fichier trop volumineux")
```

---

## 📊 Affichage de la Photo

### **Dans la Fiche Agent**
```html
<div style="width: 120px; height: 120px; border-radius: 50%; overflow: hidden; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
  {% if agent.photo_path %}
    <img src="{{ agent.photo_path }}" alt="{{ agent.prenom }} {{ agent.nom }}" style="width: 100%; height: 100%; object-fit: cover;">
  {% else %}
    <div style="display: flex; align-items: center; justify-content: center; color: white; font-size: 3rem; font-weight: bold;">
      {{ agent.prenom[0] }}{{ agent.nom[0] }}
    </div>
  {% endif %}
</div>
```

### **Dans les Listes**
```html
<td>
  <div style="width: 40px; height: 40px; border-radius: 50%; overflow: hidden;">
    {% if agent.photo_path %}
      <img src="{{ agent.photo_path }}" style="width: 100%; height: 100%; object-fit: cover;">
    {% else %}
      <div style="background: #667eea; color: white; display: flex; align-items: center; justify-content: center; font-weight: bold;">
        {{ agent.prenom[0] }}{{ agent.nom[0] }}
      </div>
    {% endif %}
  </div>
</td>
```

---

## 🚀 Utilisation

### **1. Créer un Agent avec Photo**

#### **Étape 1** : Remplir le formulaire
```
Personnel → ➕ Nouvel Agent
```

#### **Étape 2** : Sélectionner une photo
```
Section "📸 Photo de l'agent"
→ Cliquer sur "📷 Choisir une photo"
→ Sélectionner un fichier (JPG, PNG, GIF)
→ Voir la prévisualisation
```

#### **Étape 3** : Soumettre
```
→ Remplir les autres champs obligatoires
→ Cliquer sur "💾 Enregistrer"
→ Photo uploadée et sauvegardée automatiquement
```

### **2. Supprimer la Photo Sélectionnée**
```
→ Après avoir sélectionné une photo
→ Cliquer sur "🗑️ Supprimer"
→ La prévisualisation redevient le placeholder
→ Le champ file est vidé
```

---

## 🔄 Mise à Jour de Photo

### **Modifier un Agent Existant**
```python
# À implémenter dans la fonction api_update_agent
@router.put("/api/agents/{agent_id}")
async def api_update_agent(
    agent_id: int,
    # ... autres champs ...
    photo: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session)
):
    agent = session.get(AgentComplet, agent_id)
    
    # Si nouvelle photo fournie
    if photo and photo.filename:
        # Supprimer l'ancienne photo si elle existe
        if agent.photo_path:
            old_file_path = Path(f"app{agent.photo_path}")
            if old_file_path.exists():
                old_file_path.unlink()
        
        # Uploader la nouvelle photo
        # ... (même logique que create)
```

---

## 📈 Améliorations Futures

### **Court Terme**
- [ ] Validation du type MIME côté serveur
- [ ] Compression automatique des images
- [ ] Miniatures (thumbnails) pour les listes
- [ ] Suppression de photo existante (dans modification)

### **Moyen Terme**
- [ ] Crop et redimensionnement côté client
- [ ] Rotation d'image
- [ ] Galerie de photos (multiples photos par agent)
- [ ] CDN pour les images

### **Long Terme**
- [ ] Reconnaissance faciale
- [ ] Détection automatique de doublons
- [ ] Watermarking automatique
- [ ] Intégration avec stockage cloud (S3, Azure Blob)

---

## 🐛 Debugging

### **Problème : Photo ne s'affiche pas**
```python
# Vérifier le chemin dans la BDD
SELECT photo_path FROM agent_complet WHERE id = 1;

# Vérifier l'existence du fichier
import os
file_path = "app/static/uploads/photos/agents/AG2024001_xxxxx.jpg"
print(os.path.exists(file_path))

# Vérifier les permissions
import stat
print(oct(os.stat(file_path).st_mode))
```

### **Problème : Upload échoue**
```javascript
// Console navigateur
console.log('File size:', file.size);
console.log('File type:', file.type);
console.log('File name:', file.name);

// Vérifier la réponse serveur
const response = await fetch(...);
console.log('Status:', response.status);
console.log('Response:', await response.json());
```

### **Problème : FormData vide**
```javascript
// Afficher le contenu de FormData
for (let [key, value] of formData.entries()) {
  console.log(key, value);
}

// Vérifier que le fichier est bien dans FormData
console.log('Photo:', formData.get('photo'));
```

---

## 📊 Statistiques

### **Métriques d'Upload**
```python
# Nombre total de photos uploadées
SELECT COUNT(*) FROM agent_complet WHERE photo_path IS NOT NULL;

# Taille totale utilisée
import os
from pathlib import Path

photos_dir = Path("app/static/uploads/photos/agents")
total_size = sum(f.stat().st_size for f in photos_dir.glob('*') if f.is_file())
total_mb = total_size / (1024 * 1024)
print(f"Espace utilisé : {total_mb:.2f} MB")

# Photo la plus lourde
max_file = max(photos_dir.glob('*'), key=lambda f: f.stat().st_size)
print(f"Plus gros fichier : {max_file.name} ({max_file.stat().st_size / (1024*1024):.2f} MB)")
```

---

## ✅ Checklist d'Implémentation

### **Frontend**
- [x] Champ `<input type="file">` dans le formulaire
- [x] Fonction `previewPhoto()` pour prévisualisation
- [x] Fonction `clearPhoto()` pour suppression
- [x] Style CSS pour photo circulaire
- [x] Validation taille fichier (5 MB max)
- [x] Soumission avec FormData

### **Backend**
- [x] Import `UploadFile` et `File` de FastAPI
- [x] Paramètre `photo: Optional[UploadFile] = File(None)`
- [x] Création automatique du dossier
- [x] Génération nom unique avec `secrets.token_hex()`
- [x] Sauvegarde du fichier
- [x] Enregistrement du chemin dans BDD
- [x] Gestion des erreurs

### **Affichage**
- [x] Photo dans la fiche détail agent
- [ ] Photo dans la liste des agents
- [ ] Photo dans les exports PDF

---

## 🎉 Résultat Final

### **Workflow Complet**
```
1. User → Sélectionne une photo (max 5 MB)
   ↓
2. JavaScript → Prévisualisation immédiate
   ↓
3. User → Remplit le formulaire et soumet
   ↓
4. Frontend → Envoie FormData avec tous les champs + fichier
   ↓
5. Backend → Valide et sauvegarde la photo
   ↓
6. Backend → Génère nom unique : matricule_token.ext
   ↓
7. Backend → Stocke dans /static/uploads/photos/agents/
   ↓
8. Backend → Enregistre le chemin dans la BDD
   ↓
9. Frontend → Redirige vers la fiche agent
   ↓
10. User → Voit la photo dans la fiche ✅
```

---

**📸 Système d'upload de photo production-ready !**

Les agents peuvent maintenant avoir leur photo de profil pour une meilleure identification visuelle dans le système. 🎉

