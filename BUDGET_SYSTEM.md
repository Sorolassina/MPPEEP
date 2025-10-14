# 💰 Système de Gestion Budgétaire

## 📋 Vue d'Ensemble

Système complet de **gestion budgétaire** et **conférences budgétaires** pour préparer, suivre et exécuter le budget annuel.

---

## 🎯 Composantes Principales

### **1. Suivi Budgétaire** 📊
Dashboard de suivi de l'exécution budgétaire en cours d'année :
- Budget voté
- Engagements
- Mandats visés
- Mandats PEC (Pris En Charge)
- Disponible
- Taux d'exécution

### **2. Conférences Budgétaires** 🤝
Gestion des conférences pour préparer le budget de l'année N+1 :
- **Conférences internes** : Avec les programmes pour définir leurs besoins
- **Conférences ministérielles** : Validation officielle au niveau ministère

### **3. Fiches Techniques** 📋
Documents structurés de demande budgétaire :
- Budget année précédente (N-1)
- Enveloppe demandée
- Compléments demandés
- Engagements de l'État
- Financements bailleurs de fonds
- Note justificative
- Pièces jointes

### **4. Import Excel** 📥
Chargement des activités et natures de dépenses depuis Excel

### **5. Export PDF** 📄
Impression des fiches techniques en PDF

---

## 🏗️ Modèles de Données

### **1. NatureDepense** (Référentiel)
```python
{
    "id": 1,
    "code": "BS",  # BS, P, I, T
    "libelle": "Biens et Services",
    "description": "Fournitures, entretien, services",
    "actif": true
}
```

**4 Natures de dépense** :
- **BS** : Biens et Services
- **P** : Personnel
- **I** : Investissement
- **T** : Transferts

### **2. Activite** (Référentiel - Import Excel)
```python
{
    "id": 1,
    "code": "ACT001",
    "libelle": "Maintenance informatique",
    "programme_id": 1,
    "direction_id": 2,
    "nature_depense_id": 1,  # BS
    "description": "Entretien parc informatique",
    "actif": true
}
```

### **3. FicheTechnique** (Document central)
```python
{
    "id": 1,
    "numero_fiche": "FT-2026-P01-001",
    "annee_budget": 2026,
    "programme_id": 1,
    "direction_id": 2,
    
    # Budget
    "budget_anterieur": 100000000,        # Budget 2025
    "enveloppe_demandee": 120000000,      # Base demandée
    "complement_demande": 15000000,        # Compléments
    "engagement_etat": 5000000,            # Projets garantis
    "financement_bailleurs": 10000000,     # Bailleurs
    "budget_total_demande": 150000000,     # TOTAL (auto)
    
    # Justification
    "note_justificative": "...",
    "observations": "...",
    
    # Statut
    "statut": "Brouillon",  # Brouillon, Soumis, Validé, Rejeté, Approuvé
    "phase": "Conférence interne",
    
    # Dates
    "date_creation": "2025-10-13",
    "date_soumission": null,
    "date_validation": null
}
```

### **4. LigneBudgetaire** (Détail des dépenses)
```python
{
    "id": 1,
    "fiche_technique_id": 1,
    "activite_id": 5,
    "nature_depense_id": 1,  # BS
    "libelle": "Achat ordinateurs",
    
    "budget_n_moins_1": 5000000,   # Budget 2025
    "budget_demande": 8000000,     # Demandé 2026
    "budget_valide": 7000000,      # Validé après conférence
    
    "justification": "Renouvellement parc informatique",
    "priorite": "Élevée",
    "ordre": 1
}
```

### **5. DocumentBudget** (Pièces jointes)
```python
{
    "id": 1,
    "fiche_technique_id": 1,
    "type_document": "Devis",
    "nom_fichier": "devis_ordinateurs_2026.pdf",
    "file_path": "/static/uploads/budget/fiches/1/devis_ordinateurs_2026.pdf",
    "taille_octets": 245678,
    "uploaded_by_user_id": 1,
    "uploaded_at": "2025-10-13 15:30:00"
}
```

