# 💰 Système de Gestion Budgétaire - Documentation Complète

## 📋 Vue d'Ensemble

Système complet de **gestion budgétaire** intégrant le suivi d'exécution SIGOBE (Système d'Information de Gestion et d'Observation Budgétaire) et les fiches techniques pour le MPPEEP (Ministère du Plan, de la Prospérité Économique et de l'Emploi Public).

**Version :** 2.0  
**Dernière mise à jour :** Octobre 2025  
**Statut :** Production

---

## 🎯 Composantes Principales

### **1. Dashboard Budgétaire** 📊
Tableau de bord principal avec suivi en temps réel :
- **URL :** `/api/v1/budget/`
- **KPIs** : Budget Actuel, Budget Voté, Engagements, Mandats, Disponible, Taux d'exécution
- **Filtres** : Année, Trimestre, Programme, Nature de dépense
- **Visualisations** : Exécution par programme, Nature de dépenses, Variation N vs N-1

### **2. SIGOBE (Système d'Information de Gestion et d'Observation Budgétaire)** 📈
Gestion des imports de données d'exécution budgétaire :
- **URL :** `/api/v1/budget/sigobe`
- **Import Excel** : Fichiers d'exécution budgétaire
- **Calcul KPIs** : Automatique par programme, nature, dimension globale
- **Historique** : Conservation de tous les chargements
- **Filtres** : Année, Trimestre

### **3. Fiches Techniques Budgétaires** 📋
Documents structurés pour la préparation budgétaire :
- **URL :** `/api/v1/budget/fiches`
- **Création** : Formulaire complet avec hiérarchie Programme → Direction
- **Détails** : Lignes budgétaires avec activités et natures
- **Documents** : Upload de pièces justificatives
- **Export** : PDF pour impression et archivage

---

## 🏗️ Architecture de la Base de Données

### **1. Modèles SIGOBE (Exécution Budgétaire)**

#### **SigobeChargement**
Table historique des imports de fichiers SIGOBE.

```python
{
    "id": 1,
    "annee": 2025,
    "trimestre": 1,  # 1, 2, 3, 4 ou null pour annuel
    "periode_libelle": "T1 2025",
    
    # Métadonnées fichier
    "nom_fichier": "Situation execution.xlsx",
    "taille_octets": 2456789,
    "chemin_fichier": "uploads/sigobe/2025_T1_20251014_213506.xlsx",
    
    # Résumé import
    "nb_lignes_importees": 388,
    "nb_programmes": 3,
    "nb_actions": 15,
    
    # Statut
    "statut": "Terminé",  # En cours, Terminé, Erreur
    "message_erreur": null,
    
    # Traçabilité
    "uploaded_by_user_id": 1,
    "date_chargement": "2025-10-14 21:29:43"
}
```

**Relations :**
- `uploaded_by_user` → User
- `executions` → List[SigobeExecution]
- `kpis` → List[SigobeKpi]

---

#### **SigobeExecution**
Lignes détaillées de l'exécution budgétaire.

```python
{
    "id": 1,
    "chargement_id": 1,
    "annee": 2025,
    "trimestre": 1,
    "periode": "2025-01-31",  # Date de la période
    
    # Classification SIGOBE
    "section": "DEPENSES",
    "categorie": "PERSONNEL",
    "type_credit": "AE",  # Autorisation d'Engagement
    
    # Hiérarchie budgétaire
    "programmes": "Administration Générale",
    "actions": "Coordination et animation du ministère",
    "rprog": "DRH",  # Responsable Programme
    "type_depense": "Biens et services",
    "activites": "Maintenance informatique",
    "taches": "Achat ordinateurs",
    
    # Montants (en FCFA)
    "budget_vote": 123849000000,
    "budget_actuel": 123849000000,
    "engagements_emis": 55094000000,
    "disponible_eng": 68756000000,
    "mandats_emis": 54232000000,
    "mandats_vise_cf": 50538000000,
    "mandats_pec": 50538000000,
    
    # Métadonnées
    "created_at": "2025-10-14 21:29:43"
}
```

**Index :**
- `idx_chargement` sur `chargement_id`
- `idx_programmes` sur `programmes`
- `idx_type_depense` sur `type_depense`

**Notes :**
- Un fichier SIGOBE peut contenir plusieurs centaines de lignes
- Chaque ligne représente un détail d'exécution
- Les montants sont en FCFA (Francs CFA)

---

#### **SigobeKpi**
KPIs agrégés calculés automatiquement après import.

```python
{
    "id": 1,
    "annee": 2025,
    "trimestre": 1,
    "chargement_id": 1,
    
    # Dimension
    "dimension": "global",  # global, programme, nature
    "dimension_code": null,  # Code si dimension = programme ou nature
    "dimension_libelle": null,
    
    # Agrégats (en FCFA)
    "budget_vote_total": 123849000000,
    "budget_actuel_total": 123849000000,
    "engagements_total": 55094000000,
    "mandats_total": 50538000000,
    
    # Taux (en %)
    "taux_engagement": 44.48,
    "taux_mandatement": 91.73,
    "taux_execution": 40.79,
    
    # Métadonnées
    "date_calcul": "2025-10-14 21:30:15"
}
```

**Dimensions :**
- **global** : KPI pour tout le chargement
- **programme** : KPI par programme (ex: "Administration Générale")
- **nature** : KPI par nature de dépense (ex: "Biens et services")

**Calculs :**
```python
# Taux d'engagement
taux_engagement = (engagements_total / budget_actuel_total) * 100

# Taux de mandatement
taux_mandatement = (mandats_total / engagements_total) * 100

# Taux d'exécution
taux_execution = (mandats_total / budget_actuel_total) * 100
```

---

### **2. Modèles Fiches Techniques**

#### **FicheTechnique**
Document central de demande budgétaire.

