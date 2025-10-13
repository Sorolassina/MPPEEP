# 📊 Système de Gestion des Besoins en Agents

## 📋 Vue d'Ensemble

Système complet pour **exprimer**, **suivre** et **consolider** les besoins en agents à tous les niveaux de l'organisation.

---

## 🎯 Objectif

Gérer le cycle complet des besoins en personnel :
1. 📝 **Expression** : Les services expriment leurs besoins
2. 📊 **Consolidation** : Agrégation au niveau Direction puis Programme
3. 📤 **Transmission** : Envoi au Ministère de la Fonction Publique
4. 📥 **Suivi** : Tracking des agents obtenus
5. 📈 **Évaluation** : Calcul du taux de satisfaction

---

## 🏗️ Structure Hiérarchique

```
Service (exprime besoin)
    ↓
    │ Ex: Service Comptabilité demande 2 Secrétaires
    ↓
Direction (consolidation niveau 1)
    ↓
    │ Ex: DAF consolide tous ses services
    │     → 10 agents demandés au total
    ↓
Programme (consolidation niveau 2)
    ↓
    │ Ex: P01 consolide toutes ses directions
    │     → 25 agents demandés au total
    ↓
Ministère (niveau global)
    ↓
    │ Consolide tous les programmes
    │ → Transmission au Ministère de la Fonction Publique
    ↓
Ministère de la Fonction Publique
    ↓
    │ Examine les besoins
    │ → Fournit les agents (partiellement ou totalement)
    ↓
Suivi & Évaluation
    │
    │ On fait le point:
    │ - Demandé: 25
    │ - Obtenu: 18
    │ - Taux: 72%
```

---

## 📊 Modèles de Données

### **1. BesoinAgent** (Table principale)
```python
{
    "id": 1,
    "annee": 2025,
    "periode": "Trimestre 1",
    
    # Hiérarchie
    "service_id": 5,         # Service Comptabilité
    "direction_id": 2,       # DAF
    "programme_id": 1,       # P01
    
    # Besoin
    "poste_libelle": "Secrétaire de Direction",
    "grade_id": 7,           # B3
    "categorie_souhaitee": "B",
    
    # Quantité
    "nombre_demande": 2,
    "nombre_obtenu": 1,      # Mis à jour après réponse ministère
    
    # Justification
    "motif": "Surcharge de travail...",
    "urgence": "Normale",    # Faible, Normale, Élevée, Critique
    
    # Statut
    "statut": "Transmis",    # Exprimé, Transmis, En attente, Partiellement satisfait, Satisfait, Rejeté
    
    # Dates
    "date_expression": "2025-01-15",
    "date_transmission": "2025-02-01",
    "date_satisfaction": null,
    
    # Metadata
    "exprime_par_user_id": 3,
    "valide_par_user_id": 1
}
```

### **2. SuiviBesoin** (Historique)
```python
{
    "id": 1,
    "besoin_id": 1,
    
    "ancien_statut": "Exprimé",
    "nouveau_statut": "Transmis",
    
    "nombre_obtenu_avant": 0,
    "nombre_obtenu_apres": 1,
    
    "modifie_par_user_id": 1,
    "commentaire": "Transmis au ministère le 01/02/2025",
    "date_modification": "2025-02-01 10:00:00"
}
```

### **3. ConsolidationBesoin** (Vue agrégée)
```python
{
    "id": 1,
    "annee": 2025,
    "niveau": "Direction",   # Service, Direction, Programme, Ministère
    "direction_id": 2,       # DAF
    
    # Agrégats
    "total_demande": 10,
    "total_obtenu": 7,
    "taux_satisfaction": 70.0,  # %
    
    # Par catégorie
    "demande_cat_a": 2, "obtenu_cat_a": 1,
    "demande_cat_b": 4, "obtenu_cat_b": 3,
    "demande_cat_c": 3, "obtenu_cat_c": 2,
    "demande_cat_d": 1, "obtenu_cat_d": 1,
    
    "statut": "Transmis"     # En cours, Transmis, Clôturé
}
```

---

## 🛣️ Endpoints API

### **Besoins**
```
GET    /api/v1/besoins/                     # Page principale
GET    /api/v1/besoins/nouveau              # Formulaire création
GET    /api/v1/besoins/consolidation        # Vue consolidée

GET    /api/v1/besoins/api/besoins          # Liste avec filtres (?annee=2025&statut=...)
POST   /api/v1/besoins/api/besoins          # Créer besoin
PUT    /api/v1/besoins/api/besoins/{id}     # Mettre à jour (nombre obtenu, statut)
DELETE /api/v1/besoins/api/besoins/{id}     # Désactiver

GET    /api/v1/besoins/api/statistiques     # Stats globales
```