### **6. ExecutionBudgetaire** (Suivi mensuel)
```python
{
    "id": 1,
    "annee": 2025,
    "mois": 6,
    "periode": "2025-06",
    
    "programme_id": 1,
    "direction_id": 2,
    "nature_depense_id": 1,
    
    "budget_vote": 123849000000,      # Budget voté
    "engagements": 55094000000,       # Engagements pris
    "mandats_vises": 54232000000,     # Mandats visés
    "mandats_pec": 50538000000,       # Mandats payés
    "disponible": 68756000000,        # Restant
    
    "taux_engagement": 44.48,         # %
    "taux_mandatement": 40.79,        # %
    "taux_execution": 40.79           # %
}
```

### **7. ConferenceBudgetaire** (Sessions)
```python
{
    "id": 1,
    "numero_conference": "CB-2026-INT-001",
    "type_conference": "Interne",
    "annee_budget": 2026,
    "programme_id": 1,
    "date_conference": "2025-11-15",
    "ordre_du_jour": "Révision budget P01",
    "compte_rendu": "...",
    "decisions": "...",
    "statut": "Terminée"
}
```

---

## 🛣️ Routes et Endpoints

### **Dashboard**
```
GET /api/v1/budget/                    # Dashboard suivi budgétaire
  ?annee=2025                          # Filtre année
  &programme_id=1                       # Filtre programme
```

### **Fiches Techniques**
```
GET  /api/v1/budget/fiches                  # Liste des fiches
GET  /api/v1/budget/fiches/nouveau          # Formulaire création
GET  /api/v1/budget/fiches/{id}             # Détail d'une fiche

POST /api/v1/budget/api/fiches              # Créer fiche
PUT  /api/v1/budget/api/fiches/{id}         # Modifier fiche
DELETE /api/v1/budget/api/fiches/{id}       # Supprimer fiche
```

### **Lignes Budgétaires**
```
POST   /api/v1/budget/api/fiches/{id}/lignes           # Ajouter ligne
PUT    /api/v1/budget/api/fiches/{id}/lignes/{lid}     # Modifier ligne
DELETE /api/v1/budget/api/fiches/{id}/lignes/{lid}     # Supprimer ligne
```

### **Documents**
```
POST /api/v1/budget/api/fiches/{id}/documents    # Upload document
```

### **Export**
```
GET /api/v1/budget/api/fiches/{id}/export/pdf   # Export PDF
```

### **Import**
```
POST /api/v1/budget/api/import/activites         # Import Excel activités
```

### **Conférences**
```
GET  /api/v1/budget/conferences                  # Liste des conférences
POST /api/v1/budget/api/conferences              # Créer conférence
```

---

## 📝 Workflow Complet

### **Phase 1 : Préparation (Octobre-Novembre)**

#### **Étape 1** : Créer les Fiches Techniques
```
1. Budget → Fiches Techniques → ➕ Nouvelle Fiche
2. Remplir:
   - Année budget: 2026
   - Programme: P01
   - Direction: DAF
   - Budget antérieur: 100 000 000 FCFA
   - Enveloppe demandée: 120 000 000 FCFA
   - Compléments: 15 000 000 FCFA
   - Engagements État: 5 000 000 FCFA
   - Bailleurs: 10 000 000 FCFA
   → TOTAL: 150 000 000 FCFA (calculé auto)
3. Note justificative: Texte explicatif
4. 💾 Enregistrer
```

**Résultat** :
- ✅ Fiche créée : FT-2026-P01-001
- ✅ Statut: Brouillon
- ✅ Phase: Conférence interne

---

#### **Étape 2** : Ajouter les Lignes de Dépenses
```
1. Ouvrir la fiche → ➕ Ajouter une Ligne
2. Remplir:
   - Nature: BS (Biens et Services)
   - Activité: Maintenance informatique
   - Libellé: Achat 10 ordinateurs HP
   - Budget N-1: 5 000 000 FCFA
   - Budget demandé: 8 000 000 FCFA
   - Priorité: Élevée
   - Justification: Renouvellement parc obsolète
3. 💾 Enregistrer
4. Répéter pour chaque ligne
```