```python
{
    "id": 1,
    "numero_fiche": "FT-2026-P01-001",
    "annee_budget": 2026,
    
    # Hiérarchie
    "programme_id": 1,
    "direction_id": 2,
    
    # Montants budgétaires (en FCFA)
    "budget_anterieur": 100000000,        # Budget N-1
    "enveloppe_demandee": 120000000,      # Base demandée
    "complement_demande": 15000000,       # Compléments
    "engagement_etat": 5000000,           # Engagements
    "financement_bailleurs": 10000000,    # Bailleurs
    "budget_total_demande": 150000000,    # Calculé auto
    
    # Justification
    "note_justificative": "Modernisation des infrastructures...",
    "observations": "Priorité élevée",
    
    # Workflow
    "statut": "Brouillon",  # Brouillon, Soumis, Validé, Rejeté, Approuvé
    "phase": "Préparation",
    
    # Dates
    "date_creation": "2025-10-13",
    "date_soumission": null,
    "date_validation": null,
    
    # Traçabilité
    "created_by_user_id": 1,
    "created_at": "2025-10-13 10:30:00",
    "updated_at": "2025-10-13 15:45:00",
    "actif": true
}
```

**Calcul automatique :**
```python
budget_total_demande = (
    enveloppe_demandee +
    complement_demande +
    engagement_etat +
    financement_bailleurs
)
```

**Numérotation :**
Format : `FT-{annee}-P{programme}-{sequence}`
- `FT` = Fiche Technique
- `2026` = Année budget
- `P01` = Programme 01
- `001` = Numéro séquentiel

---

#### **LigneBudgetaire**
Détail des dépenses par ligne.

```python
{
    "id": 1,
    "fiche_technique_id": 1,
    
    # Classification
    "nature_depense_id": 1,  # BS, P, I, T
    "activite_id": 5,
    
    "libelle": "Achat de 10 ordinateurs HP",
    
    # Montants (en FCFA)
    "budget_n_moins_1": 5000000,      # Budget N-1
    "budget_demande": 8000000,        # Demandé N
    "budget_valide": 7000000,         # Validé après révision
    
    # Métadonnées
    "justification": "Renouvellement parc obsolète",
    "priorite": "Élevée",  # Basse, Normale, Élevée, Critique
    "ordre": 1,
    
    # Traçabilité
    "actif": true,
    "created_at": "2025-10-13 10:45:00"
}
```

**Relations :**
- `fiche_technique` → FicheTechnique
- `nature_depense` → NatureDepense
- `activite` → Activite

---

#### **NatureDepense** (Référentiel)
Classification des dépenses.

```python
{
    "id": 1,
    "code": "BS",
    "libelle": "Biens et Services",
    "description": "Fournitures, entretien, services, consommables",
    "actif": true
}
```

**4 Natures :**
| Code | Libellé              | Description                              |
|------|---------------------|------------------------------------------|
| BS   | Biens et Services   | Fournitures, entretien, services         |
| P    | Personnel           | Salaires, primes, charges sociales       |
| I    | Investissement      | Équipements, constructions, immobilisations |
| T    | Transferts          | Subventions, bourses, aides              |

---

#### **Activite** (Référentiel)
Activités budgétaires.

```python
{
    "id": 1,
    "code": "ACT001",
    "libelle": "Maintenance informatique",
    
    # Hiérarchie
    "programme_id": 1,
    "direction_id": 2,
    "nature_depense_id": 1,  # BS
    
    "description": "Entretien et maintenance du parc informatique",
    "actif": true
}
```

**Import Excel :**
- Format : Code, Libellé, Programme, Direction, Nature, Description
- Mise à jour automatique si code existe
- Création si nouveau code

---

#### **DocumentBudget**
Pièces jointes aux fiches.

```python
{
    "id": 1,
    "fiche_technique_id": 1,
    
    # Document
    "type_document": "Devis",  # Devis, Facture, Note, Rapport, Autre
    "nom_fichier": "devis_ordinateurs_2026.pdf",
    "file_path": "uploads/budget/fiches/1/devis_ordinateurs_2026.pdf",
    "taille_octets": 245678,
    
    # Traçabilité
    "uploaded_by_user_id": 1,
    "uploaded_at": "2025-10-13 15:30:00",
    "actif": true
}
```

**Stockage :**
- Dossier : `uploads/budget/fiches/{fiche_id}/`
- Nom unique : `{timestamp}_{original_filename}`

---

#### **HistoriqueBudget**
Traçabilité des modifications.

```python
{
    "id": 1,
    "fiche_technique_id": 1,
    
    # Action
    "action": "Modification",  # Création, Modification, Suppression, Validation
    "ancien_statut": "Brouillon",
    "nouveau_statut": "Validé",
    
    # Montants
    "montant_avant": 100000000,
    "montant_apres": 120000000,
    
    "commentaire": "Augmentation après révision",
    
    # Traçabilité
    "user_id": 1,
    "date_action": "2025-10-13 16:00:00"
}
```

---

### **3. Modèles Personnel (Référentiels)**

#### **Programme**
Programmes budgétaires.

```python
{
    "id": 1,
    "code": "P01",
    "libelle": "Administration Générale",
    "description": "Coordination et administration centrale",
    "actif": true
}
```

#### **Direction**
Directions rattachées aux programmes.

```python
{
    "id": 1,
    "code": "DAF",
    "libelle": "Direction des Affaires Financières",
    "programme_id": 1,
    "actif": true
}
```

---

## 🛣️ Routes et Endpoints API

### **Dashboard Budgétaire**

```
GET /api/v1/budget/
```

**Paramètres :**
- `annee` (int, optionnel) : Année à afficher (défaut : dernière année disponible)
- `trimestre` (int, optionnel) : Trimestre (1, 2, 3, 4)
- `programme_id` (int, optionnel) : Filtre par programme
- `nature` (str, optionnel) : Filtre par nature (BS, P, I, T)

**Réponse :**
- Template HTML avec KPIs, graphiques, filtres

**Exemple :**
```
/api/v1/budget/?annee=2025&trimestre=1&programme_id=1
```

---

### **SIGOBE**

#### Liste des chargements
```
GET /api/v1/budget/sigobe
```

**Paramètres :**
- `annee` (int, optionnel) : Filtre par année
- `trimestre` (int, optionnel) : Filtre par trimestre

