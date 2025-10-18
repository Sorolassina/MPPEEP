# 🎓 Explication Complète du Fonctionnement des Workflows

## 📋 Vue d'Ensemble

Le système de workflows permet de **gérer automatiquement le circuit de validation des demandes** selon la position hiérarchique de l'agent.

---

## 🔄 Fonctionnement Étape par Étape

### **ÉTAPE 1 : Configuration (Une seule fois)**

#### **A. L'administrateur configure les workflows**

**Via l'interface :** `http://localhost:8000/api/v1/admin/workflow-config`

**Action 1 : Initialiser les workflows système**
```
Admin clique sur "🔄 Initialiser les Workflows Système"
                    ↓
Appel API: POST /admin/workflow-config/api/initialize-system-workflows
                    ↓
Service WorkflowConfigService.initialize_system_workflows()
                    ↓
Crée 3 templates en base de données:

1. Circuit Long (CIRCUIT_LONG_RH)
   └─ Étape 1: N+1
   └─ Étape 2: N+2
   └─ Étape 3: RH
   └─ Étape 4: DAF

2. Circuit Moyen (CIRCUIT_MOYEN)
   └─ Étape 1: N+1
   └─ Étape 2: N+2

3. Tâche Descendante (TACHE_DESCENDANTE)
   └─ Étape 1: DEMANDEUR (retour à l'agent)
```

**Action 2 : Créer un type de demande**
```
Admin va sur onglet "Types de Demandes"
Admin clique "➕ Créer un Type de Demande"
                    ↓
Remplit le formulaire:
  - Code: DEMANDE_MATERIEL
  - Libellé: Demande de Matériel
  - Template: Circuit Moyen (sans RH)
  - Catégorie: Logistique
                    ↓
Enregistre
                    ↓
Appel API: POST /admin/workflow-config/api/request-types
                    ↓
Service WorkflowConfigService.create_request_type()
                    ↓
Crée dans la table request_type_custom:
  - code: DEMANDE_MATERIEL
  - workflow_template_id: 2 (Circuit Moyen)
  - actif: true
```

**Résultat :**
✅ Le type "Demande de Matériel" est maintenant disponible pour tous les utilisateurs !

---

### **ÉTAPE 2 : Utilisation (À chaque demande)**

#### **A. Un agent crée une demande**

**Contexte :**
- Jean KOUASSI (Agent, Service Budget)
- Marie DIALLO (Chef du Service Budget)
- Paul BAMBA (Sous-directeur Budget)

**Action :**
```
Jean va sur: http://localhost:8000/api/v1/rh/
Jean clique "Nouvelle demande"
Jean choisit le type: "Demande de Matériel"
Jean remplit le formulaire
Jean clique "Soumettre"
                    ↓
Appel API: POST /api/v1/rh/demandes
                    ↓
Backend crée une HRRequest:
  - type: DEMANDE_MATERIEL
  - agent_id: 15 (Jean)
  - current_state: DRAFT
  - current_assignee_role: AGENT
                    ↓
Demande créée avec ID: 42
```

---

#### **B. Le système détermine le circuit**

**Quand Jean soumet la demande :**

```
Jean clique "Soumettre"
                    ↓
Appel API: POST /api/v1/rh/demandes/42/submit
                    ↓
Backend appelle: RHService.transition(42, SUBMITTED, user_id=15)
                    ↓
RHService vérifie la transition: DRAFT → SUBMITTED ✅
                    ↓
HierarchyService.get_hierarchy(agent_id=15)
                    ↓
Analyse la position de Jean:
  1. fonction = "Agent" (ou vide)
  2. service_id = 5 (Service Budget)
                    ↓
Cherche le Chef du service:
  SELECT * FROM service WHERE id=5
  → chef_service_id = 8 (Marie)
                    ↓
Cherche le Sous-directeur:
  direction_id = 2 (Direction Budget)
  SELECT * FROM direction WHERE id=2
  → directeur_id = 3 (Paul)
                    ↓
Résultat hiérarchie:
  - position: "Agent"
  - n_plus_1: Marie (ID: 8)
  - n_plus_2: Paul (ID: 3)
  - rh: Sophie (ID: 12)
  - daf: Pierre (ID: 1)
```

