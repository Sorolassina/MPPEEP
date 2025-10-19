# 👤 Guide d'Attribution des Rôles Personnalisés

## 📋 Vue d'Ensemble

Ce guide explique comment attribuer un **rôle personnalisé** à un agent dans le système MPPEEP.

Les rôles personnalisés permettent de désigner des validateurs spécifiques pour certains types de demandes, indépendamment de la hiérarchie organisationnelle.

---

## 🎯 Pourquoi attribuer un rôle ?

### **Exemples de cas d'usage :**

| Rôle | Utilité | Exemple |
|------|---------|---------|
| `RESP_BUDGET` | Responsable Budget | Valide toutes les demandes budgétaires |
| `RESP_IT` | Responsable Informatique | Valide les demandes de matériel IT |
| `RESP_LOGISTIQUE` | Responsable Logistique | Valide les demandes de fournitures |
| `COMITE_VALIDATION` | Membre du comité | Validation collégiale de demandes sensibles |

---

## 🚀 Méthode 1 : Via l'Interface Web (Recommandé)

### **Étape 1 : Accéder à la Configuration**

```
1. Se connecter en tant qu'ADMIN
2. Aller sur : http://localhost:8000/api/v1/admin/workflow-config
3. Cliquer sur l'onglet "👥 Rôles Personnalisés"
```

### **Étape 2 : Créer le Rôle (si pas encore créé)**

```
1. Cliquer sur "➕ Créer un Rôle"
2. Remplir le formulaire :
   - Code : RESP_BUDGET (en majuscules, sans espaces)
   - Libellé : Responsable Budget
   - Description : Valide toutes les demandes budgétaires
3. Cliquer "Enregistrer"
```

### **Étape 3 : Attribuer le Rôle à un Agent**

```
1. Trouver le rôle dans la liste
2. Cliquer sur "👤 Attribuer à un agent"
3. Dans le modal qui s'ouvre :
   - Le rôle est pré-rempli
   - Sélectionner l'agent dans la liste déroulante
   - (Optionnel) Définir une date de fin
4. Cliquer "Attribuer"
5. ✅ Confirmation : "Rôle attribué avec succès !"
```

### **Capture d'écran du processus**

```
┌─────────────────────────────────────────────────────────┐
│ 👥 Rôles Personnalisés                                   │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────┐            │
│  │ Responsable Budget                       │            │
│  │ Badge: RESP_BUDGET                       │            │
│  │ Description: Valide les demandes budget  │            │
│  │                                           │            │
│  │ [👤 Attribuer] [✏️ Éditer] [🔴 Suppr.]  │  ← Clic ici
│  └─────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────┘

                      ↓ Clic sur "Attribuer"

┌─────────────────────────────────────────────────────────┐
│ 👤 Attribuer un Rôle à un Agent                         │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  Rôle *                                                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Responsable Budget (RESP_BUDGET)  [lecture seule]│    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  Agent *                                                 │
│  ┌─────────────────────────────────────────────────┐    │
│  │ ▼ Jean KOUASSI - Agent Budget               │    │  ← Choisir
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  Date de fin (optionnelle)                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │ [___/___/____]                                   │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│             [Annuler]  [Attribuer]                       │
└─────────────────────────────────────────────────────────┘
```

---

## 💻 Méthode 2 : Via l'API REST

### **Endpoint**

```http
POST /api/v1/admin/workflow-config/api/custom-roles/{role_id}/assign
Content-Type: application/json
Authorization: Bearer <token>

{
    "agent_id": 15,
    "date_fin": "2025-12-31"  // Optionnel
}
```

### **Exemple avec curl**

```bash
# 1. Récupérer l'ID du rôle
curl -X GET "http://localhost:8000/api/v1/admin/workflow-config/api/custom-roles"

# 2. Attribuer le rôle (supposons role_id = 1)
curl -X POST "http://localhost:8000/api/v1/admin/workflow-config/api/custom-roles/1/assign" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "agent_id": 15,
    "date_fin": null
  }'
```

### **Réponse**

```json
{
  "ok": true,
  "assignment_id": 42,
  "message": "Rôle attribué avec succès"
}
```