**Résultat** :
- ✅ Ligne ajoutée au détail de la fiche
- ✅ Visible dans le tableau
- ✅ Total calculé automatiquement

---

#### **Étape 3** : Joindre les Documents
```
1. Dans la fiche → 📤 Upload
2. Sélectionner type: Devis
3. Choisir fichier: devis_ordinateurs.pdf
4. Upload
5. Répéter pour:
   - Factures proforma
   - Notes justificatives
   - Plans d'action
   - Rapports
```

**Résultat** :
- ✅ Documents stockés dans `/static/uploads/budget/fiches/{id}/`
- ✅ Taille et date enregistrées
- ✅ Téléchargeables depuis la fiche

---

### **Phase 2 : Conférences Internes (Novembre-Décembre)**

#### **Organiser une Conférence**
```
1. Budget → Conférences → ➕ Nouvelle Conférence
2. Remplir:
   - Type: Interne
   - Année: 2026
   - Programme: P01
   - Date: 2025-11-15
   - Ordre du jour: Révision budget P01
3. 💾 Créer
```

**Résultat** :
- ✅ Conférence créée : CB-2026-INT-001
- ✅ Statut: Planifiée

---

#### **Pendant la Conférence**
```
Actions possibles:
1. Consulter les fiches du programme
2. Examiner les pièces justificatives
3. Modifier les lignes budgétaires:
   - Augmenter/Diminuer montants
   - Ajouter nouvelles lignes
   - Supprimer lignes non prioritaires
4. Discuter et décider
5. Valider ou demander révisions
```

---

#### **Après la Conférence**
```
1. Mettre à jour les lignes:
   - budget_demande → budget_valide
2. Changer statut fiche: Brouillon → Validé
3. Ajouter compte-rendu et décisions
```

**Résultat** :
- ✅ Fiche validée en interne
- ✅ Historique complet des modifications
- ✅ Prête pour conférence ministérielle

---

### **Phase 3 : Import Excel des Activités**

#### **Préparer le Fichier Excel**
```
Colonnes requises:
- Code (obligatoire)
- Libelle (obligatoire)
- Programme (optionnel)
- Direction (optionnel)
- Nature (optionnel)
- Description (optionnel)

Exemple:
| Code    | Libelle                  | Programme | Direction | Nature | Description              |
|---------|--------------------------|-----------|-----------|--------|--------------------------|
| ACT001  | Maintenance informatique | P01       | DAF       | BS     | Entretien parc IT        |
| ACT002  | Formation personnel      | P01       | DRH       | P      | Formation continue       |
| ACT003  | Achat véhicules          | P02       | LOG       | I      | Renouvellement flotte    |
```

#### **Importer**
```
1. Fiches Techniques → 📥 Importer Activités Excel
2. Sélectionner fichier .xlsx
3. Cliquer "📥 Importer"
4. Voir résultat:
   - X activité(s) créée(s)
   - Y activité(s) mise(s) à jour
   - Erreurs éventuelles
```

**Résultat** :
- ✅ Activités en base de données
- ✅ Disponibles dans les selects
- ✅ Liées aux programmes/directions/natures

---

### **Phase 4 : Export PDF de la Fiche**

#### **Générer le PDF**
```
1. Ouvrir une fiche technique
2. Cliquer "📄 Exporter en PDF"
3. Nouvelle fenêtre s'ouvre
4. Impression automatique (Ctrl+P)
5. Enregistrer en PDF ou imprimer papier
```