**HierarchyService.get_workflow_circuit(agent_id=15, type=DEMANDE_MATERIEL)**

```
1. Récupère le template associé au type DEMANDE_MATERIEL
   → Template: Circuit Moyen (N+1, N+2)

2. Construit le circuit selon la position de Jean:
   [DRAFT, SUBMITTED, VALIDATION_N1, VALIDATION_N2, ARCHIVED]

3. Comme c'est "Circuit Moyen", pas de RH ni DAF
```

**Mise à jour de la demande :**
```
HRRequest (ID: 42):
  - current_state: SUBMITTED
  - current_assignee_role: N1 (Marie doit valider)
```

---

#### **C. Marie valide (N+1)**

**Marie se connecte et va sur son dashboard RH**

```
HierarchyService.get_pending_requests_for_user(user_id=8)
                    ↓
1. Récupère l'agent de Marie: agent_id=8

2. Pour chaque demande non archivée:
   - Demande 42: agent_id=15 (Jean), current_state=SUBMITTED
   - Calcule le circuit: [DRAFT, SUBMITTED, VALIDATION_N1, VALIDATION_N2, ARCHIVED]
   - État actuel: SUBMITTED (index 1)
   - Prochain état: VALIDATION_N1 (index 2)
   
3. HierarchyService.get_expected_validator(request_id=42, to_state=VALIDATION_N1)
   ↓
   Récupère la hiérarchie de Jean (agent_id=15)
   Pour VALIDATION_N1 → Validateur = n_plus_1 = Marie (agent_id=8)
   
4. Compare: Marie (8) == Validateur attendu (8) ✅
   → La demande 42 est dans les "pending_requests" de Marie
```

**Dashboard de Marie :**
```html
Section: "⏳ Demandes en attente de ma validation"
  - Demande #42 (Jean KOUASSI - Demande de Matériel)
  - Bouton "Valider" visible ✅
```

**Marie clique "Valider" :**
```
Appel API: POST /api/v1/rh/demandes/42/to/VALIDATION_N1
                    ↓
RHService.transition(42, VALIDATION_N1, user_id=8)
                    ↓
HierarchyService.can_user_validate(user_id=8, request_id=42, to_state=VALIDATION_N1)
                    ↓
1. Récupère l'agent de Marie: agent_id=8
2. Récupère le validateur attendu pour VALIDATION_N1
   → expected_validator = Marie (8)
3. Compare: Marie (8) == Expected (8) ✅ AUTORISÉ
                    ↓
Mise à jour:
  - current_state: VALIDATION_N1
  - current_assignee_role: N2 (Paul doit valider maintenant)
                    ↓
WorkflowHistory créé:
  - from_state: SUBMITTED
  - to_state: VALIDATION_N1
  - acted_by_user_id: 8 (Marie)
  - acted_by_role: "N1"
```

---

#### **D. Paul valide (N+2)**

**Paul se connecte**

```
HierarchyService.get_pending_requests_for_user(user_id=3)
                    ↓
Demande 42:
  - État actuel: VALIDATION_N1
  - Prochain état: VALIDATION_N2
  - Validateur attendu: Paul (3) ✅
                    ↓
Paul voit la demande dans son dashboard
Paul clique "Valider"
                    ↓
Transition: VALIDATION_N1 → VALIDATION_N2
                    ↓
Comme c'est le dernier validateur du Circuit Moyen:
  - Prochain état: ARCHIVED
  - current_assignee_role: NULL
                    ↓
Demande terminée ! ✅
```

---

### **ÉTAPE 3 : Sécurité - Tentative Non Autorisée**

#### **Si un autre agent (Sophie) tente de valider la demande de Jean :**

