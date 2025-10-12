# 📋 Tests Fonctionnels

## 🤔 Pourquoi "Fonctionnel" ?

Le mot "**fonctionnel**" vient de "**fonctionnalité**" - une caractéristique complète de l'application du point de vue de l'utilisateur.

### 🏗️ Analogie Simple

Imaginez que vous construisez une maison :

- ⚪ **Test Unitaire** = Vérifier qu'une brique est solide
- ⚪ **Test d'Intégration** = Vérifier que les briques forment un mur
- ✅ **Test Fonctionnel** = Vérifier qu'on peut entrer dans la maison, monter l'escalier, et ouvrir une fenêtre

**Exemples concrets dans notre application :**

| Fonctionnalité | Workflow Complet |
|----------------|------------------|
| Récupération de mot de passe | Oublier → Demander code → Recevoir code → Saisir code → Nouveau mdp → Se connecter |
| Inscription et connexion | S'inscrire → Vérifier email → Se connecter → Accéder au dashboard |
| Gestion de compte | Créer compte → Modifier profil → Désactiver → Réactiver |

---

## 🎯 Objectif des Tests Fonctionnels

### Pour quoi faire ?

1. **Tester des scénarios utilisateur complets**
   - "En tant qu'utilisateur, je veux réinitialiser mon mot de passe"
   - Toutes les étapes du début à la fin
   
2. **Vérifier que les workflows métier fonctionnent**
   - Est-ce qu'un utilisateur peut vraiment se connecter après inscription ?
   - Est-ce que le processus de récupération de mot de passe fonctionne de A à Z ?
   
3. **Simuler des cas d'usage réels**
   - Comme si un vrai utilisateur utilisait l'application

### 📊 Avantages

✅ **Très réaliste** - Teste ce que les utilisateurs font vraiment  
✅ **Détecte les bugs de workflow** - Quand une étape casse l'étape suivante  
✅ **Documentation vivante** - Les tests montrent comment l'app est censée fonctionner  

---

## ⚙️ Comment ça Fonctionne ?

### Principe Simple

```
1. Définir un scénario utilisateur complet
2. Exécuter chaque étape du scénario
3. Vérifier que tout fonctionne de bout en bout
```

### 🎬 Exemple Concret

**Scénario : Utilisateur oublie son mot de passe**

```
GIVEN (Étant donné) : Un utilisateur avec un compte
WHEN (Quand) : 
  1. Il clique sur "Mot de passe oublié"
  2. Il entre son email
  3. Il reçoit un code
  4. Il saisit le code
  5. Il définit un nouveau mot de passe
THEN (Alors) : Il peut se connecter avec le nouveau mot de passe
```

**Code du test :**
```python
@pytest.mark.functional
def test_complete_password_recovery_workflow(client, test_user, session):
    # ÉTAPE 1: Demander la récupération
    response = client.post("/api/v1/forgot-password", 
        data={"email": "test@example.com"})
    assert response.status_code == 303
    
    # ÉTAPE 2: Aller sur la page de vérification
    response = client.get("/api/v1/verify-code?email=test@example.com")
    assert response.status_code == 200
    
    # ÉTAPE 3: Vérifier le code (simulation)
    # Dans un vrai test, on récupérerait le code des logs
    
    # ÉTAPE 4: Définir nouveau mot de passe
    # ... etc.
    
    # ÉTAPE 5: Se connecter avec le nouveau mot de passe
    response = client.post("/api/v1/login", 
        data={"username": "test@example.com", 
              "password": "nouveau_mdp"})
    assert response.status_code == 303  # Connexion réussie !
```

---

## 🚀 Lancer les Tests Fonctionnels

### 📝 Commandes Simples

```bash
# Tous les tests fonctionnels
pytest tests/functional/

# Avec plus de détails
pytest tests/functional/ -v

# Par marqueur
pytest -m functional

# Un workflow spécifique
pytest tests/functional/ -k "password_recovery"
```

### 🎨 Comprendre les Résultats