**Réponse :**
- Template HTML avec liste des chargements et formulaire d'upload

---

#### Upload fichier SIGOBE
```
POST /api/v1/budget/api/sigobe/upload
```

**Body (multipart/form-data) :**
```python
{
    "fichier": UploadFile,  # Fichier Excel
    "annee": 2025,
    "trimestre": 1  # Optionnel
}
```

**Processus :**
1. Lecture du fichier Excel (pandas)
2. Nettoyage des données (colonnes, lignes vides)
3. Extraction des métadonnées (Section, Catégorie, Type_credit)
4. Parsing des montants (Budget_Vote, Engagements, Mandats...)
5. Création des lignes SigobeExecution
6. Calcul des KPIs (global, par programme, par nature)
7. Sauvegarde en base

**Réponse :**
```json
{
    "ok": true,
    "message": "Chargement terminé",
    "chargement_id": 1,
    "nb_lignes": 388,
    "nb_programmes": 3,
    "nb_actions": 15
}
```

**Erreurs possibles :**
- Fichier invalide
- Format Excel incorrect
- Colonnes manquantes
- Erreur de parsing

---

#### Supprimer chargement
```
DELETE /api/v1/budget/api/sigobe/{chargement_id}
```

**Réponse :**
```json
{
    "ok": true,
    "message": "Chargement supprimé"
}
```

**Cascade :**
- Supprime toutes les lignes SigobeExecution
- Supprime tous les KPIs SigobeKpi
- Supprime le fichier physique

---

#### Récupérer KPIs
```
GET /api/v1/budget/api/sigobe/{chargement_id}/kpis
```

**Paramètres :**
- `dimension` (str, optionnel) : global, programme, nature

**Réponse :**
```json
{
    "ok": true,
    "kpis": [
        {
            "dimension": "global",
            "budget_actuel_total": 48808856296,
            "engagements_total": 18272066882,
            "mandats_total": 17929446968,
            "taux_engagement": 37.44,
            "taux_mandatement": 98.13,
            "taux_execution": 36.73
        }
    ]
}
```

---

### **Fiches Techniques**

#### Liste hiérarchique
```
GET /api/v1/budget/fiches
```

**Paramètres :**
- `annee` (int, optionnel) : Année budget

**Réponse :**
- Template HTML avec arborescence Programme → Direction → Fiches

---

#### Formulaire nouvelle fiche
```
GET /api/v1/budget/fiches/nouveau
```

**Réponse :**
- Template HTML avec formulaire

---

#### Détail d'une fiche
```
GET /api/v1/budget/fiches/{fiche_id}
```

**Réponse :**
- Template HTML avec récapitulatif, lignes, documents, historique

---

#### Structure d'une fiche (édition avancée)
```
GET /api/v1/budget/fiches/{fiche_id}/structure
```

**Réponse :**
- Template HTML avec gestion des lignes et documents

---

#### Créer fiche
```
POST /api/v1/budget/api/fiches
```

**Body (form-data) :**
```python
{
    "annee_budget": 2026,
    "programme_id": 1,
    "direction_id": 2,
    "budget_anterieur": 100000000,
    "enveloppe_demandee": 120000000,
    "complement_demande": 15000000,
    "engagement_etat": 5000000,
    "financement_bailleurs": 10000000,
    "note_justificative": "...",
    "observations": "..."
}
```

**Réponse :**
```json
{
    "ok": true,
    "fiche_id": 1,
    "numero_fiche": "FT-2026-P01-001"
}
```

---

#### Modifier fiche
```
PUT /api/v1/budget/api/fiches/{fiche_id}
```

**Body :** Identique à création

**Réponse :**
```json
{
    "ok": true,
    "message": "Fiche mise à jour"
}
```

---

#### Supprimer fiche
```
DELETE /api/v1/budget/api/fiches/{fiche_id}
```

**Réponse :**
```json
{
    "ok": true,
    "message": "Fiche supprimée"
}
```

**Cascade :**
- Supprime toutes les lignes budgétaires
- Supprime tous les documents (fichiers + DB)
- Supprime l'historique

---

#### Ajouter ligne budgétaire
```
POST /api/v1/budget/api/fiches/{fiche_id}/lignes
```

**Body (JSON) :**
```json
{
    "nature_depense_id": 1,
    "activite_id": 5,
    "libelle": "Achat ordinateurs",
    "budget_n_moins_1": 5000000,
    "budget_demande": 8000000,
    "justification": "Renouvellement parc",
    "priorite": "Élevée"
}
```

**Réponse :**
```json
{
    "ok": true,
    "ligne_id": 1
}
```

---

#### Modifier ligne
```
PUT /api/v1/budget/api/fiches/{fiche_id}/lignes/{ligne_id}
```

---

#### Supprimer ligne
```
DELETE /api/v1/budget/api/fiches/{fiche_id}/lignes/{ligne_id}
```

---

#### Upload document
```
POST /api/v1/budget/api/fiches/{fiche_id}/documents
```

**Body (multipart/form-data) :**
```python
{
    "fichier": UploadFile,
    "type_document": "Devis"  # Devis, Facture, Note, Rapport, Autre
}
```

**Réponse :**
```json
{
    "ok": true,
    "document_id": 1,
    "nom_fichier": "devis_ordinateurs.pdf"
}
```

---

#### Supprimer document
```
DELETE /api/v1/budget/api/fiches/{fiche_id}/documents/{document_id}
```

---

#### Export PDF
```
GET /api/v1/budget/api/fiches/{fiche_id}/export/pdf
```

**Réponse :**
- Template HTML optimisé pour impression (print CSS)
- Auto-ouverture de Ctrl+P

---

### **Import/Export**

#### Import activités Excel
```
POST /api/v1/budget/api/import/activites
```

**Body (multipart/form-data) :**
```python
{
    "fichier": UploadFile  # Excel avec colonnes: Code, Libelle, Programme, Direction, Nature, Description
}
```