---

## 🐍 Méthode 3 : Via Python/Script

### **Script Simple**

Créer un fichier `scripts/assign_role_custom.py` :

```python
"""
Script pour attribuer un rôle personnalisé à un agent
Usage: python scripts/assign_role_custom.py
"""
from sqlmodel import Session, select
from app.db.session import engine
from app.services.workflow_config_service import WorkflowConfigService
from app.models.workflow_config import CustomRole
from app.models.personnel import AgentComplet

def main():
    with Session(engine) as session:
        # Configuration
        ROLE_CODE = "RESP_BUDGET"  # À modifier
        AGENT_ID = 15  # À modifier
        
        # 1. Récupérer le rôle
        role = session.exec(
            select(CustomRole)
            .where(CustomRole.code == ROLE_CODE)
            .where(CustomRole.actif == True)
        ).first()
        
        if not role:
            print(f"❌ Rôle '{ROLE_CODE}' introuvable")
            print("\nRôles disponibles :")
            roles = session.exec(select(CustomRole).where(CustomRole.actif == True)).all()
            for r in roles:
                print(f"  - {r.code} : {r.libelle}")
            return
        
        # 2. Récupérer l'agent
        agent = session.get(AgentComplet, AGENT_ID)
        if not agent:
            print(f"❌ Agent avec ID {AGENT_ID} introuvable")
            return
        
        # 3. Attribuer le rôle
        try:
            assignment = WorkflowConfigService.assign_role_to_agent(
                session=session,
                custom_role_id=role.id,
                agent_id=agent.id,
                date_fin=None,  # Attribution permanente
                user_id=1  # ID de l'admin
            )
            
            print("✅ Attribution réussie !")
            print(f"   Rôle : {role.libelle} ({role.code})")
            print(f"   Agent : {agent.prenom} {agent.nom}")
            print(f"   Fonction : {agent.fonction or 'Non définie'}")
            print(f"   Assignment ID : {assignment.id}")
            
        except ValueError as e:
            print(f"❌ Erreur : {str(e)}")
        except Exception as e:
            print(f"❌ Erreur inattendue : {str(e)}")

if __name__ == "__main__":
    main()
```

### **Exécution**

```bash
python scripts/assign_role_custom.py
```

### **Résultat attendu**

```
✅ Attribution réussie !
   Rôle : Responsable Budget (RESP_BUDGET)
   Agent : Jean KOUASSI
   Fonction : Agent Budget
   Assignment ID : 42
```

---

## 🔍 Vérifier les Attributions

### **Via l'API**

```bash
# Récupérer tous les agents avec un rôle spécifique
curl -X GET "http://localhost:8000/api/v1/admin/workflow-config/api/custom-roles/1/agents"
```

### **Via Python**

```python
from sqlmodel import Session, select
from app.db.session import engine
from app.models.workflow_config import CustomRoleAssignment, CustomRole
from app.models.personnel import AgentComplet

with Session(engine) as session:
    # Récupérer toutes les attributions actives
    assignments = session.exec(
        select(CustomRoleAssignment)
        .where(CustomRoleAssignment.actif == True)
    ).all()
    
    print("📋 Attributions de rôles actives :")
    for assign in assignments:
        role = session.get(CustomRole, assign.custom_role_id)
        agent = session.get(AgentComplet, assign.agent_id)
        print(f"  - {agent.prenom} {agent.nom} → {role.libelle}")
```

---

## ⚙️ Utilisation du Rôle dans un Workflow

### **Étape 1 : Créer un Template avec Rôle Personnalisé**

```
1. Aller sur : Configuration Workflows → Onglet "Templates"
2. Créer un nouveau template
3. Ajouter une étape avec :
   - Type de rôle : CUSTOM
   - Nom du rôle : RESP_BUDGET
```

### **Étape 2 : Créer un Type de Demande**

```
1. Onglet "Types de Demandes"
2. Créer "DEMANDE_BUDGET_EXCEPTIONNEL"
3. Associer au template créé à l'étape 1
```

### **Étape 3 : Tester**