```
Sophie clique sur la demande de Jean
Sophie clique "Valider"
                    ↓
Appel API: POST /api/v1/rh/demandes/42/to/VALIDATION_N1
                    ↓
RHService.transition(42, VALIDATION_N1, user_id=12)
                    ↓
HierarchyService.can_user_validate(user_id=12, request_id=42, to_state=VALIDATION_N1)
                    ↓
1. Récupère l'agent de Sophie: agent_id=12
2. Récupère le validateur attendu pour VALIDATION_N1
   → expected_validator = Marie (8)
3. Compare: Sophie (12) != Marie (8) ❌ REFUSÉ
                    ↓
ValueError lancée:
"Vous n'êtes pas autorisé à effectuer cette validation.
 Cette action doit être effectuée par : Marie DIALLO"
                    ↓
HTTPException 400 renvoyée au frontend
                    ↓
Message d'erreur affiché à Sophie ❌
AUCUNE modification en base de données
```

---

## 🎯 Schémas Détaillés

### **Schéma 1 : Détermination de la Hiérarchie**

```
┌─────────────────────────────────────────────────────────────┐
│ Agent: Jean KOUASSI (ID: 15)                                 │
│ Fonction: "Agent"                                            │
│ Service: Budget (ID: 5)                                      │
│ Direction: Direction Budget (ID: 2)                          │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ HierarchyService.get_hierarchy(15)                          │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Étape 1: Analyser la fonction                               │
│ "agent" in fonction.lower() → Oui                           │
│ "chef" in fonction.lower() → Non                            │
│ → Position = "Agent"                                        │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Étape 2: Chercher N+1 (Chef de service)                    │
│ Service ID: 5                                                │
│ SELECT * FROM service WHERE id=5                            │
│ → chef_service_id = 8                                       │
│ SELECT * FROM agent_complet WHERE id=8                      │
│ → Marie DIALLO                                              │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Étape 3: Chercher N+2 (Sous-directeur)                     │
│ Direction ID: 2                                              │
│ SELECT * FROM direction WHERE id=2                          │
│ → directeur_id = 3                                          │
│ SELECT * FROM agent_complet WHERE id=3                      │
│ → Paul BAMBA                                                │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Étape 4: Chercher RH                                        │
│ SELECT * FROM direction WHERE code LIKE '%RH%'              │
│ → direction.directeur_id = 12                               │
│ → Sophie TRAORÉ                                             │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Étape 5: Chercher DAF                                       │
│ SELECT * FROM agent_complet WHERE fonction LIKE '%DAF%'     │
│ → Pierre KONÉ (ID: 1)                                       │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ RÉSULTAT:                                                    │
│ {                                                            │
│   'agent': Jean (15),                                        │
│   'position': 'Agent',                                       │
│   'n_plus_1': Marie (8),                                     │
│   'n_plus_2': Paul (3),                                      │
│   'rh': Sophie (12),                                         │
│   'daf': Pierre (1)                                          │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
```

---

### **Schéma 2 : Construction du Circuit**

```
┌─────────────────────────────────────────────────────────────┐
│ Type de demande: DEMANDE_MATERIEL                           │
│ Template associé: Circuit Moyen                             │
│ Agent: Jean (position: "Agent")                             │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ HierarchyService.get_workflow_circuit(15, DEMANDE_MATERIEL) │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Étape 1: États de base                                      │
│ circuit = [DRAFT, SUBMITTED]                                │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Étape 2: Ajouter les validateurs hiérarchiques             │
│ Position = "Agent"                                          │
│ n_plus_1 existe? → Oui (Marie)                             │
│   circuit.append(VALIDATION_N1)                             │
│ n_plus_2 existe? → Oui (Paul)                              │
│   circuit.append(VALIDATION_N2)                             │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Étape 3: Vérifier le type                                   │
│ Type dans SHORT_CIRCUIT_TYPES (PERMISSION)? → Non          │
│ Type dans RH_REQUIRED_TYPES (CONGE...)? → Non              │
│ → Type personnalisé, pas de RH ni DAF                       │
│   circuit.append(ARCHIVED)                                  │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ RÉSULTAT FINAL:                                             │
│ [DRAFT, SUBMITTED, VALIDATION_N1, VALIDATION_N2, ARCHIVED]  │
│                                                              │
│ Traduction:                                                  │
│ Brouillon → Soumis → Marie valide → Paul valide → Terminé  │
└─────────────────────────────────────────────────────────────┘
```