### **Consolidation**
```
POST   /api/v1/besoins/api/consolidation/generer      # Générer consolidation
GET    /api/v1/besoins/api/consolidation/{id}/export  # Exporter données
```

---

## 📝 Workflow Complet

### **Étape 1 : Expression du Besoin (Service)**

**Qui** : Chef de service ou responsable

**Action** :
1. Accéder : `RH → Suivi des besoins agents → ➕ Exprimer un Besoin`
2. Remplir :
   - Année et période
   - Service concerné
   - Intitulé du poste (ex: "Secrétaire")
   - Grade ou catégorie souhaité
   - Nombre d'agents
   - Urgence
   - Motif détaillé
3. Soumettre

**Résultat** :
- ✅ Besoin créé avec statut "Exprimé"
- ✅ Visible dans le tableau des besoins
- ✅ Suivi créé automatiquement

---

### **Étape 2 : Consolidation (Direction)**

**Qui** : Directeur ou DRH

**Action** :
1. Accéder : `Besoins → 📋 Vue Consolidée`
2. Générer consolidation :
   - Année : 2025
   - Niveau : Par Direction
   - Direction : DAF
3. Cliquer "📊 Générer"

**Résultat** :
- ✅ Consolidation créée
- ✅ Calculs automatiques :
  - Total demandé (somme de tous les services)
  - Par catégorie (A, B, C, D)
  - Taux de satisfaction initial (0%)
- ✅ Prête pour transmission

---

### **Étape 3 : Consolidation Globale (Programme)**

**Qui** : Responsable Programme ou DG

**Action** :
1. Vue Consolidée
2. Générer :
   - Niveau : Par Programme
   - Programme : P01
3. Générer

**Résultat** :
- ✅ Consolidation programme
- ✅ Agrège toutes les directions
- ✅ Vue d'ensemble pour le ministère

---

### **Étape 4 : Transmission au Ministère**

**Qui** : DRH ou DG

**Action** :
1. Liste des besoins
2. Pour chaque besoin → 📝 Mettre à jour
3. Changer statut : "Transmis"
4. Saisir date de transmission
5. Enregistrer

**Résultat** :
- ✅ Statut passe à "Transmis"
- ✅ Date de transmission enregistrée
- ✅ Badge cyan dans le tableau
- ✅ En attente de réponse du ministère

---

### **Étape 5 : Réponse du Ministère**

**Qui** : DRH (après réponse officielle)

**Scénario A - Totalement satisfait** :
```
Action :
- 📝 Mettre à jour
- Nombre obtenu : 2 (sur 2 demandés)
- Statut auto : "Satisfait" ✅
- Enregistrer

Résultat :
- Badge vert "Satisfait"
- Barre de progression : 100%
- Date satisfaction enregistrée
```

**Scénario B - Partiellement satisfait** :
```
Action :
- 📝 Mettre à jour
- Nombre obtenu : 1 (sur 2 demandés)
- Statut auto : "Partiellement satisfait" ⚠️
- Observations : "1 seul agent disponible"
- Enregistrer

Résultat :
- Badge orange "Partiellement satisfait"
- Barre de progression : 50%
```

**Scénario C - Rejeté** :
```
Action :
- 📝 Mettre à jour
- Nombre obtenu : 0
- Statut : "Rejeté" ❌
- Observations : "Budget insuffisant"
- Enregistrer

Résultat :
- Badge rouge "Rejeté"
- Barre de progression : 0%
```

---

### **Étape 6 : Évaluation et Reporting**

**Qui** : DRH, Direction, DG

**Actions** :
1. Consulter les statistiques (page principale)
   - Total besoins
   - Total demandé
   - Total obtenu
   - **Taux de satisfaction global**

2. Vue consolidée
   - Par direction
   - Par programme
   - Par catégorie
   - Export des données

3. Analyse
   - Identifier les déficits
   - Préparer les besoins pour l'année suivante

---

## 📊 Interface Utilisateur

### **Page Principale** (`/api/v1/besoins/`)

#### **KPIs (4 cartes)** :
```
┌───────────────┬───────────────┬───────────────┬───────────────┐
│ Total Besoins │ Agents        │ Agents        │ Taux          │
│      25       │ Demandés: 50  │ Obtenus: 35   │ Satisfaction  │
│               │               │               │     70%       │
└───────────────┴───────────────┴───────────────┴───────────────┘
```