**Réponse :**
```json
{
    "ok": true,
    "nb_created": 15,
    "nb_updated": 3,
    "errors": []
}
```

---

## 📊 Calculs et Formules

### **KPIs Dashboard**

#### Budget Actuel Total
```python
budget_actuel_total = sum(e.budget_actuel for e in executions)
```

#### Taux d'Engagement
```python
budg_select = budget_actuel_total or budget_vote_total
taux_engagement = (engagements_total / budg_select * 100) if budg_select > 0 else 0
```

**Formule DAX équivalente :**
```dax
_Tx_Eng = DIVIDE([Engagements], [Budget_Actuel])
```

#### Taux de Mandatement Visé
```python
taux_mandatement_vise = (mandats_vises_total / mandats_pec_total * 100) if mandats_pec_total > 0 else 0
```

**Formule DAX :**
```dax
_Tx_Mandat_Vise = DIVIDE([Mandats_Vise], [Mandats_PEC])
```

#### Taux de Mandatement PEC
```python
taux_mandatement_pec = (mandats_pec_total / mandats_emis_total * 100) if mandats_emis_total > 0 else 0
```

**Formule DAX :**
```dax
_Tx_Mandat_PEC = DIVIDE([Mandats_PEC], [Mandats_Emis])
```

#### Taux d'Exécution Global
```python
taux_execution_global = (disponible_eng_total / budg_select * 100) if budg_select > 0 else 0
```

**Formule DAX :**
```dax
_Tx_Exe.Global = DIVIDE([Disponible], [Budget_Actuel])
```

---

### **Variation N vs N-1**

Pour comparer une année N avec l'année N-1 :

```python
# Récupérer les KPIs de N et N-1
kpi_n = get_kpi(annee=2025, trimestre=1, dimension="global")
kpi_n1 = get_kpi(annee=2024, trimestre=1, dimension="global")

# Calculer les variations (en points de pourcentage)
variation_engagement = kpi_n.taux_engagement - kpi_n1.taux_engagement
variation_mandatement = kpi_n.taux_mandatement - kpi_n1.taux_mandatement
variation_execution = kpi_n.taux_execution - kpi_n1.taux_execution
```

**Affichage :**
- Positif : Vert, flèche ↑, "+X%"
- Négatif : Rouge, flèche ↓, "-X%"
- Nul : Gris, "0.0%"

---

### **Exécution par Programme**

```python
kpis_programmes = get_kpis(chargement_id, dimension="programme")

for kpi in kpis_programmes:
    code = kpi.dimension_code or kpi.dimension_libelle
    exec_par_programme[code] = {
        "libelle": kpi.dimension_libelle,
        "budget": float(kpi.budget_actuel_total),
        "engagements": float(kpi.engagements_total),
        "mandats": float(kpi.mandats_total),
        "taux": float(kpi.taux_execution)
    }
```

**Affichage :**
- Barre de progression horizontale
- Pourcentage d'exécution
- Couleur selon taux (vert > 80%, jaune 50-80%, rouge < 50%)

---

## 🔄 Workflow Import SIGOBE

### **Étape 1 : Upload Fichier**

1. Utilisateur accède à `/api/v1/budget/sigobe`
2. Clique sur "📤 Charger des données"
3. Modal s'ouvre avec formulaire :
   - Année (obligatoire)
   - Trimestre (optionnel)
   - Fichier Excel (obligatoire)
4. Upload du fichier

---

### **Étape 2 : Parsing Excel (Power Query Logic)**

Le système suit scrupuleusement la logique Power Query :

#### **A. Charger et Nettoyer**
```python
# 1. Charger Excel (première feuille)
Source = pd.ExcelFile(fichier)
Raw = pd.read_excel(Source, sheet_name=0, header=None)

# 2. Identifier les colonnes à garder (celles contenant "_Budget" ou "_Engagements" etc.)
ColsToKeep = [col for col in Raw.columns if any(kw in str(Raw.iloc[0, col]) for kw in KEYWORDS)]

# 3. Filtrer colonnes
Filtered = Raw[ColsToKeep]

# 4. Promouvoir première ligne en en-têtes
Filtered.columns = Filtered.iloc[0]
Result = Filtered[1:].reset_index(drop=True)

# 5. Supprimer lignes vides
Result = Result.dropna(how='all')
```

#### **B. Extraire Métadonnées**
```python
# Chercher les lignes contenant "Section:", "Categorie:", "Type_credit:"
Metadatafile = {}
for col in Result.columns:
    for idx, val in Result[col].items():
        if "Section:" in str(val):
            Metadatafile['section'] = val.replace("Section:", "").strip()
        if "Categorie:" in str(val):
            Metadatafile['categorie'] = val.replace("Categorie:", "").strip()
        if "Type_credit:" in str(val):
            Metadatafile['type_credit'] = val.replace("Type_credit:", "").strip()

# Supprimer les lignes de métadonnées
Result = Result[~Result.apply(lambda row: any("Section:" in str(v) or "Categorie:" in str(v) for v in row), axis=1)]
```

#### **C. Extraire les Montants**
```python
# Fonction pour parser un montant
def parse_montant(val):
    if pd.isna(val) or val == '':
        return 0.0
    try:
        # Nettoyer : enlever espaces, remplacer virgule par point
        clean = str(val).replace(' ', '').replace(',', '.')
        # Enlever symboles monétaires
        clean = re.sub(r'[^\d.-]', '', clean)
        return float(clean)
    except:
        return 0.0

# Pour chaque ligne, extraire les montants
for _, row in Result.iterrows():
    montants = {
        'budget_vote': parse_montant(row.get('Budget_Vote', 0)),
        'budget_actuel': parse_montant(row.get('Budget_Actuel', 0)),
        'engagements_emis': parse_montant(row.get('Engagements_Emis', 0)),
        'disponible_eng': parse_montant(row.get('Disponible_Eng', 0)),
        'mandats_emis': parse_montant(row.get('Mandats_Emis', 0)),
        'mandats_vise_cf': parse_montant(row.get('Mandats_Vise_CF', 0)),
        'mandats_pec': parse_montant(row.get('Mandats_PEC', 0))
    }
```