---

### **Schéma 3 : Validation avec Contrôle d'Accès**

```
┌─────────────────────────────────────────────────────────────┐
│ Marie clique "Valider" sur la demande de Jean              │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Frontend: onclick="advance('VALIDATION_N1')"                │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ API: POST /api/v1/rh/demandes/42/to/VALIDATION_N1          │
│ current_user: Marie (user_id=8)                             │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ RHService.transition()                                       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ CONTRÔLE 1: Transition autorisée?                       │ │
│ │ current_state=SUBMITTED, to_state=VALIDATION_N1         │ │
│ │ WorkflowStep existe? ✅ Oui                             │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ CONTRÔLE 2: Utilisateur autorisé? (NOUVEAU)            │ │
│ │ HierarchyService.can_user_validate(8, 42, VALIDATION_N1)│ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ can_user_validate():                                         │
│                                                              │
│ 1. Récupère l'agent de Marie: agent_id=8                   │
│                                                              │
│ 2. Récupère le validateur attendu:                         │
│    get_expected_validator(42, VALIDATION_N1)               │
│    ├─ Récupère la demande: agent_id=15 (Jean)             │
│    ├─ Récupère la hiérarchie de Jean                      │
│    └─ Pour VALIDATION_N1 → return hierarchy['n_plus_1']   │
│       → Marie (8)                                           │
│                                                              │
│ 3. Compare:                                                 │
│    user_agent.id (8) == expected_validator.id (8)          │
│    → True ✅ AUTORISÉ                                      │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Mise à jour de la demande:                                  │
│ - current_state = VALIDATION_N1                             │
│ - current_assignee_role = N2 (Paul)                         │
│                                                              │
│ WorkflowHistory créé:                                        │
│ - from_state: SUBMITTED                                     │
│ - to_state: VALIDATION_N1                                   │
│ - acted_by_user_id: 8 (Marie)                               │
│ - acted_by_role: "N1"                                       │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Réponse au frontend: {"ok": true, "state": "VALIDATION_N1"}│
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Frontend affiche: "✅ Demande validée avec succès"         │
│ Page actualisée                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 Cas Particuliers

### **Cas 1 : Chef de service crée une demande**

**Exemple : Marie (Chef) demande un congé**

```
Marie → HierarchyService.get_hierarchy(8)
                    ↓
fonction = "Chef de service"
                    ↓
N+1 = Sous-directeur (Paul)
N+2 = DAF (Pierre)
                    ↓
Circuit:
[DRAFT, SUBMITTED, VALIDATION_N1, VALIDATION_N2, VALIDATION_RH, SIGNATURE_DAF, ARCHIVED]
        ↓           ↓               ↓                ↓                 ↓
      Marie       Paul             Pierre          Sophie           Pierre
```

**Différence :**
- ✅ Marie n'a que 2 niveaux de validation (N+1=Paul, N+2=Pierre)
- ✅ Ensuite RH et DAF comme tout le monde

---

### **Cas 2 : Sous-directeur RH demande un congé**

**Exemple : Sophie (RH) demande un congé**

```
Sophie → HierarchyService.get_hierarchy(12)
                    ↓
fonction = "Sous-directeur"
                    ↓
N+1 = DAF (Pierre)
N+2 = NULL (pas de N+2 pour un sous-directeur)
                    ↓
Type = CONGE (nécessite RH)
Mais Sophie EST le RH !
→ rh = NULL (ne peut pas se valider elle-même)
                    ↓
Circuit:
[DRAFT, SUBMITTED, SIGNATURE_DAF, ARCHIVED]
        ↓              ↓
     Sophie         Pierre
```

**Résultat :**
- ✅ Sophie soumet directement au DAF
- ✅ Pas de passage par RH (c'est elle !)

---

### **Cas 3 : Type avec RH obligatoire (CONGE)**

**Exemple : Jean demande un congé**

```
Type = CONGE
Type in RH_REQUIRED_TYPES? → Oui ✅
                    ↓
