# 📁 Système de Gestion de Fichiers - MPPEEP Dashboard

## 🎯 Vue d'Ensemble

Le système de gestion de fichiers permet d'**uploader, traiter et gérer des fichiers Excel** avec métadonnées complètes et traitement automatique selon le type de fichier.

---

## 🏗️ Architecture

### Composants Principaux

```
📦 Système de Fichiers
├── 🗄️  Modèle de données (File)
├── 📋 Schémas Pydantic (validation)
├── 🔧 Services
│   ├── FileService (gestion CRUD)
│   └── ExcelProcessorService (traitement Excel)
├── 🌐 Endpoints API (/api/v1/files)
└── 🎨 Interface utilisateur (/fichiers)
```

---

## 📂 Structure des Dossiers

Les dossiers sont **créés automatiquement** au démarrage de l'application dans `app/core/path_config.py`.

```
uploads/files/
├── raw/        ← Fichiers originaux uploadés
├── processed/  ← Fichiers après traitement (futur usage)
└── archive/    ← Fichiers archivés
```

**Configuration centralisée dans :** `app/core/path_config.py`

---

## 🗄️ Modèle de Base de Données

### Table `file`

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | Integer | Identifiant unique |
| `original_filename` | String | Nom original du fichier |
| `stored_filename` | String | Nom stocké (renommé) |
| `file_path` | String | Chemin complet du fichier |
| `file_size` | Integer | Taille en bytes |
| `mime_type` | String | Type MIME |
| **Métadonnées** | | |
| `file_type` | Enum | Type de fichier (budget, dépenses, etc.) |
| `program` | String | Programme concerné |
| `period` | String | Période (ex: "2024-01", "Q1-2024") |
| `title` | String | Titre descriptif |
| `description` | String | Description (optionnel) |
| **Traitement** | | |
| `status` | Enum | Statut (uploaded, processing, processed, error, archived) |
| `processing_error` | String | Message d'erreur si échec |
| `rows_processed` | Integer | Nombre de lignes traitées |
| `rows_failed` | Integer | Nombre de lignes en échec |
| `processed_at` | DateTime | Date de traitement |
| **Suivi** | | |
| `uploaded_by` | Integer | ID de l'utilisateur |
| `created_at` | DateTime | Date de création |
| `updated_at` | DateTime | Date de modification |

---

## 📋 Types de Fichiers Supportés

Définis dans `app/core/enums.py` → `FileType`

| Type | Description | Traitement |
|------|-------------|-----------|
| `budget` | 💰 Budget | Traitement spécifique budgétaire |
| `depenses` | 💸 Dépenses | Extraction des dépenses |
| `revenus` | 💵 Revenus | Extraction des revenus |
| `personnel` | 👥 Personnel | Données RH |
| `rapport_activite` | 📋 Rapport d'activité | Rapports d'activité |
| `beneficiaires` | 👤 Bénéficiaires | Liste des bénéficiaires |
| `indicateurs` | 📊 Indicateurs | Indicateurs de performance |
| `autre` | 📄 Autre | Traitement générique |

---

## 🔄 Workflow de Traitement

### 1️⃣ Upload du Fichier

```
Client (Interface Web)
  ↓
POST /api/v1/files/upload
  ↓
Validation (extension, taille, métadonnées)
  ↓
FileService.save_file()
  ├─ Génération nom fichier: {type}_{program}_{period}_{timestamp}.xlsx
  ├─ Sauvegarde physique dans uploads/files/raw/
  └─ Création entrée en DB avec status = "uploaded"
  ↓
Lancement traitement en arrière-plan (BackgroundTasks)
```

### 2️⃣ Traitement du Fichier

```
process_file_background()
  ↓
Mise à jour status → "processing"
  ↓
ExcelProcessorService.process_file()
  ├─ Lecture du fichier Excel avec pandas
  ├─ Dispatcher selon file_type:
  │   ├─ budget → _process_budget()
  │   ├─ depenses → _process_depenses()
  │   ├─ revenus → _process_revenus()
  │   └─ autre → _process_generic()
  ├─ Extraction et validation des données
  └─ Retour: (success, rows_processed, rows_failed, error_msg, data)
  ↓
Mise à jour status → "processed" ou "error"
  ├─ Enregistrement des statistiques (rows_processed, rows_failed)
  └─ Sauvegarde de error_message si échec
```

### 3️⃣ Consultation et Actions