```
1. Un agent fait une demande de type DEMANDE_BUDGET_EXCEPTIONNEL
2. La demande arrive automatiquement à Jean (qui a le rôle RESP_BUDGET)
3. Jean valide → suit le reste du circuit
```

---

## 🎓 Cas d'Usage Avancés

### **Cas 1 : Rôle Temporaire (Intérim)**

```python
# Attribution avec date de fin
WorkflowConfigService.assign_role_to_agent(
    session=session,
    custom_role_id=role.id,
    agent_id=agent.id,
    date_fin=datetime(2025, 12, 31),  # Fin de l'intérim
    user_id=admin_id
)
```

### **Cas 2 : Plusieurs Agents avec le Même Rôle**

```python
# Attribuer le même rôle à plusieurs agents (comité)
membres_comite = [15, 23, 45]

for agent_id in membres_comite:
    WorkflowConfigService.assign_role_to_agent(
        session=session,
        custom_role_id=role_comite.id,
        agent_id=agent_id,
        user_id=admin_id
    )
```

### **Cas 3 : Révoquer une Attribution**

```python
from app.models.workflow_config import CustomRoleAssignment

# Désactiver l'attribution
assignment = session.get(CustomRoleAssignment, assignment_id)
if assignment:
    assignment.actif = False
    session.add(assignment)
    session.commit()
```

---

## 📊 Résumé

| Méthode | Difficulté | Cas d'usage |
|---------|------------|-------------|
| **Interface Web** | ⭐ Facile | Usage quotidien, administrateurs |
| **API REST** | ⭐⭐ Moyen | Intégrations, automatisations |
| **Script Python** | ⭐⭐⭐ Avancé | Migrations, attributions en masse |

---

## 🎯 Checklist Complète

- [ ] **1. Créer le rôle personnalisé**
  - Code : `RESP_BUDGET`
  - Libellé : `Responsable Budget`
  
- [ ] **2. Attribuer le rôle à un agent**
  - Via l'interface : Clic "👤 Attribuer à un agent"
  - Choisir l'agent : Jean KOUASSI
  
- [ ] **3. Créer un template utilisant ce rôle**
  - Étape 1 : CUSTOM (RESP_BUDGET)
  - Étape 2 : DAF
  
- [ ] **4. Créer un type de demande**
  - Code : `DEMANDE_BUDGET`
  - Template : Circuit Budget
  
- [ ] **5. Tester**
  - Créer une demande de type DEMANDE_BUDGET
  - Vérifier que Jean reçoit la demande
  - Valider le circuit complet

---

## 🚨 Erreurs Courantes

### **Erreur : "Agent a déjà ce rôle"**

**Cause :** L'agent a déjà une attribution active de ce rôle.

**Solution :**
```python
# Désactiver l'ancienne attribution d'abord
old_assignment = session.exec(
    select(CustomRoleAssignment)
    .where(CustomRoleAssignment.custom_role_id == role_id)
    .where(CustomRoleAssignment.agent_id == agent_id)
    .where(CustomRoleAssignment.actif == True)
).first()

if old_assignment:
    old_assignment.actif = False
    session.add(old_assignment)
    session.commit()
```

### **Erreur : "Rôle introuvable"**

**Cause :** Le code du rôle est incorrect ou le rôle est désactivé.

**Solution :** Vérifier que le rôle existe et est actif :
```python
roles = session.exec(select(CustomRole).where(CustomRole.actif == True)).all()
for role in roles:
    print(f"{role.code} : {role.libelle}")
```

### **Erreur : "Agent introuvable"**

**Cause :** L'ID de l'agent est incorrect.

**Solution :** Lister les agents disponibles :
```python
agents = session.exec(select(AgentComplet)).all()
for agent in agents:
    print(f"{agent.id} : {agent.prenom} {agent.nom}")
```

---

## 📞 Support

Pour toute question ou problème :

1. Vérifier ce guide
2. Consulter la documentation : `WORKFLOW_IMPLEMENTATION_FINALE.md`
3. Consulter les logs : `logs/app.log`
4. Tester via l'interface web d'abord (plus simple)

---

**Dernière mise à jour :** 19 octobre 2025  
**Version :** 1.0  
**Auteur :** Système MPPEEP