Circuit pour Agent:
[DRAFT, SUBMITTED, VALIDATION_N1, VALIDATION_N2, VALIDATION_RH, SIGNATURE_DAF, ARCHIVED]
        ↓           ↓               ↓                ↓                 ↓           ↓
      Jean        Marie            Paul            Sophie           Pierre    Système
```

**Différence :**
- ✅ Ajoute VALIDATION_RH après N+2
- ✅ Ajoute SIGNATURE_DAF avant archivage

---

### **Cas 4 : Type court (PERMISSION)**

```
Type = PERMISSION
Type in SHORT_CIRCUIT_TYPES? → Oui ✅
                    ↓
Circuit:
[DRAFT, SUBMITTED, VALIDATION_N1, VALIDATION_N2, ARCHIVED]
        ↓           ↓               ↓           ↓
      Jean        Marie            Paul     Système
```

**Différence :**
- ✅ S'arrête au N+2 (Paul)
- ✅ Pas de RH ni DAF

---

## 📊 Base de Données - Tables et Relations

### **Tables de Configuration**

```sql
-- 1. Template de workflow
workflow_template
├─ id, code, nom
├─ direction (ASCENDANT/DESCENDANT)
└─ est_systeme (protégé si true)

-- 2. Étapes du template
workflow_template_step
├─ template_id → workflow_template
├─ order_index (1, 2, 3...)
├─ role_type (N+1, N+2, RH, DAF, CUSTOM)
└─ obligatoire, peut_rejeter

-- 3. Types de demandes
request_type_custom
├─ code, libelle
├─ workflow_template_id → workflow_template
├─ categorie (RH, Logistique...)
└─ necessite_validation_rh, necessite_validation_daf

-- 4. Rôles personnalisés
custom_role
└─ code, libelle

-- 5. Attribution de rôles
custom_role_assignment
├─ custom_role_id → custom_role
├─ agent_id → agent_complet
└─ date_debut, date_fin

-- 6. Historique config
workflow_config_history
├─ entity_type, entity_id
├─ action (CREATE, UPDATE, DELETE)
└─ performed_by, performed_at
```

### **Tables de Workflow Existantes (ancien système)**

```sql
-- Demandes RH
hrrequest
├─ type (CONGE, PERMISSION...)
├─ agent_id → agent
├─ current_state (DRAFT, SUBMITTED...)
└─ current_assignee_role (N1, N2, RH, DAF)

-- Étapes de workflow (ancien)
workflowstep
├─ type, from_state, to_state
├─ assignee_role
└─ order_index

-- Historique des transitions
workflowhistory
├─ request_id → hrrequest
├─ from_state → to_state
└─ acted_by_user_id, acted_by_role
```

---

## 🎯 Flux Complet : De la Configuration à l'Archivage

```
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 1: CONFIGURATION (Admin, une fois)                         │
├──────────────────────────────────────────────────────────────────┤
│ Admin → Interface Config → Initialiser Workflows Système        │
│                          → Créer types de demandes              │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 2: CRÉATION (Agent)                                        │
├──────────────────────────────────────────────────────────────────┤
│ Jean → RH → Nouvelle Demande → Choisir type → Remplir → Créer  │
│ État: DRAFT                                                      │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 3: SOUMISSION (Agent)                                      │
├──────────────────────────────────────────────────────────────────┤
│ Jean → Soumettre                                                 │
│ HierarchyService → Calcule circuit                              │
│ État: SUBMITTED, Assigné à: N1 (Marie)                          │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 4: VALIDATION N+1 (Chef)                                   │
├──────────────────────────────────────────────────────────────────┤
│ Marie → Dashboard → "Demandes en attente" → Voit demande Jean  │
│ Marie → Valider                                                  │
│ HierarchyService → Vérifie: Marie = N+1 de Jean? ✅             │
│ État: VALIDATION_N1, Assigné à: N2 (Paul)                       │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 5: VALIDATION N+2 (Sous-directeur)                         │
├──────────────────────────────────────────────────────────────────┤
│ Paul → Dashboard → Voit demande Jean                            │
│ Paul → Valider                                                   │
│ HierarchyService → Vérifie: Paul = N+2 de Jean? ✅              │
│ État: VALIDATION_N2, Assigné à: NULL (dernier validateur)       │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 6: ARCHIVAGE (Automatique)                                 │
├──────────────────────────────────────────────────────────────────┤
│ Système → Transition automatique vers ARCHIVED                  │
│ État: ARCHIVED                                                   │
│ ✅ Demande terminée !                                           │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Sécurité - Défense en Profondeur

