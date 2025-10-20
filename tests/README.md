# 🧪 Tests MPPEEP Dashboard - CI/CD

## 🎯 Vue d'ensemble

Cette suite de tests contient **uniquement les tests critiques** exécutés automatiquement en CI/CD à chaque push sur GitHub.

---

## 🚀 Exécution Rapide

```bash
# Tous les tests critiques
pytest -m critical

# Avec couverture
pytest -m critical --cov=app --cov-report=term

# Verbose
pytest -m critical -v

# Arrêt au premier échec
pytest -m critical -x
```

---

## 📂 Structure

```
tests/
├── conftest.py              # Configuration pytest
├── unit/                    # Tests unitaires
│   ├── test_config.py       # Configuration
│   ├── test_security.py     # Sécurité (JWT, bcrypt)
│   └── test_models.py       # Validation des modèles
├── integration/             # Tests d'intégration
│   ├── test_database_initialization.py  # Initialisation DB
│   ├── test_auth_api.py                 # API authentification
│   └── test_health.py                   # Health check
└── README.md                # Ce fichier
```

---

## ✅ Tests Critiques

### 1. Configuration (test_config.py)
- ✅ Variables d'environnement chargées
- ✅ SECRET_KEY définie et suffisamment longue
- ✅ DATABASE_URL valide

### 2. Sécurité (test_security.py)
- ✅ Hachage bcrypt fonctionne
- ✅ Vérification de mot de passe
- ✅ Création de JWT valide
- ✅ Décodage de JWT
- ✅ Expiration de token

### 3. Modèles (test_models.py)
- ✅ User : Création et validation
- ✅ Agent : Création et relations
- ✅ HRRequest : Création et workflow
- ✅ Article : Création avec périssable/amortissable

### 4. Initialisation DB (test_database_initialization.py)
- ✅ Toutes les tables créées
- ✅ Contraintes de clés étrangères
- ✅ Index créés
- ✅ Pas de doublons

### 5. API Authentification (test_auth_api.py)
- ✅ GET /api/v1/auth/login accessible
- ✅ POST /api/v1/auth/login avec credentials valides
- ✅ POST /api/v1/auth/login avec credentials invalides
- ✅ Cookie access_token créé
- ✅ JWT valide

### 6. Health Check (test_health.py)
- ✅ Application démarre
- ✅ Base de données accessible
- ✅ Routes enregistrées

---

## 🏷️ Marqueurs pytest

Les tests critiques sont marqués avec `@pytest.mark.critical` :

```python
import pytest

@pytest.mark.critical
def test_database_tables_created(db_session):
    """Test critique : Vérifier que toutes les tables sont créées"""
    # ...
```

### Exécution par marqueur

```bash
# Tests critiques uniquement (CI/CD)
pytest -m critical

# Tests unitaires
pytest -m unit

# Tests d'intégration
pytest -m integration

# Tous les tests
pytest
```

---

## 📊 Couverture de Code

### Objectifs

- **Global** : 80% minimum
- **Critique** : 100% (auth, security, models)
- **Services** : 90% minimum
- **API** : 85% minimum

### Générer un rapport

```bash
# Rapport dans le terminal
pytest --cov=app --cov-report=term-missing

# Rapport HTML
pytest --cov=app --cov-report=html

# Ouvrir le rapport
start htmlcov/index.html  # Windows
open htmlcov/index.html   # Mac
xdg-open htmlcov/index.html  # Linux
```

---

## 🔄 CI/CD GitHub Actions

### Workflow automatique