---

### **Étape 3 : Sauvegarde en Base**

```python
# 1. Créer SigobeChargement
chargement = SigobeChargement(
    annee=annee,
    trimestre=trimestre,
    periode_libelle=f"T{trimestre} {annee}" if trimestre else f"Annuel {annee}",
    nom_fichier=fichier.filename,
    taille_octets=len(fichier_bytes),
    chemin_fichier=save_path,
    nb_lignes_importees=0,
    nb_programmes=0,
    nb_actions=0,
    statut="En cours",
    uploaded_by_user_id=current_user.id
)
session.add(chargement)
session.commit()

# 2. Créer les SigobeExecution
nb_lignes = 0
programmes_set = set()
actions_set = set()

for _, row in Result.iterrows():
    execution = SigobeExecution(
        chargement_id=chargement.id,
        annee=annee,
        trimestre=trimestre,
        section=Metadatafile.get('section'),
        categorie=Metadatafile.get('categorie'),
        type_credit=Metadatafile.get('type_credit'),
        programmes=row.get('Programmes'),
        actions=row.get('Actions'),
        rprog=row.get('Rprog'),
        type_depense=row.get('Type_depense'),
        activites=row.get('Activites'),
        taches=row.get('Taches'),
        budget_vote=montants['budget_vote'],
        budget_actuel=montants['budget_actuel'],
        engagements_emis=montants['engagements_emis'],
        disponible_eng=montants['disponible_eng'],
        mandats_emis=montants['mandats_emis'],
        mandats_vise_cf=montants['mandats_vise_cf'],
        mandats_pec=montants['mandats_pec']
    )
    session.add(execution)
    nb_lignes += 1
    
    if row.get('Programmes'):
        programmes_set.add(row.get('Programmes'))
    if row.get('Actions'):
        actions_set.add(row.get('Actions'))

# 3. Mettre à jour le chargement
chargement.nb_lignes_importees = nb_lignes
chargement.nb_programmes = len(programmes_set)
chargement.nb_actions = len(actions_set)
chargement.statut = "Terminé"
session.commit()
```

---

### **Étape 4 : Calcul des KPIs**

```python
def calcul_kpis_sigobe(chargement_id, session):
    # Récupérer toutes les exécutions
    executions = session.exec(
        select(SigobeExecution).where(SigobeExecution.chargement_id == chargement_id)
    ).all()
    
    # 1. KPI Global
    global_budget_vote = sum(e.budget_vote or 0 for e in executions)
    global_budget_actuel = sum(e.budget_actuel or 0 for e in executions)
    global_engagements = sum(e.engagements_emis or 0 for e in executions)
    global_mandats = sum(e.mandats_emis or 0 for e in executions)
    
    taux_engagement = (global_engagements / global_budget_actuel * 100) if global_budget_actuel > 0 else 0
    taux_mandatement = (global_mandats / global_engagements * 100) if global_engagements > 0 else 0
    taux_execution = (global_mandats / global_budget_actuel * 100) if global_budget_actuel > 0 else 0
    
    kpi_global = SigobeKpi(
        annee=chargement.annee,
        trimestre=chargement.trimestre,
        dimension="global",
        budget_vote_total=global_budget_vote,
        budget_actuel_total=global_budget_actuel,
        engagements_total=global_engagements,
        mandats_total=global_mandats,
        taux_engagement=taux_engagement,
        taux_mandatement=taux_mandatement,
        taux_execution=taux_execution,
        chargement_id=chargement_id
    )
    session.add(kpi_global)
    
    # 2. KPIs par Programme
    programmes_dict = defaultdict(lambda: {'budget_vote': 0, 'budget_actuel': 0, 'engagements': 0, 'mandats': 0})
    
    for e in executions:
        if e.programmes:
            programmes_dict[e.programmes]['budget_vote'] += e.budget_vote or 0
            programmes_dict[e.programmes]['budget_actuel'] += e.budget_actuel or 0
            programmes_dict[e.programmes]['engagements'] += e.engagements_emis or 0
            programmes_dict[e.programmes]['mandats'] += e.mandats_emis or 0
    
    for prog, data in programmes_dict.items():
        taux_eng = (data['engagements'] / data['budget_actuel'] * 100) if data['budget_actuel'] > 0 else 0
        taux_mand = (data['mandats'] / data['engagements'] * 100) if data['engagements'] > 0 else 0
        taux_exec = (data['mandats'] / data['budget_actuel'] * 100) if data['budget_actuel'] > 0 else 0
        
        code, libelle = split_code_libelle(prog)  # Sépare "P01 - Administration Générale"
        
        kpi_prog = SigobeKpi(
            annee=chargement.annee,
            trimestre=chargement.trimestre,
            dimension="programme",
            dimension_code=code,
            dimension_libelle=libelle,
            budget_vote_total=data['budget_vote'],
            budget_actuel_total=data['budget_actuel'],
            engagements_total=data['engagements'],
            mandats_total=data['mandats'],
            taux_engagement=taux_eng,
            taux_mandatement=taux_mand,
            taux_execution=taux_exec,
            chargement_id=chargement_id
        )
        session.add(kpi_prog)
    
    # 3. KPIs par Nature
    natures_dict = defaultdict(lambda: {'budget_vote': 0, 'budget_actuel': 0, 'engagements': 0, 'mandats': 0})
    
    for e in executions:
        if e.type_depense:
            natures_dict[e.type_depense]['budget_vote'] += e.budget_vote or 0
            natures_dict[e.type_depense]['budget_actuel'] += e.budget_actuel or 0
            natures_dict[e.type_depense]['engagements'] += e.engagements_emis or 0
            natures_dict[e.type_depense]['mandats'] += e.mandats_emis or 0
    
    for nature, data in natures_dict.items():
        taux_eng = (data['engagements'] / data['budget_actuel'] * 100) if data['budget_actuel'] > 0 else 0
        taux_mand = (data['mandats'] / data['engagements'] * 100) if data['engagements'] > 0 else 0
        taux_exec = (data['mandats'] / data['budget_actuel'] * 100) if data['budget_actuel'] > 0 else 0
        
        code_nature, libelle_nature = split_code_libelle(nature)
        
        # Si pas de code, utiliser abréviations
        if not code_nature or code_nature == libelle_nature:
            nature_lower = nature.lower()
            if 'bien' in nature_lower or 'service' in nature_lower:
                code_nature = 'BS'
            elif 'personnel' in nature_lower:
                code_nature = 'P'
            elif 'investissement' in nature_lower:
                code_nature = 'I'
            elif 'transfert' in nature_lower:
                code_nature = 'T'
            else:
                code_nature = nature[:3].upper()
            libelle_nature = nature
        
        kpi_nature = SigobeKpi(
            annee=chargement.annee,
            trimestre=chargement.trimestre,
            dimension="nature",
            dimension_code=code_nature,
            dimension_libelle=libelle_nature,
            budget_vote_total=data['budget_vote'],
            budget_actuel_total=data['budget_actuel'],
            engagements_total=data['engagements'],
            mandats_total=data['mandats'],
            taux_engagement=taux_eng,
            taux_mandatement=taux_mand,
            taux_execution=taux_exec,
            chargement_id=chargement_id
        )
        session.add(kpi_nature)
    
    session.commit()
    logger.info(f"✅ KPIs calculés : 1 global + {len(programmes_dict)} programmes + {len(natures_dict)} natures")
```

