# 🚀 Plan d'Implémentation - Workflow Hiérarchique Dynamique

## 📋 Règles Métier Validées

### **1. Circuits de validation par type**

```python
# Circuit LONG (avec RH)
CONGE, FORMATION, BESOIN_ACTE
└→ Agent → Chef Service (N+1) → Sous-directeur (N+2) → RH → DAF → Archivé

# Circuit MOYEN (sans RH)
PERMISSION
└→ Agent → Chef Service (N+1) → Sous-directeur (N+2) → Archivé

# Circuit COURT (demandes du RH)
Si demandeur = Sous-directeur RH
└→ RH → DAF → Archivé

# Circuit DAF
Si demandeur = DAF
└→ DAF → Archivé (auto-validation)
```

### **2. Structure hiérarchique**

```
Niveau 1: Agent
Niveau 2: Chef de service
Niveau 3: Sous-directeur (Budget / MG&Compta / RH)
Niveau 4: DAF
```

### **3. Paramétrage du workflow**

Interface d'administration pour configurer :
- Types de demandes
- Rôles et hiérarchie
- Circuits de validation
- Types d'actes administratifs

---

## 🔍 Analyse de la Base de Données

### **Tables existantes :**

#### **Structure organisationnelle :**
```sql
Programme → Direction → Service
```

#### **Agent :**
```python
AgentComplet:
  - service_id → Service
  - direction_id → Direction
  - programme_id → Programme
  - fonction: str  # "Agent", "Chef de service", "Sous-directeur", "DAF"
  - user_id → User
```

#### **Service :**
```python
Service:
  - chef_service_id → AgentComplet (FK)
  - direction_id → Direction (FK)
```

#### **Direction :**
```python
Direction:
  - directeur_id → AgentComplet (FK)  # Sous-directeur
  - programme_id → Programme (FK)
```

### **⚠️ Problème identifié :**

**Manque de lien hiérarchique direct dans `AgentComplet` !**

Actuellement :
- ❌ Pas de champ `chef_direct_id` (N+1)
- ❌ Pas de champ `sous_directeur_id` (N+2)

**Solution :**
On peut déduire la hiérarchie via :
1. `agent.service_id` → `service.chef_service_id` = N+1
2. `agent.direction_id` → `direction.directeur_id` = N+2

---

## 📦 Fichiers à créer/modifier

### **1. Service de hiérarchie** ✨ NOUVEAU

**Fichier :** `app/services/hierarchy_service.py`

```python
class HierarchyService:
    """Service pour déterminer la hiérarchie d'un agent"""
    
    @staticmethod
    def get_hierarchy(session, agent_id: int) -> dict:
        """
        Retourne la hiérarchie complète d'un agent
        Returns:
        {
            'n_plus_1': AgentComplet | None,
            'n_plus_2': AgentComplet | None,
            'rh': AgentComplet | None,
            'daf': AgentComplet | None,
            'position': str  # "Agent", "Chef de service", "Sous-directeur", "DAF"
        }
        """
    
    @staticmethod
    def get_circuit_for_request(session, agent_id: int, request_type: RequestType) -> List[WorkflowStep]:
        """Détermine le circuit de validation selon l'agent et le type"""
    
    @staticmethod
    def can_user_validate(session, user_id: int, request_id: int) -> bool:
        """Vérifie si un utilisateur peut valider une demande"""
```

### **2. Modification du workflow** 🔄 MODIFIER

**Fichier :** `app/core/logique_metier/rh_workflow.py`

```python
# Ajouter des circuits conditionnels selon le type
def ensure_workflow_steps(session: Session):
    """Crée les circuits de base (standard)"""
    # Ces circuits serviront de TEMPLATE
    # Le circuit réel sera calculé dynamiquement par HierarchyService
```

### **3. Modification du service RH** 🔄 MODIFIER

**Fichier :** `app/services/rh.py`

```python
class RHService:
    @staticmethod
    def transition(session, request_id, to_state, user_id, user_role):
        """
        AJOUT: Vérifier que user_id est bien le validateur attendu
        via HierarchyService.can_user_validate()
        """
```

### **4. Modification des endpoints** 🔄 MODIFIER