**Contenu du PDF** :
```
═══════════════════════════════════════════════════
     FICHE TECHNIQUE BUDGÉTAIRE
     FT-2026-P01-001
     Budget 2026
     Programme: Administration Générale
═══════════════════════════════════════════════════

RÉCAPITULATIF BUDGÉTAIRE (FCFA)
┌─────────────────────────────────┬─────────────────┐
│ Budget Année Précédente (2025)  │ 100 000 000     │
│ Enveloppe Demandée              │ 120 000 000     │
│ Compléments Demandés            │  15 000 000     │
│ Engagements de l'État           │   5 000 000     │
│ Financement Bailleurs de Fonds  │  10 000 000     │
├─────────────────────────────────┼─────────────────┤
│ BUDGET TOTAL DEMANDÉ            │ 150 000 000     │
└─────────────────────────────────┴─────────────────┘

DÉTAIL DES DÉPENSES
┌────────┬──────────────────────┬──────────┬──────────┬─────────┐
│ Nature │ Libellé              │ Budget   │ Demandé  │ Priorité│
│        │                      │ N-1      │          │         │
├────────┼──────────────────────┼──────────┼──────────┼─────────┤
│ BS     │ Achat ordinateurs    │ 5 000 000│ 8 000 000│ Élevée  │
│ P      │ Formation agents     │ 2 000 000│ 3 000 000│ Normale │
│ I      │ Rénovation bureaux   │10 000 000│12 000 000│ Critique│
└────────┴──────────────────────┴──────────┴──────────┴─────────┘

NOTE JUSTIFICATIVE
Le budget demandé vise à moderniser nos infrastructures et
renforcer les capacités du personnel...

Date d'édition: 13/10/2025
Statut: Brouillon
```

---

## 📊 Dashboard Budgétaire

### **KPIs Principaux**

#### **1. Budget Voté (BV)**
```
Montant: 123 849 millions FCFA
Pourcentage: 100%
```

#### **2. Engagements (Eng)**
```
Montant: 55 094 millions FCFA
Taux: 44,48%
Interprétation: 44% du budget est déjà engagé
```

#### **3. Mandats Visés (MV)**
```
Montant: 54 232 millions FCFA
Taux: 107,31%  (des engagements)
```

#### **4. Mandats PEC (MP)**
```
Montant: 50 538 millions FCFA
Taux: 92,41%  (des mandats visés)
Interprétation: 92% des mandats sont payés
```

#### **5. Disponible (Dis)**
```
Montant: 68 756 millions FCFA
Taux: 55,52%
Interprétation: 55% du budget reste disponible
```

---

### **Variation N vs N-1**

Graphique en barres montrant l'évolution :
- **Taux Engagement** : -50% (diminution)
- **Taux MV** : +7% (augmentation)
- **Taux M.PEC** : -7% (diminution)
- **Taux E.G** : +50% (augmentation)

---

### **Exécution par Programme**

Barres horizontales de progression :
```
AG (Administration Générale)    ████████░░ 57,39%
GEPN (Gestion Personnel)        ███████░░░ 55,77%
PE (Politique Économique)       ██████░░░░ 48,05%
```

---

### **Nature de Dépenses**

Vue latérale (right rail) :
```
┌─────────────────────────────────┐
│ BS  Biens & Services            │
│     Budget: 26 223 M            │
│                      64,32%     │
├─────────────────────────────────┤
│ P   Personnel                   │
│     Budget: 15 471 M            │
│                      76,19%     │
├─────────────────────────────────┤
│ I   Investissement              │
│     Budget: 25 794 M            │
│                      35,23%     │
├─────────────────────────────────┤
│ T   Transferts                  │
│     Budget: 56 361 M            │
│                      55,03%     │
└─────────────────────────────────┘
```

---

## 🔄 Cycle Budgétaire

```
Octobre - Novembre : Préparation
    ↓
    │ - Créer fiches techniques
    │ - Remplir demandes
    │ - Joindre documents
    ↓
Novembre - Décembre : Conférences Internes
    ↓
    │ - Organiser conférences par programme
    │ - Examiner les demandes
    │ - Discuter et arbitrer
    │ - Modifier les montants
    │ - Valider les fiches
    ↓
Janvier : Consolidation
    ↓
    │ - Consolider toutes les fiches
    │ - Préparer projet de budget ministère
    ↓
Février - Mars : Conférences Ministérielles
    ↓
    │ - Présenter au ministère
    │ - Défendre les demandes
    │ - Négocier
    │ - Validation finale
    ↓
Avril - Mai : Vote Budget
    ↓
    │ - Loi de finances
    │ - Budget officiellement voté
    ↓
Janvier - Décembre (Année N) : Exécution
    ↓
    │ - Suivi mensuel
    │ - Dashboard mis à jour
    │ - Reporting
```