**✅ Succès**
```
tests/functional/test_password_recovery_workflow.py::
  test_complete_password_recovery_workflow PASSED [100%]

✓ Le workflow complet de récupération de mot de passe fonctionne !
```

**❌ Échec à l'étape 3**
```
FAILED at step 3: Verify code
AssertionError: assert 400 == 200

✗ Le workflow s'arrête à la vérification du code
```

---

## 📂 Fichiers de Tests Fonctionnels

### `test_password_recovery_workflow.py` - Récupération de Mot de Passe

**Workflows testés :**

#### 1️⃣ Workflow Complet de Récupération

```
Utilisateur → Oublie mdp → Demande récupération → 
Reçoit code → Vérifie code → Nouveau mdp → Connexion ✓
```

**Ce qu'on vérifie :**
- ✅ Chaque étape fonctionne
- ✅ Les redirections sont correctes
- ✅ Les données transitent bien entre les étapes

---

#### 2️⃣ Workflow Inscription → Connexion

```
Nouveau user → Crée compte → Vérifie en DB → 
Se connecte → Accède dashboard ✓
```

**Ce qu'on vérifie :**
- ✅ Le compte est bien créé en base
- ✅ L'utilisateur peut se connecter immédiatement
- ✅ Les données sont correctes

**Code :**
```python
def test_user_registration_and_login_workflow(client, session):
    # 1. Créer un compte
    response = client.post("/api/v1/users/", json={
        "email": "nouveau@example.com",
        "full_name": "Nouveau User"
    })
    assert response.status_code == 200
    
    # 2. Vérifier qu'il existe en DB
    user = session.exec(
        select(User).where(User.email == "nouveau@example.com")
    ).first()
    assert user is not None
    
    # 3. Se connecter (si le mot de passe était disponible)
    # ...
```

---

#### 3️⃣ Workflow Désactivation de Compte

```
User actif → Se connecte ✓ → Admin désactive → 
Tentative connexion ✗ → Admin réactive → Connexion ✓
```

**Ce qu'on vérifie :**
- ✅ Un user actif peut se connecter
- ✅ Un user désactivé ne peut PAS se connecter
- ✅ Réactiver le compte permet de se reconnecter

**Pourquoi c'est important :**  
Vérifie que la gestion des comptes (actif/inactif) fonctionne sur tout le parcours.

---

## 💡 Conseils pour Comprendre

### 🔍 Différence avec les autres tests

| Aspect | Unitaire | Intégration | Fonctionnel |
|--------|----------|-------------|-------------|
| **Portée** | 1 fonction | 1 endpoint | Plusieurs endpoints |
| **Étapes** | 1 | 1 | Plusieurs (3-10) |
| **Durée** | 5ms | 50ms | 200ms+ |
| **Exemple** | Hasher un mdp | POST /login | Workflow complet |
| **Point de vue** | Développeur | API | Utilisateur |

### 🎯 Quand un test fonctionnel échoue

Si un test fonctionnel échoue, posez-vous ces questions :

1. **À quelle étape ça échoue ?**
   ```
   FAILED at step 3: Verify code
   → Le problème est à la vérification du code
   ```

2. **Est-ce qu'une étape précédente a mal fonctionné ?**
   ```
   Étape 1 ✓ → Étape 2 ✓ → Étape 3 ✗
   → Vérifier les données passées de l'étape 2 à 3
   ```

3. **Est-ce un problème d'intégration ou de logique métier ?**
   - Intégration : L'API ne répond pas
   - Métier : La logique du workflow est cassée

### 📖 Structure d'un Test Fonctionnel

Tous nos tests fonctionnels suivent ce pattern :

```python
@pytest.mark.functional
def test_nom_du_workflow(client, fixtures_nécessaires):
    """
    Description du scénario utilisateur
    
    Scenario:
    1. Étape 1
    2. Étape 2
    3. Étape 3
    """
    
    # Étape 1: Action
    response1 = ...
    assert ...  # Vérification
    
    # Étape 2: Action
    response2 = ...
    assert ...  # Vérification
    
    # Étape 3: Action finale
    response3 = ...
    assert ...  # Vérification finale
```