#### **Filtres** :
- Année (2025, 2024, 2023)
- Statut (Tous, Exprimé, Transmis, Satisfait, etc.)

#### **Tableau des Besoins** :
| Service | Poste | Grade | Demandé | Obtenu | Satisfaction | Urgence | Statut | Actions |
|---------|-------|-------|---------|--------|--------------|---------|--------|---------|
| SCPT | Secrétaire | B3 | 2 | 1 | [====] 50% | Normale | Partiellement | 👁️📝🗑️ |

#### **Actions** :
- ➕ **Exprimer un Besoin** : Nouveau besoin
- 📋 **Vue Consolidée** : Consolidations

---

### **Formulaire Besoin** (`/api/v1/besoins/nouveau`)

**Sections** :
1. 📅 **Période** : Année + Trimestre/Semestre
2. 🏢 **Localisation** : Programme → Direction → Service (cascading)
3. 👤 **Description** : Poste, Grade, Nombre, Urgence
4. 📝 **Justification** : Motif détaillé

---

### **Vue Consolidée** (`/api/v1/besoins/consolidation`)

**Fonctionnalités** :
- Générer consolidation (Direction ou Programme)
- Liste des consolidations existantes
- Export des données (JSON)
- Statistiques par catégorie

**Tableau Consolidations** :
| Année | Niveau | Entité | Demandé | Obtenu | Taux | Statut | Actions |
|-------|--------|--------|---------|--------|------|--------|---------|
| 2025 | Direction | DAF | 10 | 7 | 70% | Transmis | 📥👁️ |

---

## 🎨 Design

### **Badges de Statut**
```css
Exprimé              → Gris (#adb5bd)
Transmis             → Cyan (#0dcaf0)
En attente           → Jaune (#ffc107)
Partiellement satisfait → Orange (#fd7e14)
Satisfait            → Vert (#198754)
Rejeté               → Rouge (#dc3545)
```

### **Badges d'Urgence**
```css
Faible    → Cyan clair
Normale   → Vert clair
Élevée    → Jaune
Critique  → Rouge
```

### **Barre de Progression**
```html
<div class="progress-container">
  <div class="progress-bar [low|medium|high]" style="width: 70%;">
    70%
  </div>
</div>
```

**Couleurs** :
- 0-49% : Rouge (low)
- 50-99% : Jaune (medium)
- 100% : Vert (high)

---

## 💾 Données Initiales

### **Aucune Donnée Pré-Créée**
Contrairement aux référentiels, les besoins sont **créés par les utilisateurs** selon les besoins réels.

### **Première Utilisation**
```
1. Page vide avec message
2. "Aucun besoin exprimé pour 2025"
3. Bouton "➕ Exprimer un Besoin"
4. Créer le premier besoin
```

---

## 🔄 Statuts des Besoins

| Statut | Description | Action Suivante |
|--------|-------------|-----------------|
| **Exprimé** | Besoin formulé par le service | Valider et transmettre |
| **Transmis** | Envoyé au Ministère | Attendre réponse |
| **En attente** | En cours d'examen ministère | Suivre l'évolution |
| **Partiellement satisfait** | Une partie obtenue | Noter la différence |
| **Satisfait** | Totalement obtenu | Archiver |
| **Rejeté** | Refusé par le ministère | Analyser et réessayer |

---

## 📈 Calculs Automatiques

### **Taux de Satisfaction**
```
Taux = (Nombre Obtenu / Nombre Demandé) × 100

Exemples:
- 10/10 = 100% → Satisfait ✅
- 5/10 = 50% → Partiellement satisfait ⚠️
- 0/10 = 0% → Rejeté ❌
```

### **Auto-Update du Statut**
Quand on met à jour le nombre obtenu :
```python
if nombre_obtenu == 0:
    statut = "En attente"
elif nombre_obtenu < nombre_demande:
    statut = "Partiellement satisfait"
elif nombre_obtenu >= nombre_demande:
    statut = "Satisfait"
    date_satisfaction = today()
```

---

## 📊 Consolidation

### **Par Direction**
```sql
SELECT 
    direction_id,
    SUM(nombre_demande) as total_demande,
    SUM(nombre_obtenu) as total_obtenu,
    SUM(CASE WHEN categorie='A' THEN nombre_demande END) as demande_cat_a,
    ...
FROM besoin_agent
WHERE annee = 2025 AND direction_id = 2
GROUP BY direction_id
```

