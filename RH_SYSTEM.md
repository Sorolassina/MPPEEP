# 👥 Système de Gestion RH

## 📋 Vue d'Ensemble

Le système RH (Ressources Humaines) est un module complet de gestion administrative du personnel intégré à MPPEEP Dashboard. Il permet de gérer les agents, leurs demandes administratives (congés, permissions, formations, besoins d'actes) et de suivre le circuit de validation via un workflow paramétrique.

---

## 🎯 Fonctionnalités Principales

### **1. Gestion des Référentiels**
- **Agents** : Base de données du personnel (matricule, nom, prénom, grade, service)
- **Grades** : Catégories et niveaux hiérarchiques
- **Services/Départements** : Organisation administrative

### **2. Gestion des Demandes**
4 types de demandes supportées :
- 🏖️ **Congés** : Demandes de congés annuels, maladie, etc.
- ⏰ **Permissions** : Autorisations d'absence courte durée
- 📚 **Formations** : Demandes de formation professionnelle
- 📄 **Besoins d'actes** : Demandes d'actes administratifs

### **3. Workflow Paramétrique**
Circuit de validation configurable avec traçabilité complète :
- Soumission par l'agent
- Validation hiérarchique (N1, N2)
- Validation RH (DRH)
- Signature autorité (DG, DAF)
- Archivage automatique

### **4. Statistiques et KPIs**
- Effectifs totaux et agents actifs
- Agents en formation/congé/permission
- Répartition par grade et service
- Évolution des effectifs par année
- Taux de satisfaction (besoins d'actes)

---

## 🏗️ Architecture

### **Modèles de Données**

#### **Référentiels**
```python
# Grade (Catégories hiérarchiques)
class Grade(SQLModel, table=True):
    id: int
    code: str              # Ex: "A1", "B2"
    libelle: str           # Ex: "Catégorie A - Niveau 1"

# Service/Département
class ServiceDept(SQLModel, table=True):
    id: int
    code: str              # Ex: "DRH", "DSI"
    libelle: str           # Ex: "Direction des Ressources Humaines"

# Agent
class Agent(SQLModel, table=True):
    id: int
    matricule: str         # Unique
    nom: str
    prenom: str
    email: str
    date_recrutement: date
    actif: bool
    grade_id: int          # Foreign Key → Grade
    service_id: int        # Foreign Key → ServiceDept
```

#### **Demandes et Workflow**
```python
# Demande administrative
class HRRequest(SQLModel, table=True):
    id: int
    agent_id: int                    # Foreign Key → Agent
    type: RequestType                # CONGE, PERMISSION, FORMATION, BESOIN_ACTE
    objet: str                       # Objet de la demande
    motif: str                       # Motif détaillé
    date_debut: date                 # Pour congés/permissions/formations
    date_fin: date
    nb_jours: float
    satisfaction_note: int           # Note de satisfaction (1-5)
    current_state: WorkflowState     # État actuel dans le workflow
    current_assignee_role: str       # Rôle en charge (N1, DRH, DG...)
    created_at: datetime
    updated_at: datetime

# Configuration du workflow
class WorkflowStep(SQLModel, table=True):
    id: int
    type: RequestType                # Type de demande concerné
    from_state: WorkflowState        # État de départ
    to_state: WorkflowState          # État d'arrivée
    assignee_role: str               # Rôle responsable de l'étape
    order_index: int                 # Ordre d'exécution

# Historique des transitions
class WorkflowHistory(SQLModel, table=True):
    id: int
    request_id: int                  # Foreign Key → HRRequest
    from_state: WorkflowState
    to_state: WorkflowState
    acted_by_user_id: int            # Qui a effectué l'action
    acted_by_role: str               # Rôle de l'utilisateur
    comment: str                     # Commentaire éventuel
    acted_at: datetime               # Horodatage
```

### **Enums**
```python
# Types de demandes
class RequestType(str, Enum):
    CONGE = "Congé"
    PERMISSION = "Permission"
    FORMATION = "Formation"
    BESOIN_ACTE = "Besoin d'acte administratif"

# États du workflow
class WorkflowState(str, Enum):
    DRAFT = "Brouillon"              # Brouillon (agent)
    SUBMITTED = "Soumis"             # Soumis pour traitement
    VALIDATION_N1 = "Validation N1"  # Chef de service
    VALIDATION_N2 = "Validation N2"  # Chef de direction (optionnel)
    VALIDATION_DRH = "Validation DRH" # Direction RH
    SIGNATURE_DG = "Signature DG"    # Directeur Général
    SIGNATURE_DAF = "Signature DAF"  # Directeur Admin/Financier (optionnel)
    ARCHIVED = "Archivé"             # Traité et archivé
    REJECTED = "Rejeté"              # Rejeté
```

---

## 🔄 Workflow Standard

### **Circuit de Validation**

Pour tous les types de demandes, le circuit standard **obligatoire** est :

```
┌─────────────────┐
│  1. DRAFT       │  Agent crée une demande en brouillon
│  (Brouillon)    │
└────────┬────────┘
         ↓
┌─────────────────┐
│  2. SUBMITTED   │  Agent soumet la demande
│  (Soumis)       │
└────────┬────────┘
         ↓
┌─────────────────┐
│  3. VALIDATION  │  Chef de service valide (N1)
│     N1          │  → Validation hiérarchique niveau 1
└────────┬────────┘
         ↓
┌─────────────────┐
│  4. VALIDATION  │  Chef de direction valide (N2) ⭐ OBLIGATOIRE
│     N2          │  → Validation hiérarchique niveau 2
└────────┬────────┘
         ↓
┌─────────────────┐
│  5. VALIDATION  │  Direction RH valide
│     DRH         │  → Vérifie conformité administrative
└────────┬────────┘
         ↓
┌─────────────────┐
│  6. SIGNATURE   │  Directeur Général signe
│     DG          │  → Autorisation finale
└────────┬────────┘
         ↓
┌─────────────────┐
│  7. SIGNATURE   │  Directeur Admin/Financier ⭐ OBLIGATOIRE
│     DAF         │  → Signature finale pour aspects financiers
└────────┬────────┘
         ↓
┌─────────────────┐
│  8. ARCHIVED    │  Demande archivée et terminée
│  (Archivé)      │
└─────────────────┘

À tout moment : peut passer à REJECTED (Rejeté)
```

**Circuit complet (7 étapes obligatoires) :**
```
DRAFT → SUBMITTED → VALIDATION_N1 → VALIDATION_N2 → VALIDATION_DRH → SIGNATURE_DG → SIGNATURE_DAF → ARCHIVED
```

**Toutes les étapes sont obligatoires.** Chaque demande doit passer par l'ensemble du circuit.

### **Traçabilité Complète**

Chaque transition est enregistrée dans `WorkflowHistory` avec :
- ✅ État de départ et d'arrivée
- ✅ Utilisateur ayant effectué l'action
- ✅ Rôle de l'utilisateur
- ✅ Date et heure exacte
- ✅ Commentaire éventuel

---

## 📡 API et Endpoints

### **Structure des Routes : `/api/v1/rh/`**

#### **Pages HTML**
| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/` | Page principale avec KPIs et graphiques |
| GET | `/demandes/new` | Formulaire de création de demande |
| GET | `/demandes/{id}` | Détail d'une demande avec timeline |
| POST | `/demandes` | Traitement formulaire création |

#### **API REST (JSON)**

**Statistiques :**
| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/api/kpis` | KPIs RH (effectifs, agents en formation...) |
| GET | `/api/evolution` | Évolution des effectifs par année |
| GET | `/api/grade` | Répartition par grade |
| GET | `/api/service` | Répartition par service/département |
| GET | `/api/satisfaction-besoins` | Taux de satisfaction besoins |

**CRUD Demandes :**
| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/api/demandes/{id}` | Récupérer une demande (JSON) |
| POST | `/api/demandes` | Créer une demande (JSON) |

**Workflow :**
| Méthode | URL | Description |
|---------|-----|-------------|
| POST | `/demandes/{id}/submit` | Soumettre (DRAFT → SUBMITTED) |
| POST | `/demandes/{id}/to/{state}` | Transition vers un état |
| POST | `/demandes/{id}/advance` | Avancer dans le workflow |

**Référentiels :**
| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/api/agents` | Liste tous les agents |
| GET | `/api/grades` | Liste tous les grades |
| GET | `/api/services` | Liste tous les services |

---

## 💻 Service RHService

Le service `RHService` centralise toute la logique métier :

### **Statistiques**

```python
# KPIs complets
kpis = RHService.kpis(session)
# Retourne: {
#   "total_agents": 150,
#   "actifs": 145,
#   "en_formation": 12,
#   "en_conge": 8,
#   "permissionnaires": 3,
#   "satisfaction_besoins_archives": 4.2
# }

# Évolution par année
evolution = RHService.evolution_par_annee(session)
# Retourne: [{"annee": 2020, "effectif": 20}, ...]

# Répartition par grade
grades = RHService.repartition_par_grade(session)
# Retourne: [{"grade": "A1", "nb": 25}, ...]

# Répartition par service
services = RHService.repartition_par_service(session)
# Retourne: [{"service": "DRH", "nb": 15}, ...]

# Satisfaction besoins
satisfaction = RHService.satisfaction_besoins(session)
# Retourne: {"exprimes": 50, "satisfaits": 45, "taux": 90.0}
```

### **Gestion du Workflow**

```python
# Obtenir les prochaines étapes possibles
next_steps = RHService.next_states_for(session, RequestType.CONGE, WorkflowState.SUBMITTED)
# Retourne: [WorkflowStep(...), ...]

# Effectuer une transition
updated_request = RHService.transition(
    session=session,
    request_id=123,
    to_state=WorkflowState.VALIDATION_N1,
    acted_by_user_id=user.id,
    acted_by_role=user.type_user,
    comment="Approuvé"
)
# Vérifie que la transition est autorisée
# Enregistre dans l'historique
# Met à jour l'état de la demande
```

---

## 🚀 Utilisation

### **1. Initialisation du Système**

Le système s'initialise automatiquement au démarrage de l'application :

```bash
uvicorn app.main:app --reload
```

**Ce qui se passe :**
1. ✅ Création des tables RH (si elles n'existent pas)
2. ✅ Initialisation des workflow steps
3. ✅ Système prêt à l'emploi

**Logs attendus :**
```
👥 Initialisation du système RH...
✅ Système RH initialisé avec succès
```

### **2. Initialisation Manuelle avec Données d'Exemple**

```bash
python scripts/init_rh_system.py
```

**Crée automatiquement :**
- 5 grades d'exemple (A1, A2, B1, B2, C1)
- 4 services d'exemple (DRH, DAF, DSI, COM)
- Configuration complète des workflows

### **3. Créer une Demande (API)**

```python
# Via API REST
import httpx

response = httpx.post(
    "http://localhost:8000/api/v1/rh/api/demandes",
    params={"agent_id": 1},
    json={
        "type": "Congé",
        "objet": "Congé annuel",
        "motif": "Vacances d'été",
        "date_debut": "2025-07-01",
        "date_fin": "2025-07-15",
        "nb_jours": 10
    }
)
demande = response.json()
print(f"Demande créée : ID {demande['id']}")
```

### **4. Faire Avancer une Demande**

```python
# Soumettre la demande (agent)
response = httpx.post(
    f"http://localhost:8000/api/v1/rh/demandes/{demande_id}/submit"
)

# Valider (N1)
response = httpx.post(
    f"http://localhost:8000/api/v1/rh/demandes/{demande_id}/to/Validation N1"
)

# Chaque transition est enregistrée dans l'historique
```

---

## 📊 KPIs et Statistiques

### **Tableau de Bord RH**

Le système fournit des indicateurs clés en temps réel :

```python
kpis = RHService.kpis(session)
```

**Indicateurs disponibles :**
- 👥 **Effectif total** : Nombre total d'agents
- ✅ **Agents actifs** : Agents en activité
- 📚 **En formation** : Agents actuellement en formation
- 🏖️ **En congé** : Agents en congé
- ⏰ **Permissionnaires** : Agents en permission
- ⭐ **Satisfaction** : Note moyenne satisfaction (1-5)

### **Graphiques et Analyses**

**1. Évolution des Effectifs**
- Recrutements par année
- Tendance d'évolution

**2. Répartition par Grade**
- Distribution des agents par catégorie
- Visualisation pyramide des âges

**3. Répartition par Service**
- Charge par département
- Optimisation organisationnelle

**4. Satisfaction des Besoins**
- Taux de traitement des demandes
- Délais de traitement

---

## 🔐 Sécurité et Contrôle d'Accès

### **Principes**

1. **Authentification obligatoire**
   - Toutes les routes nécessitent un utilisateur connecté
   - Utilise `get_current_user` de l'authentification globale

2. **Traçabilité complète**
   - Chaque action est enregistrée
   - Audit trail dans `WorkflowHistory`

3. **Validation des transitions**
   - Seules les transitions autorisées sont possibles
   - Respect du workflow paramétré

### **Rôles et Permissions**

| Rôle | Permissions |
|------|-------------|
| **Agent** | Créer demandes, voir ses demandes |
| **N1** (Chef service) | Valider/rejeter demandes de son service |
| **N2** (Chef direction) | Valider/rejeter demandes de sa direction |
| **DRH** | Valider/rejeter toutes demandes, accès stats complètes |
| **DG/DAF** | Signature finale, accès complet |
| **Admin** | Accès total au système |

---

## 📝 Workflow de Configuration

### **Personnaliser le Workflow**

Le workflow est paramétrique et peut être adapté :

**Fichier :** `app/core/rh_workflow_seed.py`

```python
def ensure_workflow_steps(session: Session):
    # Définir les étapes pour chaque type de demande
    for request_type in [RequestType.CONGE, RequestType.PERMISSION, ...]:
        add(request_type, WorkflowState.DRAFT, WorkflowState.SUBMITTED, "N1", 1)
        add(request_type, WorkflowState.SUBMITTED, WorkflowState.VALIDATION_N1, "N1", 2)
        # ... autres étapes
```

**Possibilités :**
- ✅ Ajouter/retirer des étapes
- ✅ Modifier les rôles responsables
- ✅ Créer des circuits différents par type de demande
- ✅ Ajouter des branches conditionnelles

---

## 🧪 Tests et Validation

### **Tester les Imports**

```bash
python -c "from app.api.v1.endpoints import rh; print('✅ OK')"
python -c "from app.services import rh; print('✅ OK')"
python -c "from app.models import rh; print('✅ OK')"
```

### **Tester les Endpoints**

```bash
# KPIs
curl http://localhost:8000/api/v1/rh/api/kpis

# Liste des agents
curl http://localhost:8000/api/v1/rh/api/agents

# Statistiques
curl http://localhost:8000/api/v1/rh/api/evolution
```

---

## 🚀 Évolutions Futures

### **Fonctionnalités Prévues**

1. **Gestion Avancée des Agents**
   - Import/Export Excel
   - Historique de carrière
   - Documents associés (contrats, attestations)

2. **Notifications**
   - Email automatique lors des transitions
   - Rappels pour actions en attente
   - Notifications in-app

3. **Rapports et Exports**
   - Export PDF des demandes
   - Rapports mensuels/annuels
   - Statistiques personnalisées

4. **Calendrier**
   - Vue calendrier des congés/formations
   - Gestion des chevauchements
   - Planification des absences

5. **Intégration**
   - API externe pour systèmes tiers
   - Synchronisation avec paie
   - Connexion à Active Directory

---

## 📚 Ressources

### **Documentation Technique**

- `app/models/rh.py` - Modèles de données
- `app/services/rh.py` - Logique métier
- `app/api/v1/endpoints/rh.py` - Routes API
- `app/core/rh_workflow_seed.py` - Configuration workflow

### **Scripts Utilitaires**

- `scripts/init_rh_system.py` - Initialisation avec données exemple
- `scripts/test_rh_imports.py` - Test de validation

### **Templates HTML**

- `app/templates/pages/rh.html` - Dashboard principal
- `app/templates/pages/rh_demande_new.html` - Formulaire
- `app/templates/pages/rh_demande_detail.html` - Détail demande

---

## 💡 Bonnes Pratiques

1. **Toujours utiliser le service RHService**
   - Ne pas accéder directement aux modèles
   - Centraliser la logique métier

2. **Traçabilité**
   - Toujours renseigner le commentaire lors des transitions
   - Conserver l'historique complet

3. **Validation**
   - Vérifier les permissions avant toute action
   - Valider les données en entrée

4. **Performance**
   - Utiliser les endpoints JSON pour les données
   - Mettre en cache les statistiques fréquentes

---

## 📞 Support

Pour toute question ou problème :

1. Consulter les logs de l'application
2. Vérifier l'initialisation du système RH au démarrage
3. Tester les imports et endpoints
4. Consulter la documentation technique

**Status :** ✅ Production-ready  
**Version :** 1.0  
**Dernière mise à jour :** 2025-01-12