### **Niveau 1 : Frontend (UX)**
```javascript
// N'afficher les boutons que si l'utilisateur peut valider
{% if can_validate %}
  <button>Valider</button>
{% else %}
  <span>⏳ En attente de {{ assignee_role }}</span>
{% endif %}
```

**But :** Éviter les clics inutiles

---

### **Niveau 2 : Backend (Sécurité)**
```python
# Vérifier OBLIGATOIREMENT que l'utilisateur a le droit
can_validate = HierarchyService.can_user_validate(...)
if not can_validate:
    raise ValueError("Action refusée")
```

**But :** Bloquer les tentatives non autorisées (même si quelqu'un bidouille le HTML)

---

### **Niveau 3 : Base de Données (Intégrité)**
```sql
-- Audit trail complet
INSERT INTO workflowhistory (
    request_id, from_state, to_state,
    acted_by_user_id, acted_by_role, timestamp
)
```

**But :** Traçabilité complète, aucune action anonyme

---

## 🎓 Exemples Concrets

### **Exemple 1 : Créer un type "Demande de Mission"**

**Besoin :**
Circuit simple : Agent → N+1 → Archivé

**Configuration :**
```
1. Template: Créer "Circuit Court"
   - Direction: ASCENDANT
   - Étapes: 
     * Ordre 1: N+1

2. Type de demande: "DEMANDE_MISSION"
   - Template: Circuit Court
   - Catégorie: Administratif
   - Document obligatoire: Oui

3. Résultat:
   - Type disponible dans RH ✅
   - Circuit: Agent → N+1 → Archivé ✅
```

---

### **Exemple 2 : Créer un rôle "Responsable Budget"**

**Besoin :**
Toutes les demandes budgétaires doivent passer par un agent spécifique (indépendamment de la hiérarchie)

**Configuration :**
```
1. Rôle: Créer "RESP_BUDGET"
   - Libellé: Responsable Budget
   
2. Attribution: Attribuer à Jean KOUASSI (agent_id=15)

3. Template: Créer "Circuit Budget"
   - Étapes:
     * Ordre 1: CUSTOM (custom_role_name: RESP_BUDGET)
     * Ordre 2: DAF

4. Type: "DEMANDE_BUDGET"
   - Template: Circuit Budget
   
5. Résultat:
   - Toute demande budgétaire → Jean → DAF ✅
   - Même si le demandeur est le chef de Jean !
```

---

### **Exemple 3 : Tâche descendante (Chef → Agent)**

**Besoin :**
Le chef assigne une tâche à un agent, qui doit marquer "Terminé"

**Configuration :**
```
1. Template: TACHE_DESCENDANTE (déjà créé par initialisation)
   - Direction: DESCENDANT
   - Étapes:
     * Ordre 1: DEMANDEUR (retour à l'agent)

2. Type: "INSTRUCTION_CHEF"
   - Template: Tâche Descendante
   - Direction: DESCENDANT

3. Utilisation:
   Marie (Chef) → Créer "Instruction" → Assigner à Jean
   État: SUBMITTED, Assigné à: Jean
   
   Jean → Dashboard → Voit l'instruction
   Jean → Marquer "Terminé"
   État: ARCHIVED ✅
```

---

## 🎉 Conclusion

Le système de workflows fonctionne en **5 étapes** :

1. **Configuration** (Admin) → Définir les templates et types
2. **Détermination de hiérarchie** (Système) → Calculer N+1, N+2, RH, DAF
3. **Construction du circuit** (Système) → Adapter selon position et type
4. **Validation** (Utilisateurs) → Contrôle d'accès strict
5. **Traçabilité** (Système) → Audit trail complet

**Tout est automatique, sauf la configuration initiale !** 🎯

---

**Rafraîchissez la page et testez le modal ! 🚀**