**Résultat** :
```json
{
  "niveau": "Direction",
  "direction": "DAF",
  "total_demande": 10,
  "total_obtenu": 7,
  "taux_satisfaction": 70%,
  "par_categorie": {
    "A": {"demande": 2, "obtenu": 1},
    "B": {"demande": 4, "obtenu": 3},
    "C": {"demande": 3, "obtenu": 2},
    "D": {"demande": 1, "obtenu": 1}
  }
}
```

### **Par Programme**
Même logique mais agrège toutes les directions du programme.

---

## 🔍 Filtres et Recherche

### **Filtres Disponibles**
- **Année** : 2025, 2024, 2023
- **Statut** : Tous, Exprimé, Transmis, Satisfait, etc.
- **Service** : Filtre par service (via API)
- **Direction** : Filtre par direction (via API)

### **Exemple d'URL Filtrée**
```
/api/v1/besoins/api/besoins?annee=2025&statut=Transmis&direction_id=2
```

---

## 📥 Export

### **Format JSON**
```json
{
  "consolidation": {
    "annee": 2025,
    "niveau": "Direction",
    "total_demande": 10,
    "total_obtenu": 7,
    "taux_satisfaction": 70.0,
    "par_categorie": {...}
  },
  "besoins_detail": [
    {
      "poste": "Secrétaire",
      "grade": "B3",
      "service": "Comptabilité",
      "demande": 2,
      "obtenu": 1,
      "statut": "Partiellement satisfait"
    },
    ...
  ]
}
```

**Usage** :
- Import dans Excel
- Génération de rapports
- Transmission officielle au ministère

---

## 🧪 Exemples d'Utilisation

### **Exemple 1 : Service Comptabilité exprime un besoin**

```
1. Login en tant que Chef de Service
2. RH → Suivi des besoins agents
3. Cliquer "➕ Exprimer un Besoin"
4. Remplir:
   - Année: 2025
   - Période: Trimestre 1
   - Service: SCPT - Service Comptabilité
   - Poste: Secrétaire Comptable
   - Grade: B3
   - Nombre: 2 agents
   - Urgence: Normale
   - Motif: "Surcharge due à nouveau logiciel comptable"
5. Soumettre

Résultat:
✅ Besoin ID #1 créé
✅ Statut: Exprimé
✅ Visible dans tableau avec badge gris
```

---

### **Exemple 2 : DRH consolide les besoins de la DAF**

```
1. Login en tant que DRH
2. Besoins → Vue Consolidée
3. Générer consolidation:
   - Année: 2025
   - Niveau: Direction
   - Direction: DAF
4. Cliquer "📊 Générer"

Résultat:
✅ Consolidation créée
✅ Agrégats calculés:
   - Service Comptabilité: 2 agents
   - Service Budget: 3 agents
   - Service Approvisionnement: 5 agents
   → Total DAF: 10 agents demandés
✅ Répartition par catégorie:
   - A: 2, B: 4, C: 3, D: 1
```

---

### **Exemple 3 : Transmission et Suivi**

```
1. DRH transmet au ministère (email/courrier officiel)
2. Dans l'app, mettre à jour chaque besoin:
   - Cliquer 📝 sur besoin #1
   - Statut: Transmis
   - Date transmission: 01/02/2025
   - Enregistrer
3. Répéter pour tous les besoins

Résultat:
✅ Tous les besoins passent en "Transmis" (badge cyan)
✅ Dates de transmission enregistrées
✅ En attente de réponse

Quelques semaines plus tard...

4. Ministère répond: 7 agents accordés sur 10
5. Mettre à jour:
   - Besoin #1: Obtenu = 1 sur 2 demandés
   - Besoin #2: Obtenu = 3 sur 3 demandés
   - Besoin #3: Obtenu = 3 sur 5 demandés
   
Résultat:
✅ Statuts auto-calculés
✅ Taux de satisfaction: 70%
✅ Vue claire du déficit: 3 agents manquants
```

---

## 📊 Rapports et Analyses

### **KPIs Principaux**
1. **Total Besoins** : Nombre de besoins exprimés
2. **Total Demandé** : Effectif total demandé
3. **Total Obtenu** : Effectif effectivement obtenu
4. **Taux de Satisfaction** : % de satisfaction

### **Analyses Possibles**
- **Par Service** : Quel service a le plus de besoins ?
- **Par Catégorie** : Déficit en catégorie A vs B vs C vs D ?
- **Par Urgence** : Prioriser les besoins critiques
- **Évolution** : Comparer année N vs N-1

---

## 🎯 Avantages