**Fichier :** `app/api/v1/endpoints/rh.py`

```python
@router.get("/", name="rh_home")
def rh_home(..., current_user: User = Depends(get_current_user)):
    """
    AJOUT: Filtrer les demandes selon la position de l'utilisateur
    - Demandes créées par l'utilisateur
    - Demandes en attente de validation par l'utilisateur
    """

@router.get("/demandes/{request_id}", name="rh_demande_detail")
def rh_demande_detail(..., current_user: User = Depends(get_current_user)):
    """
    AJOUT: 
    - Calculer les actions possibles selon la position de current_user
    - Afficher uniquement les boutons pertinents
    """

@router.post("/demandes/{request_id}/to/{to_state}")
def transition_demande(..., current_user: User = Depends(get_current_user)):
    """
    AJOUT: Vérifier via HierarchyService.can_user_validate()
    """
```

### **5. Modification du template** 🔄 MODIFIER

**Fichier :** `app/templates/pages/rh_demande_detail.html`

```jinja
{# Afficher les boutons UNIQUEMENT si l'utilisateur peut valider #}
{% if can_validate %}
  <button onclick="advance(...)">Valider</button>
{% else %}
  <span>⏳ En attente de validation par {{ req.current_assignee_role }}</span>
{% endif %}
```

### **6. Interface d'administration du workflow** ✨ NOUVEAU

**Fichiers :**
- `app/api/v1/endpoints/workflow_admin.py` (API)
- `app/templates/pages/workflow_configuration.html` (Interface)

Configuration :
- Types de demandes
- Rôles
- Circuits
- Types d'actes

---

## 🎯 Implémentation Étape par Étape

### **PHASE 1 : Service de hiérarchie** (30 min)

1. Créer `app/services/hierarchy_service.py`
2. Implémenter `get_hierarchy(agent_id)`
3. Implémenter `get_circuit_for_request(agent_id, request_type)`
4. Implémenter `can_user_validate(user_id, request_id)`
5. Tests unitaires

### **PHASE 2 : Contrôle d'accès** (20 min)

1. Modifier `RHService.transition()` pour vérifier le validateur
2. Modifier endpoint `transition_demande()` avec vérification
3. Tester avec différents rôles

### **PHASE 3 : Dashboard filtré** (15 min)

1. Modifier `rh_home()` pour filtrer les demandes
2. Ajouter logique de filtrage selon position hiérarchique
3. Tester l'affichage selon différents profils

### **PHASE 4 : Interface détail demande** (15 min)

1. Modifier `rh_demande_detail()` pour calculer `can_validate`
2. Modifier template pour affichage conditionnel des boutons
3. Tester avec différents utilisateurs

### **PHASE 5 : Workflow dynamique** (20 min)

1. Modifier `rh_workflow.py` pour circuits conditionnels
2. Intégrer `HierarchyService` dans la création de demandes
3. Tester les différents circuits (PERMISSION vs CONGE)

### **PHASE 6 : Administration du workflow** (40 min)

1. Créer modèles `WorkflowConfiguration`, `RoleDefinition`
2. Créer API `workflow_admin.py`
3. Créer interface `workflow_configuration.html`
4. Tester la configuration

---

## 📊 Algorithme de détermination de hiérarchie

