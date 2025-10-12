# 🚀 Quick Start - Système de Gestion de Fichiers

## ⚡ Installation (2 minutes)

### 1. Installer les dépendances

```bash
cd mppeep

# Option A : Avec uv (recommandé)
uv sync

# Option B : Avec pip
pip install -r requirements.txt
```

Les nouvelles dépendances ajoutées :
- `pandas>=2.0.0` - Pour traiter les fichiers Excel
- `openpyxl>=3.1.0` - Pour lire les fichiers .xlsx

### 2. Vérifier l'installation

```bash
# Test du système
python scripts/test_file_system.py
```

Vous devriez voir :
```
✅ Tous les tests sont passés!
🎉 Le système de gestion de fichiers est prêt!
```

### 3. Démarrer l'application

```bash
uvicorn app.main:app --reload
```

Les dossiers de fichiers seront **créés automatiquement** au démarrage !

---

## 🎯 Utilisation

### Via l'Interface Web

1. **Connexion** : http://localhost:8000
   - Email : `admin@mppeep.com`
   - Mot de passe : `admin123`

2. **Aller sur la page Fichiers** : http://localhost:8000/fichiers

3. **Upload d'un fichier** :
   - Cliquer sur "➕ Nouveau Fichier"
   - Remplir le formulaire :
     - Fichier Excel (.xlsx ou .xls)
     - Type : Budget, Dépenses, Revenus, etc.
     - Programme : Éducation, Santé, etc.
     - Période : 2024-01, Q1-2024, etc.
     - Titre : Description du fichier
   - Cliquer sur "📤 Télécharger et traiter"

4. **Suivre le traitement** :
   - Le statut s'affiche en temps réel
   - Actualisation automatique toutes les 10 secondes
   - Statuts possibles :
     - 🔵 Téléchargé
     - 🟡 En traitement
     - 🟢 Traité
     - 🔴 Erreur

---

## 📋 API Endpoints

Documentation interactive : http://localhost:8000/docs

### Principaux endpoints

```bash
# Upload d'un fichier
POST /api/v1/files/upload
Content-Type: multipart/form-data
{
  "file": <fichier.xlsx>,
  "file_type": "budget",
  "program": "education",
  "period": "2024-01",
  "title": "Budget Janvier 2024"
}

# Liste des fichiers
GET /api/v1/files/

# Détails d'un fichier
GET /api/v1/files/{id}

# Statut de traitement
GET /api/v1/files/{id}/status

# Retraiter un fichier
POST /api/v1/files/{id}/reprocess

# Supprimer un fichier
DELETE /api/v1/files/{id}

# Statistiques
GET /api/v1/files/statistics/overview
```

---

## 🔧 Personnalisation

### Ajouter un nouveau type de fichier

1. **Ajouter dans les énumérations** (`app/core/enums.py`)

```python
class FileType(str, Enum):
    # ... types existants
    MON_TYPE = "mon_type"
```

2. **Créer la méthode de traitement** (`app/services/excel_processor.py`)

```python
@classmethod
def _process_mon_type(cls, df: pd.DataFrame, metadata: dict):
    """Traitement spécifique pour MON_TYPE"""
    logger.info("🆕 Traitement d'un fichier MON_TYPE")
    
    processed_data = []
    
    for idx, row in df.iterrows():
        record = {
            'colonne1': row['Colonne1'],
            'colonne2': row['Colonne2'],
            # ...
        }
        processed_data.append(record)
    
    return True, len(processed_data), 0, None, processed_data
```

3. **Ajouter au dispatcher** (même fichier)

```python
def process_file(cls, file_path, file_type, metadata):
    # ...
    if file_type == FileType.MON_TYPE:
        result = cls._process_mon_type(df, metadata)
```

4. **Ajouter dans l'interface** (`app/templates/pages/fichiers.html`)

```html
<option value="mon_type">🆕 Mon Type</option>
```

---

## 📊 Structure des Fichiers Excel

### Budget (exemple)

| Ligne budgétaire | Montant prévu | Montant réalisé | Écart | Commentaire |
|------------------|---------------|-----------------|-------|-------------|
| Salaires         | 50000         | 48000           | 2000  | OK          |
| Fournitures      | 10000         | 12000           | -2000 | Dépassement |

### Dépenses (exemple)

| Date       | Bénéficiaire | Description | Catégorie | Montant | Mode paiement |
|------------|--------------|-------------|-----------|---------|---------------|
| 2024-01-15 | Fournisseur A| Achat PC    | Matériel  | 800     | Virement      |
| 2024-01-20 | Fournisseur B| Papeterie   | Fourniture| 120     | Espèces       |

### Personnalisation

Vous pouvez adapter la structure dans les méthodes `_process_*()` :

```python
# Exemple : adapter les colonnes
def _process_budget(cls, df, metadata):
    # Vérifier les colonnes
    if 'Budget' in df.columns:
        df.rename(columns={'Budget': 'Montant prévu'}, inplace=True)
    
    # ...
```

---

## 🐛 Dépannage

### Erreur : "Table file not found"

→ La table n'a pas été créée. Redémarrez l'application :

```bash
uvicorn app.main:app --reload
```

La table sera créée automatiquement au démarrage.

### Erreur : "Module pandas not found"

→ Installez les dépendances :

```bash
pip install pandas openpyxl
# ou
uv sync
```

### Erreur : "Permission denied" sur uploads/

→ Vérifiez les permissions du dossier :

```bash
chmod -R 755 uploads/
```

### Les fichiers ne se traitent pas

1. Vérifier les logs : `logs/app.log`
2. Vérifier le statut dans la DB :
   ```sql
   SELECT id, title, status, processing_error FROM file;
   ```
3. Retraiter manuellement :
   ```
   POST /api/v1/files/{id}/reprocess
   ```

---

## 📚 Documentation Complète

- [FILE_MANAGEMENT_SYSTEM.md](FILE_MANAGEMENT_SYSTEM.md) - Documentation complète
- [README.md](README.md) - Documentation principale du projet
- API Swagger : http://localhost:8000/docs

---

## ✅ Checklist de Démarrage

- [ ] Dépendances installées (`pandas`, `openpyxl`)
- [ ] Tests passés (`python scripts/test_file_system.py`)
- [ ] Application démarrée (`uvicorn app.main:app --reload`)
- [ ] Page Fichiers accessible (http://localhost:8000/fichiers)
- [ ] Premier fichier uploadé et traité avec succès

---

**🎉 Vous êtes prêt à gérer vos fichiers Excel !**

Besoin d'aide ? Consultez la [documentation complète](FILE_MANAGEMENT_SYSTEM.md).