---

## 📥 Format Excel pour Import Activités

### **Colonnes du Fichier**

| Colonne     | Type   | Obligatoire | Exemple                    | Description                    |
|-------------|--------|-------------|----------------------------|--------------------------------|
| Code        | Texte  | ✅ Oui      | ACT001                     | Code unique de l'activité      |
| Libelle     | Texte  | ✅ Oui      | Maintenance informatique   | Description de l'activité      |
| Programme   | Texte  | ❌ Non      | P01                        | Code du programme              |
| Direction   | Texte  | ❌ Non      | DAF                        | Code de la direction           |
| Nature      | Texte  | ❌ Non      | BS                         | Code nature de dépense         |
| Description | Texte  | ❌ Non      | Entretien parc IT          | Description détaillée          |

### **Exemple de Fichier Excel**
```
Feuille 1: Activités

A        | B                        | C    | D   | E  | F
---------|--------------------------|------|-----|----|-----------------------
Code     | Libelle                  | Prog | Dir | Nat| Description
ACT001   | Maintenance informatique | P01  | DAF | BS | Entretien parc IT
ACT002   | Formation personnel      | P01  | DRH | P  | Formation continue
ACT003   | Achat véhicules          | P02  | LOG | I  | Renouvellement flotte
ACT004   | Subventions écoles       | P03  | EDU | T  | Transferts enseignement
```

### **Comment Importer**
```
1. Préparer le fichier Excel (selon format ci-dessus)
2. Budget → Fiches Techniques → 📥 Importer Activités Excel
3. Sélectionner le fichier
4. Cliquer "📥 Importer"
5. Voir le résultat:
   ✅ 4 activités créées
   ✅ 0 activités mises à jour
   ❌ 0 erreurs
```

---

## 🎨 Interface Utilisateur

### **Dashboard** (Reproduction exacte du fichier HTML)
- Sidebar avec filtres (Période, Programme)
- KPIs avec neumorphism
- Variation N vs N-1 (barres)
- Exécution par programme (barres horizontales)
- Nature de dépenses (right rail)

### **Liste Fiches**
- Tableau avec filtres
- Actions (Voir, PDF, Supprimer)
- Bouton "➕ Nouvelle Fiche"
- Bouton "📥 Importer Activités"

### **Détail Fiche**
- Récapitulatif budgétaire (grandes cartes)
- Tableau des lignes budgétaires
- Liste des documents
- Actions (Modifier, Export PDF, Imprimer)

---

## 🔒 Sécurité et Traçabilité

### **Authentification**
- ✅ Toutes les pages nécessitent une connexion
- ✅ `current_user` vérifié

### **Traçabilité Complète**
```python
# Création
fiche.created_by_user_id = current_user.id

# Modification
historique = HistoriqueBudget(
    fiche_technique_id=fiche_id,
    action="Modification",
    ancien_statut="Brouillon",
    nouveau_statut="Validé",
    montant_avant=100000000,
    montant_apres=120000000,
    commentaire="Augmentation après conférence",
    user_id=current_user.id,
    date_action=datetime.now()
)

# Logs
logger.info(f"✅ Fiche {numero} créée par {current_user.email}")
logger.info(f"📄 Document {filename} uploadé pour fiche {id}")
logger.info(f"📥 Import: {created} créées, {updated} mises à jour")
```

---

## 📊 Calculs Automatiques

### **Budget Total de la Fiche**
```python
budget_total_demande = (
    enveloppe_demandee +
    complement_demande +
    engagement_etat +
    financement_bailleurs
)
```

