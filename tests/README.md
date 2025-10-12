# 🧪 Tests MPPEEP Dashboard

> **Guide Complet des Tests** - De l'utilisateur non-tech au développeur expert

---

## 📚 Table des Matières

1. [Vue d'ensemble](#-vue-densemble)
2. [Structure des tests](#-structure-des-tests)
3. [Démarrage rapide](#-démarrage-rapide)
4. [Types de tests](#-types-de-tests)
5. [Commandes principales](#-commandes-principales)
6. [Pyramide de tests](#-pyramide-de-tests)
7. [Pour aller plus loin](#-pour-aller-plus-loin)

---

## 🎯 Vue d'ensemble

### Pourquoi des tests ?

Les tests automatisés sont comme des **gardiens de votre code** :
- 🛡️ Ils vérifient que tout fonctionne
- 🐛 Ils détectent les bugs avant les utilisateurs
- 📖 Ils documentent comment l'application fonctionne
- 🚀 Ils donnent confiance pour faire des changements

### 3 Niveaux de Tests

```
🔬 UNITAIRE      = Tester une brique LEGO seule
🔗 INTÉGRATION   = Tester plusieurs briques assemblées
📋 FONCTIONNEL   = Tester une construction complète
🌐 E2E (futur)   = Tester avec de vrais utilisateurs
```

---

## 📁 Structure des Tests

```
tests/
├── 📄 README.md                 ← Vous êtes ici !
├── 📄 conftest.py               ← Configuration pytest
│
├── 📂 unit/                     ← 🔬 Tests Unitaires (29 tests)
│   ├── 📘 README.md             ← Guide détaillé unitaire
│   ├── test_config.py           ← Configuration (8 tests)
│   ├── test_security.py         ← Sécurité (8 tests)
│   ├── test_models.py           ← Modèles (5 tests)
│   └── test_database_init.py    ← Init DB (8 tests) ⭐ Nouveau
│
├── 📂 integration/              ← 🔗 Tests d'Intégration (23 tests)
│   ├── 📗 README.md             ← Guide détaillé intégration
│   ├── test_auth_api.py         ← API authentification (8 tests)
│   ├── test_users_api.py        ← API utilisateurs (5 tests)
│   ├── test_health.py           ← Health checks (3 tests)
│   └── test_database_initialization.py  ← Init DB complète (7 tests) ⭐ Nouveau
│
├── 📂 functional/               ← 📋 Tests Fonctionnels (8 tests)
│   ├── 📙 README.md             ← Guide détaillé fonctionnel
│   ├── test_password_recovery_workflow.py  ← Récupération password (3 tests)
│   └── test_database_init_workflow.py      ← Workflows init DB (5 tests) ⭐ Nouveau
│
├── 📂 e2e/                      ← 🌐 Tests E2E (futur)
│   └── 📕 README.md             ← Guide détaillé E2E
│
├── 📄 AUTOMATION.md             ← Guide automatisation pytest ⭐ Nouveau
└── 📄 DATABASE_TESTS.md         ← Documentation tests DB ⭐ Nouveau
```

**Total actuel : 60 tests automatisés** ✅ (+20 nouveaux tests)

---

## 🚀 Démarrage Rapide

### Prérequis

```bash
# 1. Être dans le bon dossier
cd mppeep

# 2. Avoir les dépendances installées
uv sync
```

### Lancer TOUS les tests

```bash
pytest
```

**Résultat attendu :**
```
=================== 40 passed in 2.5s ===================
✅ Tous les tests passent !
```

### Lancer par type

```bash
# Tests rapides seulement (unitaires)
pytest tests/unit/

# Tests d'API (intégration)
pytest tests/integration/

# Tests de workflows (fonctionnels)
pytest tests/functional/
```

### En cas d'erreur

```bash
# Voir plus de détails
pytest -v

# Voir BEAUCOUP plus de détails
pytest -vvs

# Arrêter au premier échec
pytest -x
```

---

## 📊 Types de Tests

### 🎯 Tableau Comparatif

| Type | Vitesse | Quantité | Quand lancer | Documentation |
|------|---------|----------|--------------|---------------|
| **🔬 Unitaire** | ⚡⚡⚡ 5ms | 21 tests | À chaque modification | [unit/README.md](unit/README.md) |
| **🔗 Intégration** | ⚡⚡ 50ms | 16 tests | Avant de commit | [integration/README.md](integration/README.md) |
| **📋 Fonctionnel** | ⚡ 200ms | 3 tests | Avant une release | [functional/README.md](functional/README.md) |
| **🌐 E2E** | 🐌 5-30s | 0 (futur) | Avant production | [e2e/README.md](e2e/README.md) |

### 🔬 Tests Unitaires

**C'est quoi ?** Tester une fonction isolée

**Exemple :** Vérifier que `get_password_hash("password")` ne retourne PAS "password"

**Lancer :**
```bash
pytest tests/unit/
```

**📘 [Voir le guide complet](unit/README.md)**

---

### 🔗 Tests d'Intégration

**C'est quoi ?** Tester l'API avec la base de données

**Exemple :** Envoyer `POST /api/v1/login` et vérifier la redirection

**Lancer :**
```bash
pytest tests/integration/
```

**📗 [Voir le guide complet](integration/README.md)**

---

### 📋 Tests Fonctionnels

**C'est quoi ?** Tester un workflow complet utilisateur

**Exemple :** Oublier mdp → Demander code → Vérifier → Nouveau mdp → Login

**Lancer :**
```bash
pytest tests/functional/
```

**📙 [Voir le guide complet](functional/README.md)**

---

### 🌐 Tests E2E (End-to-End)

**C'est quoi ?** Tester avec un vrai navigateur (Chrome, Firefox)

**Statut :** 🔜 À implémenter plus tard

**📕 [Voir le guide complet](e2e/README.md)**

---

## 🎮 Commandes Principales

### Par Type de Test

```bash
# Tests unitaires (rapides)
pytest tests/unit/ -v

# Tests d'intégration (API)
pytest tests/integration/ -v

# Tests fonctionnels (workflows)
pytest tests/functional/ -v

# Tous les tests
pytest
```

### Par Fichier

```bash
# Un fichier spécifique
pytest tests/unit/test_security.py

# Une fonction spécifique
pytest tests/unit/test_security.py::test_password_hashing
```

### Par Mot-Clé

```bash
# Tous les tests avec "login"
pytest -k "login"

# Tous les tests avec "password"
pytest -k "password"

# Tous les tests SAUF "slow"
pytest -k "not slow"
```

### Par Marqueur

```bash
# Tests unitaires seulement
pytest -m unit

# Tests d'intégration seulement
pytest -m integration

# Tests fonctionnels seulement
pytest -m functional

# Combinaison
pytest -m "unit or integration"
```

### Options Utiles

```bash
# Verbose (détaillé)
pytest -v

# Très verbose
pytest -vv

# Avec les prints
pytest -s

# Arrêter au premier échec
pytest -x

# Couverture de code
pytest --cov=app --cov-report=html
```

---

## 🏔️ Pyramide de Tests

Notre répartition suit la **pyramide de tests** :

```
          /\
         /  \      🌐 E2E (0 tests - futur)
        /    \     Lent, fragile, coûteux
       /------\    
      /        \   📋 FUNCTIONAL (3 tests)
     /          \  Workflows complets
    /------------\ 
   /              \ 🔗 INTEGRATION (16 tests)
  /                \ Endpoints API + DB
 /------------------\
/____________________\ 🔬 UNIT (21 tests)
                       Rapide, fiable, nombreux
```

### Répartition Actuelle

| Type | Tests | Pourcentage | Objectif |
|------|-------|-------------|----------|
| Unitaire | 21 | 52.5% | ✅ 50-70% |
| Intégration | 16 | 40% | ✅ 20-30% |
| Fonctionnel | 3 | 7.5% | ✅ 10-20% |
| E2E | 0 | 0% | 🔜 5-10% |

**Notre pyramide est équilibrée !** ✅

---

## 🔧 Configuration Pytest

### Fichier `pytest.ini`

```ini
[pytest]
testpaths = tests          # Où chercher les tests
python_files = test_*.py   # Pattern des fichiers
addopts = -v -ra          # Options par défaut
```

### Marqueurs Disponibles

```python
@pytest.mark.unit          # Test unitaire
@pytest.mark.integration   # Test d'intégration
@pytest.mark.functional    # Test fonctionnel
@pytest.mark.slow          # Test lent
@pytest.mark.auth          # Lié à l'authentification
@pytest.mark.database      # Nécessite une DB
```

---

## 🛠️ Fixtures Pytest

Les fixtures sont des **données/objets pré-configurés** pour vos tests.

### Fixtures Disponibles (dans `conftest.py`)

#### `session`
```python
def test_with_database(session: Session):
    user = User(email="test@test.com")
    session.add(user)
    session.commit()
```

**Usage :** Tests nécessitant une base de données

---

#### `client`
```python
def test_api_endpoint(client: TestClient):
    response = client.get("/api/v1/ping")
    assert response.status_code == 200
```

**Usage :** Tests d'API (intégration)

---

#### `test_user`
```python
def test_with_user(test_user: User):
    assert test_user.email == "test@example.com"
```

**Données :**
- Email: `test@example.com`
- Password: `testpassword123`
- Active: `True`

**Usage :** Tests nécessitant un utilisateur standard

---

#### `admin_user`
```python
def test_admin_feature(admin_user: User):
    assert admin_user.is_superuser is True
```

**Données :**
- Email: `admin@example.com`
- Password: `admin123`
- Superuser: `True`

**Usage :** Tests nécessitant un administrateur

---

## 📊 Couverture de Code

### Générer un Rapport

```bash
# Rapport dans le terminal
pytest --cov=app

# Rapport HTML détaillé
pytest --cov=app --cov-report=html

# Ouvrir le rapport
# Windows
start htmlcov/index.html

# Mac
open htmlcov/index.html

# Linux
xdg-open htmlcov/index.html
```

### Objectifs de Couverture

| Module | Objectif | Actuel |
|--------|----------|--------|
| `app/core/` | > 90% | 🎯 À mesurer |
| `app/models/` | > 90% | 🎯 À mesurer |
| `app/api/` | > 80% | 🎯 À mesurer |
| **Global** | **> 80%** | 🎯 À mesurer |

---

## 🆘 Dépannage

### Les tests échouent après `git pull`

```bash
# 1. Mettre à jour les dépendances
uv sync

# 2. Relancer les tests
pytest
```

### Un test échoue de manière aléatoire

```bash
# Lancer plusieurs fois pour confirmer
pytest tests/path/to/test.py --count=10
```

**Si ça échoue aléatoirement → Test "flaky"** (à corriger)

### Voir pourquoi un test échoue

```bash
# Maximum de détails
pytest tests/path/to/test.py -vvs --tb=long

# Entrer en mode debug
pytest tests/path/to/test.py --pdb
```

### Tests trop lents

```bash
# Identifier les tests lents
pytest --durations=10

# Lancer en parallèle (nécessite pytest-xdist)
pytest -n auto
```

---

## 📈 Statistiques Actuelles

### Par Type

```
🔬 Tests Unitaires      : 21 tests (~0.5s total)
🔗 Tests d'Intégration  : 16 tests (~0.8s total)
📋 Tests Fonctionnels   : 3 tests  (~0.6s total)
─────────────────────────────────────────────────
📊 TOTAL               : 40 tests (~1.9s total)
```

### Par Module

```
Configuration  : 8 tests  ✅
Sécurité      : 8 tests  ✅
Modèles       : 5 tests  ✅
Auth API      : 8 tests  ✅
Users API     : 5 tests  ✅
Health        : 3 tests  ✅
Workflows     : 3 tests  ✅
```

---

## ✅ Bonnes Pratiques

### DO (À Faire)

✅ **Lancer les tests avant de commit**
```bash
git add .
pytest  # ← Toujours !
git commit -m "..."
```

✅ **Écrire des tests pour les nouveaux endpoints**
```python
# Nouveau endpoint créé ? → Nouveau test !
```

✅ **Nommer les tests de manière descriptive**
```python
# ✅ Bon
def test_login_with_wrong_password_returns_error():
    ...

# ❌ Mauvais
def test_login():
    ...
```

✅ **Suivre le pattern AAA**
```python
def test_something():
    # ARRANGE - Préparer
    data = {"email": "test@test.com"}
    
    # ACT - Agir
    result = function(data)
    
    # ASSERT - Vérifier
    assert result == expected
```

---

### DON'T (À Éviter)

❌ **Tests dépendant d'un ordre**
```python
# ❌ test_2 dépend de test_1
def test_1():
    create_user()
    
def test_2():  # ← Cassé si test_1 n'a pas run
    login_user()
```

❌ **Tests avec sleep()**
```python
# ❌ Mauvais
time.sleep(2)  # Lent et fragile

# ✅ Bon
wait_for_condition(lambda: user.is_ready)
```

❌ **Ignorer les tests qui échouent**
```python
# ❌ JAMAIS faire ça !
@pytest.mark.skip("TODO: fix later")
def test_important_feature():
    ...
```

---

## 🎓 Pour Aller Plus Loin

### 📖 Documentation Détaillée

Chaque type de test a son **guide complet** :

- 🔬 [Tests Unitaires](unit/README.md) - Guide pour non-techs
- 🔗 [Tests d'Intégration](integration/README.md) - Guide API
- 📋 [Tests Fonctionnels](functional/README.md) - Guide workflows
- 🌐 [Tests E2E](e2e/README.md) - Guide navigateur (futur)

### 🎥 Tutoriels Recommandés

- [Pytest Tutorial (English)](https://www.youtube.com/results?search_query=pytest+tutorial)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Test Pyramid Explained](https://martinfowler.com/articles/practical-test-pyramid.html)

### 📚 Ressources

- [Documentation Pytest](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLModel Testing](https://sqlmodel.tiangolo.com/tutorial/fastapi/tests/)
- [Test Best Practices](https://testdriven.io/blog/testing-best-practices/)

---

## 🎯 Roadmap Tests

### ✅ Déjà Fait

- [x] Structure des tests par type
- [x] 21 tests unitaires
- [x] 16 tests d'intégration
- [x] 3 tests fonctionnels
- [x] Documentation complète
- [x] Fixtures pytest
- [x] Configuration pytest.ini

### 🔜 Prochaines Étapes

- [ ] Atteindre 80% de couverture de code
- [ ] Ajouter tests pour nouveaux endpoints
- [ ] Compléter les workflows fonctionnels
- [ ] Implémenter tests E2E (Playwright)
- [ ] Intégration CI/CD (GitHub Actions)
- [ ] Tests de performance
- [ ] Tests de sécurité (OWASP)

---

## 💡 Conseils Finaux

### Pour les Développeurs

1. **Testez d'abord** (TDD) - Écrivez le test avant le code
2. **Gardez les tests rapides** - Un test lent = un test ignoré
3. **Tests isolés** - Chaque test doit pouvoir run seul
4. **Couverture > 80%** - Objectif minimum

### Pour les Non-Techs

1. **Les tests = Assurance qualité automatique**
2. **Vert = Tout va bien, Rouge = Problème à corriger**
3. **Plus de tests = Plus de confiance**
4. **Lire les tests = Comprendre l'application**

---

## 🚀 Commande du Jour

```bash
# Lancer tous les tests avec détails et couverture
pytest -v --cov=app --cov-report=term-missing

# Voir le rapport dans le navigateur
pytest --cov=app --cov-report=html && start htmlcov/index.html
```

---

## 📞 Besoin d'Aide ?

- 📖 Lire les guides spécifiques dans chaque sous-dossier
- 🐛 Voir la section [Dépannage](#-dépannage)
- 💬 Demander à l'équipe
- 📚 Consulter la [documentation Pytest](https://docs.pytest.org/)

---

**🎉 Bon testing !**

*Dernière mise à jour : Structure organisée par types de tests*