---

## 🎨 Interface Utilisateur

### **Dashboard Budgétaire** (`/api/v1/budget/`)

**Sections :**

#### 1. En-tête
- Profil utilisateur (photo, nom, rôle)
- Titre : "💰 Suivi Budgétaire {année} [- Trimestre {trimestre}]"
- Boutons actions :
  - "📋 Fiches Techniques"
  - "📊 SIGOBE"
  - "← Retour"

#### 2. Filtres
- **Année** : Dropdown avec années disponibles
- **Trimestre** : Dropdown (Annuel, T1, T2, T3, T4)
- **Programme** : Dropdown (Tous, P01, P02...)
- **Nature** : Dropdown (Toutes, BS, P, I, T)

**Comportement :**
- Changement de filtre → Rechargement page avec paramètres
- Overlay de chargement avec message

#### 3. KPIs (6 cartes)
```
┌────────────────────┬────────────────────┬────────────────────┐
│ Budget Actuel      │ Budget Voté        │ Engagements        │
│ 48.8 Mds FCFA      │ 48.8 Mds FCFA      │ 18.3 Mds FCFA      │
│ 100%               │ 100%               │ 37.44%             │
└────────────────────┴────────────────────┴────────────────────┘

┌────────────────────┬────────────────────┬────────────────────┐
│ Disponible Eng.    │ Mandats Visés      │ Mandats PEC        │
│ 30.5 Mds FCFA      │ 17.9 Mds FCFA      │ 17.9 Mds FCFA      │
│ 62.56%             │ 98.13%             │ 100%               │
└────────────────────┴────────────────────┴────────────────────┘
```

**Styles :**
- Gradients violets
- Box-shadow
- Animation au hover
- Compteur animé (CountUp.js)

#### 4. Exécution par Programme
```
Administration Générale           ████████░░ 34.38%
Portefeuille de l'Etat           ████████████ 47.95%
Gestion des EPN                  ██████░░░░ 23.43%
```

**Styles :**
- Barres horizontales animées
- Couleur selon taux (vert/jaune/rouge)
- Initiales du programme (cercle coloré)

#### 5. Nature de Dépenses
```
BS  Biens & Services       26.2 Mds   64%
P   Personnel              15.5 Mds   76%
I   Investissement          25.8 Mds   35%
T   Transferts             56.4 Mds   55%
```

#### 6. Variation N vs N-1
```
Taux Eng.    │▁▁▁ +2.5%    (N-1: 35.0%)
Taux MV      │▆▆▆ +15.3%   (N-1: 82.8%)
Taux PEC     │▅▅▅ +10.0%   (N-1: 90.0%)
Taux Global  │▃▃▃ +5.7%    (N-1: 31.0%)
```

**Styles :**
- Barres verticales colorées (vert = positif, rouge = négatif)
- Valeur N-1 en gris
- Légende explicative

---

### **SIGOBE** (`/api/v1/budget/sigobe`)

**Sections :**

#### 1. En-tête
- Titre : "📊 SIGOBE"
- Sous-titre : "Système d'Information de Gestion et d'Observation Budgétaire"
- Bouton "← Retour"

#### 2. Filtres
- **Année** : Dropdown
- **Trimestre** : Dropdown

#### 3. Chargements (Table)
```
┌─────────────┬────────────┬──────────────┬─────────┬──────────┬──────────┐
│ Période     │ Fichier    │ Lignes       │ Montants│ Statut   │ Actions  │
├─────────────┼────────────┼──────────────┼─────────┼──────────┼──────────┤
│ T1 2025     │ Situa...   │ 388 lignes   │ 48.8 M  │ Terminé  │ 👁️ 🗑️   │
│ 14/10/2025  │            │ 3 prog       │         │          │          │
└─────────────┴────────────┴──────────────┴─────────┴──────────┴──────────┘
```

#### 4. Bouton "📤 Charger des données"
- Ouvre modal avec formulaire
- Upload fichier Excel
- Sélection année/trimestre

**Modal Upload :**
```
┌───────────────────────────────────────────┐
│   📤 Charger des Données SIGOBE           │
├───────────────────────────────────────────┤
│   Année* : [2025 ▼]                       │
│   Trimestre : [T1 ▼]                      │
│   Fichier* : [Choisir fichier...]         │
│                                            │
│   [Annuler]          [📥 Charger]         │
└───────────────────────────────────────────┘
```

---

### **Fiches Techniques** (`/api/v1/budget/fiches`)