### **Pour les Services**
1. ✅ **Formaliser** les besoins en personnel
2. ✅ **Justifier** les demandes avec motifs
3. ✅ **Suivre** l'évolution des demandes
4. ✅ **Prioriser** avec niveaux d'urgence

### **Pour les Directions**
1. ✅ **Vue d'ensemble** des besoins de tous les services
2. ✅ **Consolidation automatique** des demandes
3. ✅ **Priorisation** par urgence et criticité
4. ✅ **Reporting** pour la direction générale

### **Pour le Programme/DG**
1. ✅ **Vision globale** des besoins de l'organisation
2. ✅ **Consolidation ministère** prête à transmettre
3. ✅ **Suivi budget** lié aux recrutements
4. ✅ **Analyse déficit** par rapport aux besoins

### **Pour la DRH**
1. ✅ **Centralisation** de tous les besoins
2. ✅ **Suivi ministère** avec dates et statuts
3. ✅ **Évaluation performance** avec taux de satisfaction
4. ✅ **Historique complet** pour analyses futures

---

## 🔒 Sécurité

### **Authentification**
- ✅ Toutes les opérations nécessitent une connexion
- ✅ `current_user` vérifié sur chaque endpoint

### **Traçabilité**
- ✅ Qui a exprimé le besoin (`exprime_par_user_id`)
- ✅ Qui a validé (`valide_par_user_id`)
- ✅ Historique complet (`SuiviBesoin`)
- ✅ Logs de toutes les opérations

### **Validation**
- ✅ Champs requis vérifiés
- ✅ Nombre demandé > 0
- ✅ Service obligatoire
- ✅ Dates cohérentes

---

## 📱 Responsive

✅ Adapté pour tous les écrans  
✅ Tables scrollables sur mobile  
✅ Grilles adaptatives  
✅ Filtres empilés sur petits écrans  

---

## 🔜 Évolutions Futures

### **Court Terme**
- [ ] Notifications email lors des changements de statut
- [ ] Export PDF pour transmission officielle
- [ ] Import des réponses du ministère (CSV)
- [ ] Dashboard dédié avec graphiques

### **Moyen Terme**
- [ ] Workflow de validation interne avant transmission
- [ ] Historique des besoins sur plusieurs années (tendances)
- [ ] Prévisions basées sur l'historique
- [ ] Intégration avec système de budget

### **Long Terme**
- [ ] IA pour suggérer les besoins basés sur turnover
- [ ] API pour intégration avec système ministère
- [ ] Alerts automatiques pour besoins critiques non satisfaits
- [ ] Tableaux de bord temps réel

---

## 📁 Fichiers Créés

```
app/models/besoins.py                          ← Modèles (130 lignes)
app/api/v1/endpoints/besoins.py                ← Endpoints (320 lignes)
app/templates/pages/besoins.html               ← Page principale (430 lignes)
app/templates/pages/besoin_form.html           ← Formulaire (230 lignes)
app/templates/pages/besoins_consolidation.html ← Consolidation (245 lignes)
BESOINS_AGENTS_SYSTEM.md                       ← Ce fichier
```

---

## 🚀 Quick Start

### **Exprimer un Premier Besoin**
```
1. RH → Suivi des besoins agents
2. ➕ Exprimer un Besoin
3. Remplir le formulaire
4. Soumettre
5. ✅ Besoin dans la liste !
```

### **Consolider pour Transmission**
```
1. Plusieurs besoins exprimés
2. Vue Consolidée
3. Générer consolidation DAF 2025
4. 📥 Exporter en JSON
5. Transmettre au ministère
```

### **Mettre à Jour après Réponse**
```
1. Ministère a répondu
2. Pour chaque besoin:
   - 📝 Mettre à jour
   - Saisir nombre obtenu
   - Statut auto-calculé
3. Voir le taux de satisfaction global
```

---

## 📊 Impact

### **Avant**
- ❌ Besoins suivis dans Excel
- ❌ Consolidation manuelle
- ❌ Pas de traçabilité
- ❌ Calculs manuels
- ❌ Pas de vue d'ensemble

### **Après**
- ✅ Besoins dans l'application
- ✅ Consolidation automatique
- ✅ Traçabilité complète
- ✅ Calculs automatiques
- ✅ Dashboards en temps réel
- ✅ Export pour transmission officielle

---

**📊 Système de gestion des besoins en agents production-ready !**

Permet une gestion professionnelle du cycle complet : Expression → Consolidation → Transmission → Suivi → Évaluation 🎉