```yaml
# .github/workflows/tests.yml
name: Tests CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run critical tests
      run: pytest -m critical --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Badges

Ajouter au README principal :

```markdown
[![Tests](https://github.com/votre-org/mppeep-dashboard/workflows/Tests%20CI/CD/badge.svg)](https://github.com/votre-org/mppeep-dashboard/actions)
[![Coverage](https://codecov.io/gh/votre-org/mppeep-dashboard/branch/main/graph/badge.svg)](https://codecov.io/gh/votre-org/mppeep-dashboard)
```

---

## 🐛 Debugging des Tests

### Test qui échoue

```bash
# Mode verbose
pytest -v test_auth_api.py::test_login_valid

# Afficher les prints
pytest -s test_auth_api.py

# Arrêter au premier échec
pytest -x

# Debugger avec pdb
pytest --pdb test_auth_api.py
```

### Fixtures

Les fixtures sont définies dans `conftest.py` :

```python
@pytest.fixture
def db_session():
    """Session de base de données de test"""
    # Crée une DB en mémoire
    yield session

@pytest.fixture
def test_user(db_session):
    """Utilisateur de test"""
    user = User(email="test@example.com", ...)
    db_session.add(user)
    db_session.commit()
    return user
```

---

## 📝 Écrire un Nouveau Test Critique

### Template

```python
import pytest
from sqlmodel import Session, select
from app.models.user import User
from app.core.security import hash_password

@pytest.mark.critical
def test_user_creation_with_valid_data(db_session: Session):
    """
    Test critique : Création d'un utilisateur avec données valides
    
    GIVEN: Des données utilisateur valides
    WHEN: On crée un utilisateur
    THEN: L'utilisateur est créé en base avec les bonnes données
    """
    # GIVEN
    user_data = {
        "email": "john.doe@example.com",
        "hashed_password": hash_password("Password123!"),
        "full_name": "John Doe",
        "role": UserRole.USER
    }
    
    # WHEN
    user = User(**user_data)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # THEN
    assert user.id is not None
    assert user.email == "john.doe@example.com"
    assert user.full_name == "John Doe"
    assert user.is_active == True
    
    # Vérifier en DB
    db_user = db_session.get(User, user.id)
    assert db_user is not None
    assert db_user.email == user.email
```

### Bonnes pratiques

- ✅ Nom explicite : `test_<fonctionnalite>_<scenario>`
- ✅ Docstring : Description claire du test
- ✅ Pattern AAA : Arrange, Act, Assert (GIVEN, WHEN, THEN)
- ✅ Isolement : Chaque test est indépendant
- ✅ Nettoyage : Utiliser les fixtures pour le cleanup

---

## ⚡ Performances des Tests

### Durées typiques

| Type | Nombre | Durée |
|------|--------|-------|
| **Unitaires** | ~20 | 2-3s |
| **Intégration** | ~10 | 5-8s |
| **Total critique** | ~30 | **8-12s** |

### Optimisations

- ✅ Base de données en mémoire (SQLite `:memory:`)
- ✅ Fixtures avec scope `session`
- ✅ Tests parallèles : `pytest -n auto`

---

## 📋 Checklist avant Commit

Avant chaque commit, vérifier :

```bash
# 1. Tests critiques passent
pytest -m critical

# 2. Pas de regression
pytest

# 3. Couverture maintenue
pytest --cov=app --cov-fail-under=80

# 4. Linting (optionnel)
black app/ tests/
flake8 app/ tests/
mypy app/
```

---

## 🔍 Commandes Utiles

```bash
# Lister tous les tests
pytest --collect-only

# Tests critiques uniquement
pytest -m critical

# Tests par fichier
pytest tests/unit/test_security.py

# Tests par fonction
pytest tests/unit/test_security.py::test_hash_password

# Avec détails
pytest -v -s

# Couverture détaillée
pytest --cov=app --cov-report=term-missing

# Générer rapport HTML
pytest --cov=app --cov-report=html
```

---

## 📈 Statistiques

- **Tests critiques** : 30
- **Couverture globale** : ~85%
- **Couverture critique** : ~95%
- **Temps d'exécution** : ~10 secondes
- **Dernière mise à jour** : 19 octobre 2025

---

## 🤝 Contribution

### Ajouter un test critique

1. Identifier une fonctionnalité critique
2. Écrire le test avec `@pytest.mark.critical`
3. S'assurer que le test passe
4. Commit : `git commit -m "test: ajout test critique pour X"`

### Tests obligatoires

Chaque **nouvelle fonctionnalité** doit avoir :
- ✅ Au moins 1 test unitaire
- ✅ Au moins 1 test d'intégration si API
- ✅ Marqué `critical` si fonctionnalité critique

---

**Les tests sont votre filet de sécurité ! 🎯**