- **Liste** : GET `/api/v1/files/`
- **Détails** : GET `/api/v1/files/{id}`
- **Statut** : GET `/api/v1/files/{id}/status`
- **Retraitement** : POST `/api/v1/files/{id}/reprocess`
- **Archive** : POST `/api/v1/files/{id}/archive`
- **Suppression** : DELETE `/api/v1/files/{id}`
- **Prévisualisation** : GET `/api/v1/files/{id}/preview`

---

## 🎨 Interface Utilisateur

### Page : `/fichiers`

**Fonctionnalités :**

1. **Upload de fichier**
   - Formulaire avec métadonnées
   - Drag & drop (futur)
   - Validation côté client

2. **Liste des fichiers**
   - Tableau avec toutes les informations
   - Filtres par type, statut, programme
   - Actions : voir, retraiter, supprimer

3. **Statistiques**
   - Total fichiers
   - Fichiers traités
   - Fichiers en traitement
   - Espace utilisé

4. **Auto-refresh**
   - Actualisation automatique toutes les 10 secondes
   - Pour suivre le traitement en temps réel

---

## 🔧 Services

### FileService

**Responsabilités :**
- CRUD des fichiers en DB
- Sauvegarde physique des fichiers
- Gestion du cycle de vie (upload → archive → delete)
- Statistiques

**Méthodes principales :**
```python
# Création
save_file(session, upload_file, metadata, uploaded_by)

# Lecture
get_file_by_id(session, file_id)
get_all_files(session, skip, limit, filters...)
count_files(session, filters...)

# Mise à jour
update_file_status(session, file_id, status, rows_processed, ...)
update_file_metadata(session, file_id, metadata)

# Suppression
delete_file(session, file_id)
archive_file(session, file_id)

# Statistiques
get_statistics(session)
```

### ExcelProcessorService

**Responsabilités :**
- Lecture des fichiers Excel
- Traitement spécifique par type
- Validation de la structure
- Extraction des données

**Méthodes principales :**
```python
# Traitement principal
process_file(file_path, file_type, metadata)

# Traitements spécifiques
_process_budget(df, metadata)
_process_depenses(df, metadata)
_process_revenus(df, metadata)
_process_personnel(df, metadata)
_process_rapport_activite(df, metadata)
_process_beneficiaires(df, metadata)
_process_indicateurs(df, metadata)
_process_generic(df, metadata)

# Utilitaires
validate_file_structure(file_path, file_type)
get_file_preview(file_path, nrows=10)
```

---

## ⚙️ Configuration

### Dépendances Requises

Dans `pyproject.toml` :
```toml
"pandas>=2.0.0",   # Traitement Excel
"openpyxl>=3.1.0", # Lecture .xlsx
```

### Installation

```bash
# Avec uv (recommandé)
uv sync

# Ou avec pip
pip install pandas openpyxl
```

---

## 🔒 Sécurité

### Validations

1. **Extension de fichier** : Seuls `.xlsx` et `.xls` acceptés
2. **Taille maximum** : 50 MB par défaut (configurable)
3. **Authentification** : Utilisateur connecté requis
4. **Autorisation** : Vérification de l'utilisateur

### Recommandations

- ⚠️ Scanner antivirus pour les fichiers uploadés (à ajouter)
- ⚠️ Limiter le taux d'upload (rate limiting)
- ⚠️ Nettoyer périodiquement les fichiers archivés
- ⚠️ Backup régulier du dossier uploads/

---

## 🚀 Personnalisation du Traitement

### Ajouter un Nouveau Type de Fichier

#### 1. Ajouter le type dans `app/core/enums.py`

```python
class FileType(str, Enum):
    # ... types existants
    NOUVEAU_TYPE = "nouveau_type"
```

#### 2. Créer la méthode de traitement dans `ExcelProcessorService`