### **Taux d'Exécution**
```python
taux_engagement = (engagements / budget_vote) * 100
taux_mandatement = (mandats_pec / budget_vote) * 100
taux_execution = taux_mandatement  # Simplification
disponible = budget_vote - engagements
```

### **Total Lignes Budgétaires**
```python
total_demande = sum(ligne.budget_demande for ligne in lignes)
total_valide = sum(ligne.budget_valide for ligne in lignes)
```

---

## 📈 Reporting et Analyses

### **Par Programme**
```sql
SELECT programme_id, 
       SUM(budget_vote) as budget_total,
       SUM(mandats_pec) as montant_execute,
       (SUM(mandats_pec) / SUM(budget_vote) * 100) as taux_execution
FROM execution_budgetaire
WHERE annee = 2025
GROUP BY programme_id
ORDER BY taux_execution DESC
```

### **Par Nature de Dépense**
```sql
SELECT nature_depense_id,
       SUM(budget_vote) as budget_total,
       SUM(engagements) as engagements_total,
       (SUM(engagements) / SUM(budget_vote) * 100) as taux_engagement
FROM execution_budgetaire
WHERE annee = 2025
GROUP BY nature_depense_id
```

### **Évolution Temporelle**
```sql
SELECT periode,
       SUM(budget_vote) as budget,
       SUM(mandats_pec) as execute,
       (SUM(mandats_pec) / SUM(budget_vote) * 100) as taux
FROM execution_budgetaire
WHERE annee = 2025
GROUP BY periode
ORDER BY periode
```

---

## 🚀 Quick Start

### **1. Créer Première Fiche**
```
Budget → Fiches Techniques → ➕ Nouvelle Fiche
→ Remplir les montants
→ Enregistrer
→ ✅ Fiche créée !
```

### **2. Ajouter Détails**
```
Fiche → ➕ Ajouter une Ligne
→ Remplir nature, libellé, montant
→ Enregistrer
→ ✅ Ligne ajoutée !
```

### **3. Joindre Documents**
```
Fiche → 📤 Upload
→ Sélectionner type et fichier
→ Upload
→ ✅ Document uploadé !
```

### **4. Exporter PDF**
```
Fiche → 📄 Exporter en PDF
→ Nouvelle fenêtre
→ Ctrl+P pour imprimer/enregistrer
→ ✅ PDF généré !
```

---

## 📁 Fichiers Créés

```
app/models/budget.py                         # 8 modèles (270 lignes)
app/api/v1/endpoints/budget.py               # Endpoints (450 lignes)
app/templates/pages/budget_dashboard.html    # Dashboard (550 lignes)
app/templates/pages/budget_fiches.html       # Liste fiches (390 lignes)
app/templates/pages/budget_fiche_form.html   # Formulaire (380 lignes)
app/templates/pages/budget_fiche_detail.html # Détail fiche (480 lignes)
app/templates/components/navbar.html         # Bouton connecté
app/models/__init__.py                       # Imports ajoutés
app/api/v1/router.py                         # Router budget
BUDGET_SYSTEM.md                             # Ce fichier
```

---

## 🎯 Fonctionnalités Clés

### **✅ Implémenté**
- [x] Modèles de données (8 tables)
- [x] Dashboard de suivi budgétaire
- [x] Création de fiches techniques
- [x] Ajout/Modification/Suppression de lignes
- [x] Upload de documents multiples
- [x] Import Excel activités
- [x] Export PDF de fiche
- [x] Historique des modifications
- [x] Conférences budgétaires
- [x] Bouton navbar connecté
- [x] 4 natures de dépense initialisées

### **🔜 À Venir** (si nécessaire)
- [ ] Graphiques d'évolution (Chart.js)
- [ ] Export Excel consolidé
- [ ] Notifications de changement de statut
- [ ] Workflow de validation (étapes)
- [ ] Comparaison N vs N-1 détaillée
- [ ] API pour intégration externe

---

**💰 Système de Gestion Budgétaire Production-Ready !**

Dashboard ✅ | Fiches Techniques ✅ | Import Excel ✅ | Export PDF ✅ | Conférences ✅