**Vue Hiérarchique :**
```
📁 Programme P01 - Administration Générale
  │
  ├─ 📂 Direction DAF - Affaires Financières
  │   ├─ FT-2026-P01-001  (150 M FCFA)  [Brouillon]  👁️ ✏️ 📄 🗑️
  │   └─ FT-2026-P01-002  (85 M FCFA)   [Validé]     👁️ ✏️ 📄 🗑️
  │
  └─ 📂 Direction DRH - Ressources Humaines
      └─ FT-2026-P01-003  (120 M FCFA)  [Soumis]     👁️ ✏️ 📄 🗑️
```

**Actions :**
- **➕ Nouvelle Fiche** : Ouvre formulaire
- **📥 Importer Activités** : Upload Excel

---

### **Détail Fiche** (`/api/v1/budget/fiches/{id}`)

**Sections :**

#### 1. Récapitulatif
```
┌────────────────────────────────────────────────────┐
│ FT-2026-P01-001                                    │
│ Budget 2026 - Administration Générale              │
│ Direction: DAF                                     │
│ Statut: Brouillon                                  │
├────────────────────────────────────────────────────┤
│ Budget Antérieur (2025)       100 000 000 FCFA    │
│ Enveloppe Demandée            120 000 000 FCFA    │
│ Compléments Demandés           15 000 000 FCFA    │
│ Engagements État                5 000 000 FCFA    │
│ Financement Bailleurs          10 000 000 FCFA    │
├────────────────────────────────────────────────────┤
│ BUDGET TOTAL DEMANDÉ          150 000 000 FCFA    │
└────────────────────────────────────────────────────┘
```

#### 2. Lignes Budgétaires (Table)
```
┌────────┬────────────────┬──────────┬──────────┬──────────┬─────────┬──────┐
│ Nature │ Activité       │ Libellé  │ Budget   │ Demandé  │ Priorité│ Act. │
│        │                │          │ N-1      │          │         │      │
├────────┼────────────────┼──────────┼──────────┼──────────┼─────────┼──────┤
│ BS     │ Maintenance IT │ Ordina...│ 5 M      │ 8 M      │ Élevée  │ ✏️ 🗑️│
│ P      │ Formation      │ Forma... │ 2 M      │ 3 M      │ Normale │ ✏️ 🗑️│
│ I      │ Rénovation     │ Rénov... │ 10 M     │ 12 M     │ Critique│ ✏️ 🗑️│
└────────┴────────────────┴──────────┴──────────┴──────────┴─────────┴──────┘

TOTAL: 23 M FCFA
```

#### 3. Documents (Liste)
```
📄 devis_ordinateurs_2026.pdf     (245 KB)  [Télécharger] [🗑️]
📄 facture_proforma.pdf            (189 KB)  [Télécharger] [🗑️]
```

#### 4. Actions
- **✏️ Modifier** : Ouvre formulaire édition
- **📄 Exporter PDF** : Génère PDF
- **🗑️ Supprimer** : Avec confirmation

---

## 🔒 Sécurité et Bonnes Pratiques

### **Authentification**
```python
@router.get("/")
def budget_home(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    # current_user est automatiquement vérifié
    # Si non connecté, redirection vers /login
```

### **Autorisation**
```python
# Vérifier que l'utilisateur peut supprimer
if fiche.created_by_user_id != current_user.id and current_user.user_type != UserType.ADMIN:
    raise HTTPException(403, "Non autorisé")
```

### **Validation des Entrées**
```python
# Vérifier l'année
if annee < 2020 or annee > 2050:
    raise HTTPException(400, "Année invalide")

# Vérifier le trimestre
if trimestre and trimestre not in [1, 2, 3, 4]:
    raise HTTPException(400, "Trimestre invalide")
```

### **Gestion des Fichiers**
```python
# Limiter la taille
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

if fichier.size > MAX_FILE_SIZE:
    raise HTTPException(400, "Fichier trop volumineux")

# Vérifier l'extension
ALLOWED_EXTENSIONS = ['.xlsx', '.xls', '.pdf', '.doc', '.docx']
ext = Path(fichier.filename).suffix.lower()

if ext not in ALLOWED_EXTENSIONS:
    raise HTTPException(400, "Type de fichier non autorisé")

# Nettoyer le nom de fichier
safe_filename = secure_filename(fichier.filename)

# Générer nom unique
unique_filename = f"{timestamp}_{safe_filename}"
```

### **Soft Delete**
```python
# Ne jamais supprimer physiquement en production
fiche.actif = False
fiche.deleted_at = datetime.now()
fiche.deleted_by_user_id = current_user.id
session.commit()
```

### **Traçabilité**
```python
# Logger toutes les actions importantes
logger.info(f"✅ Fiche {numero} créée par {current_user.email}")
logger.info(f"📄 Document {filename} uploadé pour fiche {id}")
logger.info(f"🗑️ Fiche {id} supprimée par {current_user.email}")

# Historique en base
historique = HistoriqueBudget(
    fiche_technique_id=fiche_id,
    action="Modification",
    ancien_statut="Brouillon",
    nouveau_statut="Validé",
    user_id=current_user.id,
    date_action=datetime.now()
)
session.add(historique)
```

### **Gestion des Erreurs**
```python
try:
    # Code métier
    result = process_data()
    session.commit()
    return {"ok": True, "data": result}
    
except ValueError as e:
    logger.error(f"❌ Erreur de validation: {e}")
    raise HTTPException(400, f"Données invalides: {str(e)}")
    
except Exception as e:
    logger.error(f"❌ Erreur serveur: {e}")
    session.rollback()
    raise HTTPException(500, f"Erreur interne: {str(e)}")
```

---

## 🚀 Maintenance et Évolution

### **Ajout d'un Nouveau KPI**

1. Ajouter le champ dans `SigobeKpi` :
```python
class SigobeKpi(SQLModel, table=True):
    # ... champs existants
    taux_disponible: Optional[float] = None  # Nouveau KPI
```

2. Mettre à jour le calcul :
```python
def calcul_kpis_sigobe(chargement_id, session):
    # ... calculs existants
    taux_disponible = (disponible / budget_actuel * 100) if budget_actuel > 0 else 0
    
    kpi_global.taux_disponible = taux_disponible
```