---

## 🆘 Problèmes Courants

### Test qui échoue au milieu du workflow

```
✓ Étape 1: Demande récupération - OK
✓ Étape 2: Page de vérification - OK
✗ Étape 3: Vérifier le code - FAILED
```

**Causes possibles :**
1. ❌ Le code n'a pas été généré à l'étape 1
2. ❌ Le code a expiré
3. ❌ Les données ne transitent pas entre étapes

**Solution :**
```bash
# Lancer avec logs détaillés
pytest tests/functional/ -vvs --log-cli-level=DEBUG
```

### Tous les tests fonctionnels sont lents

**C'est normal !** Les tests fonctionnels sont naturellement plus lents car :
- Plusieurs étapes
- Plusieurs requêtes HTTP
- Plusieurs opérations en base

**Optimisations possibles :**
- Lancer les tests fonctionnels moins souvent
- Les lancer en parallèle (`pytest -n auto`)
- Les regrouper dans un build CI/CD séparé

---

## 📊 Statistiques Actuelles

| Workflow | Étapes | Temps | Complexité |
|----------|--------|-------|------------|
| Récupération mot de passe | 2 étapes | ~100ms | 🟡 Moyenne |
| Inscription + Connexion | 3 étapes | ~80ms | 🟢 Simple |
| Désactivation compte | 6 étapes | ~150ms | 🔴 Complexe |

**Total : 3 workflows testés** 📋

---

## 🎓 Pour Aller Plus Loin

### Questions Fréquentes

**Q: Pourquoi il y a moins de tests fonctionnels ?**  
R: Ils sont plus longs et couvrent beaucoup de code. Quelques tests bien choisis suffisent.

**Q: Faut-il tester tous les workflows possibles ?**  
R: Non ! Concentrez-vous sur les **parcours critiques** :
- Inscription / Connexion
- Paiement (si applicable)
- Récupération de mot de passe
- Workflows métier principaux

**Q: Quelle est la différence avec les tests E2E ?**  
R: 
- **Fonctionnel** : Teste l'API (backend)
- **E2E** : Teste avec un vrai navigateur (frontend + backend)

### Pyramide de Tests (rappel)

```
      /\      E2E
     /  \     - 5% des tests
    /----\    Functional  
   /      \   - 15% des tests
  /--------\  Integration
 /          \ - 30% des tests
/____________\ Unit
               - 50% des tests
```

### User Stories Format

Nos tests fonctionnels suivent le format **Given-When-Then** :

```
GIVEN (Étant donné) : État initial
WHEN (Quand) : Actions de l'utilisateur
THEN (Alors) : Résultat attendu
```

**Exemple :**
```
GIVEN : Un utilisateur avec un compte actif
WHEN : L'admin désactive le compte
  AND : L'utilisateur tente de se connecter
THEN : La connexion est refusée
  AND : Un message explicatif est affiché
```

---

## ✨ En Résumé

| Aspect | Explication Simple |
|--------|-------------------|
| **Nom** | "Fonctionnel" = tester une fonctionnalité complète |
| **Objectif** | Vérifier qu'un workflow utilisateur fonctionne |
| **Vitesse** | 🟡 Moyen (~100-200ms) |
| **Quand** | Avant chaque release majeure |
| **Commande** | `pytest tests/functional/` ou `pytest -m functional` |

**💡 Pensez aux tests fonctionnels comme des "histoires utilisateur automatisées" - on vérifie qu'un utilisateur peut accomplir une tâche de A à Z !**

---

## 🚦 Prochaines Étapes

Pour améliorer nos tests fonctionnels :

1. **Compléter le workflow de récupération de mot de passe**
   - Ajouter un mock du système d'email
   - Récupérer le code depuis les logs
   - Tester le changement réel du mot de passe

2. **Ajouter plus de workflows**
   - Modification de profil
   - Changement de mot de passe (connecté)
   - Gestion de sessions

3. **Documenter les parcours critiques**
   - Identifier les 5 workflows les plus importants
   - Créer des tests pour chacun