```python
@classmethod
def _process_nouveau_type(cls, df: pd.DataFrame, metadata: dict) -> Tuple[bool, int, int, Optional[str], List[Dict]]:
    """
    Traitement spécifique pour NOUVEAU_TYPE
    """
    logger.info("🆕 Traitement d'un fichier NOUVEAU_TYPE")
    
    try:
        processed_data = []
        rows_failed = 0
        
        # Nettoyer les colonnes
        df.columns = df.columns.str.strip()
        
        # Traiter chaque ligne
        for idx, row in df.iterrows():
            try:
                record = {
                    'row_index': idx,
                    'colonne1': row['Colonne1'],
                    'colonne2': row['Colonne2'],
                    # ... extraire les données
                    'period': metadata.get('period'),
                    'program': metadata.get('program'),
                    'processed_at': datetime.now().isoformat()
                }
                
                # Validation
                if record['colonne1']:
                    processed_data.append(record)
                else:
                    rows_failed += 1
                    
            except Exception as e:
                logger.warning(f"⚠️ Erreur ligne {idx}: {e}")
                rows_failed += 1
        
        rows_processed = len(processed_data)
        logger.info(f"✅ Traité: {rows_processed} lignes OK, {rows_failed} échecs")
        
        # TODO: Insérer dans la base de données
        # cls._save_to_database(processed_data)
        
        return True, rows_processed, rows_failed, None, processed_data
        
    except Exception as e:
        error_msg = f"Erreur traitement: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return False, 0, 0, error_msg, []
```

#### 3. Ajouter le dispatcher dans `process_file()`

```python
def process_file(cls, file_path: str, file_type: str, metadata: dict):
    # ... code existant
    
    if file_type == FileType.NOUVEAU_TYPE:
        result = cls._process_nouveau_type(df, metadata)
    # ... autres types
```

#### 4. Mettre à jour l'interface

Ajouter l'option dans `fichiers.html` :
```html
<option value="nouveau_type">🆕 Nouveau Type</option>
```

---

## 📊 Exemple d'Utilisation

### Via l'Interface Web

1. Aller sur `/fichiers`
2. Cliquer sur "➕ Nouveau Fichier"
3. Remplir le formulaire :
   - Sélectionner le fichier Excel
   - Choisir le type (Budget, Dépenses, etc.)
   - Sélectionner le programme
   - Entrer la période
   - Donner un titre
4. Cliquer sur "📤 Télécharger et traiter"
5. Le traitement démarre automatiquement en arrière-plan
6. Actualisation automatique toutes les 10 secondes

### Via l'API

```python
import httpx

# Upload
with open('budget.xlsx', 'rb') as f:
    files = {'file': f}
    data = {
        'file_type': 'budget',
        'program': 'education',
        'period': '2024-01',
        'title': 'Budget Education Janvier 2024',
        'description': 'Budget mensuel'
    }
    response = httpx.post(
        'http://localhost:8000/api/v1/files/upload',
        files=files,
        data=data,
        cookies={'session_token': 'your_token'}
    )
    file_data = response.json()
    print(f"Fichier uploadé: ID={file_data['id']}")

# Vérifier le statut
status = httpx.get(
    f"http://localhost:8000/api/v1/files/{file_data['id']}/status"
).json()
print(f"Statut: {status['status']}")
print(f"Lignes traitées: {status['rows_processed']}")
```

---

## 🐛 Debugging

### Logs

Les logs sont enregistrés dans `logs/app.log` :
```
📊 Début du traitement du fichier: uploads/files/raw/budget_education_2024-01_20240115_143022.xlsx
📄 Fichier lu: 150 lignes, 5 colonnes
💰 Traitement d'un fichier BUDGET
✅ Budget traité: 148 lignes OK, 2 échecs
✅ Fichier 1 traité avec succès
```

### Vérification du Statut

```sql
-- Voir tous les fichiers
SELECT id, title, status, rows_processed, rows_failed FROM file;

-- Voir les erreurs
SELECT id, title, processing_error FROM file WHERE status = 'error';
```

---

## 🎯 Prochaines Étapes / TODO

1. **Tables de destination**
   - Créer des tables spécifiques pour chaque type de fichier
   - Exemple : `budget_data`, `depenses_data`, etc.
   - Insérer les données traitées dans ces tables

2. **Validation avancée**
   - Validation de la structure avant traitement
   - Détection automatique du type de fichier
   - Suggestions de mapping de colonnes

3. **Améliora tions**
   - Scanner antivirus intégré
   - Compression des fichiers archivés
   - Export des données traitées
   - Historique des modifications
   - Comparaison entre versions

4. **Notifications**
   - Email lors de la fin du traitement
   - Notifications en temps réel (WebSocket)
   - Alertes en cas d'erreur

---

## 📚 Documentation Associée

- [README.md](README.md) - Documentation principale
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Structure du projet
- [ARCHITECTURE_WORKFLOWS.md](ARCHITECTURE_WORKFLOWS.md) - Workflows détaillés
- API Swagger : http://localhost:8000/docs

---

**🎉 Le système est maintenant opérationnel !**

Vous pouvez uploader et traiter des fichiers Excel avec traçabilité complète.