3. Ajouter dans le template :
```html
<div class="kpi-card">
  <div class="kpi-label">💰 Disponible</div>
  <div class="kpi-value">{{ "{:,.0f}".format(disponible_eng_total) }}</div>
  <div class="kpi-percentage">{{ taux_disponible }}%</div>
</div>
```

---

### **Ajout d'un Nouveau Filtre**

1. Ajouter le paramètre dans l'endpoint :
```python
@router.get("/")
def budget_home(
    annee: Optional[int] = None,
    trimestre: Optional[int] = None,
    direction_id: Optional[int] = None,  # Nouveau filtre
    ...
):
    # Appliquer le filtre
    if direction_id:
        query = query.where(SigobeExecution.direction_id == direction_id)
```

2. Ajouter dans le template :
```html
<div class="filter-group">
  <label>🏢 Direction</label>
  <select name="direction_id" onchange="filtrerDashboard()">
    <option value="">Toutes</option>
    {% for dir in directions %}
    <option value="{{ dir.id }}">{{ dir.libelle }}</option>
    {% endfor %}
  </select>
</div>
```

3. Mettre à jour le JavaScript :
```javascript
function filtrerDashboard() {
  const direction = document.getElementById('filter-direction').value;
  if (direction) url += `&direction_id=${direction}`;
}
```

---

### **Migration Base de Données**

Pour ajouter une colonne :

```python
# scripts/migrate_add_taux_disponible.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "app.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Ajouter colonne
        cursor.execute("""
            ALTER TABLE sigobe_kpi 
            ADD COLUMN taux_disponible REAL
        """)
        
        conn.commit()
        print("✅ Migration réussie")
        
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("⚠️ Colonne existe déjà")
        else:
            raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
```

Exécuter :
```bash
python scripts/migrate_add_taux_disponible.py
```

---

### **Tests et Validation**

#### Test d'Import SIGOBE
```python
import pytest
from app.api.v1.endpoints.budget import _parse_sigobe_file

def test_parse_sigobe_file():
    with open("tests/fixtures/sigobe_test.xlsx", "rb") as f:
        result, metadata, cols = _parse_sigobe_file(f, 2025, 1)
    
    assert len(result) > 0
    assert 'section' in metadata
    assert 'Budget_Vote' in result.columns
```

#### Test de Calcul KPI
```python
def test_calcul_taux_engagement():
    budget = 100000000
    engagements = 45000000
    
    taux = (engagements / budget * 100)
    
    assert taux == 45.0
```

---

### **Performance**

#### Indexation
```python
# Créer des index pour les requêtes fréquentes
CREATE INDEX idx_sigobe_exec_chargement ON sigobe_execution(chargement_id);
CREATE INDEX idx_sigobe_exec_programmes ON sigobe_execution(programmes);
CREATE INDEX idx_sigobe_kpi_dimension ON sigobe_kpi(dimension);
```

#### Pagination
```python
@router.get("/api/executions")
def list_executions(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    query = select(SigobeExecution).offset(skip).limit(limit)
    executions = session.exec(query).all()
    return {"items": executions, "skip": skip, "limit": limit}
```

#### Cache
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_kpis_cached(chargement_id: int, dimension: str):
    # Mise en cache des KPIs
    return get_kpis(chargement_id, dimension)
```

---

## 📁 Structure des Fichiers

```
mppeep/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   └── budget.py                    # 3707 lignes
│   │       └── router.py
│   ├── models/
│   │   └── budget.py                            # 450 lignes
│   ├── templates/
│   │   └── pages/
│   │       ├── budget_dashboard.html            # 1303 lignes
│   │       ├── budget_sigobe.html               # 737 lignes
│   │       ├── budget_fiches_hierarchique.html  # ~400 lignes
│   │       ├── budget_fiche_form.html           # ~380 lignes
│   │       ├── budget_fiche_detail.html         # ~480 lignes
│   │       └── budget_fiche_structure.html      # ~350 lignes
│   └── static/
│       └── images/
│           └── navbar/
│               └── budget.png
├── uploads/
│   ├── budget/
│   │   └── fiches/
│   │       └── {fiche_id}/
│   │           └── {document}
│   └── sigobe/
│       └── {annee}_T{trimestre}_{timestamp}.xlsx
├── scripts/
│   └── (scripts de migration si nécessaire)
└── BUDGET_SYSTEM.md                             # Ce fichier

Total: ~7000 lignes de code + templates
```

---

## 🎯 Checklist de Production

### **Avant Déploiement**

- [ ] Base de données sauvegardée
- [ ] Migrations testées en staging
- [ ] Import SIGOBE testé avec fichiers réels
- [ ] KPIs validés avec comptabilité
- [ ] Exports PDF vérifiés
- [ ] Permissions utilisateurs configurées
- [ ] Logs configurés correctement
- [ ] Stockage fichiers sécurisé
- [ ] Limites de taille fichiers définies
- [ ] Backup automatique configuré

### **Après Déploiement**

- [ ] Import d'un fichier SIGOBE de test
- [ ] Vérification KPIs dashboard
- [ ] Création d'une fiche technique test
- [ ] Export PDF test
- [ ] Test suppression/restauration
- [ ] Vérification logs
- [ ] Test performance (temps de réponse)
- [ ] Formation utilisateurs

---

## 📞 Support et Contact

**Maintenance :**
- Documentation : `BUDGET_SYSTEM.md`
- Logs : `logs/app.log`, `logs/error.log`
- Base de données : `app.db` (SQLite)

**Développeur :**
- Code backend : `app/api/v1/endpoints/budget.py`
- Modèles : `app/models/budget.py`
- Templates : `app/templates/pages/budget_*.html`

---

**💰 Système de Gestion Budgétaire - Production Ready**

Dashboard ✅ | SIGOBE ✅ | Fiches Techniques ✅ | Export PDF ✅ | Traçabilité Complète ✅

---

**Version :** 2.0  
**Dernière mise à jour :** Octobre 2025  
**Statut :** ✅ Production