```python
def get_hierarchy(session, agent_id):
    agent = session.get(AgentComplet, agent_id)
    hierarchy = {}
    
    # 1. Déterminer la position de l'agent
    fonction = agent.fonction.lower()
    
    if "agent" in fonction and "chef" not in fonction:
        # Agent simple
        hierarchy['position'] = "Agent"
        
        # N+1 = Chef de service
        if agent.service_id:
            service = session.get(Service, agent.service_id)
            hierarchy['n_plus_1'] = session.get(AgentComplet, service.chef_service_id)
        
        # N+2 = Sous-directeur (directeur de la direction)
        if agent.direction_id:
            direction = session.get(Direction, agent.direction_id)
            hierarchy['n_plus_2'] = session.get(AgentComplet, direction.directeur_id)
    
    elif "chef" in fonction and "service" in fonction:
        # Chef de service
        hierarchy['position'] = "Chef de service"
        
        # N+1 = Sous-directeur
        if agent.direction_id:
            direction = session.get(Direction, agent.direction_id)
            hierarchy['n_plus_1'] = session.get(AgentComplet, direction.directeur_id)
        
        # N+2 = DAF
        hierarchy['n_plus_2'] = get_daf(session)
    
    elif "sous-directeur" in fonction or "directeur" in fonction:
        # Sous-directeur
        hierarchy['position'] = "Sous-directeur"
        
        # N+1 = DAF
        hierarchy['n_plus_1'] = get_daf(session)
        hierarchy['n_plus_2'] = None
    
    elif "daf" in fonction or fonction == "daf":
        # DAF
        hierarchy['position'] = "DAF"
        hierarchy['n_plus_1'] = None
        hierarchy['n_plus_2'] = None
    
    # RH = Sous-directeur RH (si différent de l'agent)
    rh_direction = session.exec(
        select(Direction).where(Direction.code.ilike("%RH%"))
    ).first()
    
    if rh_direction and rh_direction.directeur_id != agent_id:
        hierarchy['rh'] = session.get(AgentComplet, rh_direction.directeur_id)
    else:
        hierarchy['rh'] = None
    
    # DAF
    hierarchy['daf'] = get_daf(session)
    
    return hierarchy


def get_daf(session):
    """Récupère le DAF (un seul normalement)"""
    daf = session.exec(
        select(AgentComplet).where(AgentComplet.fonction.ilike("%DAF%"))
    ).first()
    return daf
```

---

## ✅ Checklist de validation

### **Tests à effectuer :**

- [ ] **Agent simple** crée une demande de CONGE
  - [ ] Circuit : Agent → Chef → Sous-dir → RH → DAF ✅
  - [ ] Seul le Chef peut valider N+1 ✅
  - [ ] Seul le Sous-dir peut valider N+2 ✅
  - [ ] Seul le RH peut valider RH ✅
  - [ ] Seul le DAF peut valider DAF ✅

- [ ] **Chef de service** crée une demande de CONGE
  - [ ] Circuit : Chef → Sous-dir → RH → DAF ✅
  - [ ] Seul le Sous-dir peut valider N+1 ✅

- [ ] **Sous-directeur RH** crée une demande de CONGE
  - [ ] Circuit : RH → DAF ✅
  - [ ] Seul le DAF peut valider ✅

- [ ] **Agent simple** crée une demande de PERMISSION
  - [ ] Circuit : Agent → Chef → Sous-dir → Archivé ✅
  - [ ] Pas de passage par RH ✅
  - [ ] Pas de passage par DAF ✅

- [ ] **Dashboard filtré**
  - [ ] Agent voit uniquement ses demandes ✅
  - [ ] Chef voit ses demandes + demandes de ses subordonnés ✅
  - [ ] Sous-dir voit demandes de sa direction ✅
  - [ ] RH voit toutes les demandes RH en attente ✅
  - [ ] DAF voit toutes les demandes DAF en attente ✅

- [ ] **Sécurité**
  - [ ] Un agent ne peut pas valider la demande d'un autre ❌
  - [ ] Un N+1 ne peut pas valider une étape N+2 ❌
  - [ ] Message d'erreur clair en cas de tentative non autorisée ✅

---

## 🎓 Points d'attention

### **1. Gestion des cas limites**

- **Agent sans chef de service défini** → Qui est le N+1 ?
  - Solution : Remonter directement au sous-directeur
  
- **Service sans sous-directeur** → Qui est le N+2 ?
  - Solution : Aller directement au DAF (ou RH)

- **Pas de RH défini** → Comment gérer les demandes RH ?
  - Solution : Bloquer la création jusqu'à configuration

### **2. Performance**

- Mettre en cache la hiérarchie d'un agent (éviter requêtes répétées)
- Indexer les champs `fonction`, `service_id`, `direction_id`

### **3. Évolutivité**

- Le système doit pouvoir s'adapter si :
  - On ajoute un niveau hiérarchique (ex: Directeur Général)
  - On change la structure (fusion de services)
  - On personnalise les circuits par type de demande

---

**Prêt à implémenter ?** 🚀

