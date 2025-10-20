# 🧹 Qualité du Code - Ruff & Pre-commit

## 🎯 Vue d'ensemble

Ce document explique comment utiliser **Ruff** pour maintenir un code propre et de qualité dans le projet MPPEEP Dashboard.

---

## 🚀 Qu'est-ce que Ruff ?

**Ruff** est un linter et formateur Python **ultra-rapide** (écrit en Rust) qui remplace plusieurs outils :

| Outil | Remplacé par Ruff |
|-------|-------------------|
| **black** | ✅ `ruff format` |
| **isort** | ✅ `ruff check --select I` |
| **flake8** | ✅ `ruff check` |
| **pyupgrade** | ✅ `ruff check --select UP` |
| **autoflake** | ✅ `ruff check --select F` |

**Avantage** : **10-100x plus rapide** que les outils traditionnels !

---

## 📥 Installation

### Avec pip

```bash
pip install ruff
```

### Avec uv (recommandé pour ce projet)

```bash
uv add ruff --dev
```

### Vérifier l'installation

```bash
ruff --version
# ruff 0.1.9

# Ou avec uv
uv run ruff --version
```

### 💡 Note sur `uv`

Ce projet utilise **`uv`** comme gestionnaire de dépendances. Préfixez toutes les commandes avec `uv run` :

```bash
# Au lieu de :
ruff check app/

# Utilisez :
uv run ruff check app/
```

---

## 🛠️ Utilisation

### 1. Vérifier le code (sans modification)

```bash
# Vérifier tout le code
ruff check app/ tests/

# Vérifier un fichier spécifique
ruff check app/main.py

# Afficher les erreurs avec code source
ruff check app/ --show-source
```

**Résultat** :
```
app/services/rh.py:45:1: F401 [*] `app.models.personnel.ServiceDept` imported but unused
app/api/v1/endpoints/stock.py:120:5: E501 Line too long (125 > 120 characters)
app/models/user.py:15:9: N805 First argument of a method should be named `self`
Found 3 errors.
[*] = auto-fixable
```

### 2. Corriger automatiquement

```bash
# Corrections auto standard (supprime imports inutiles, simplifie le code, etc.)
ruff check --fix app/ tests/

# Corrections avec Ruff via uv
uv run ruff check app/ tests/ --fix

# Corrections "non-sûres" (plus agressif)
uv run ruff check app/ tests/ --fix --unsafe-fixes

# Tri des imports uniquement (comme isort)
ruff check --select I --fix app/ tests/
```

**Résultat** :
```
✅ Fixed 324 errors
⚠️ 94 errors remain (manual fix required)
```

**Note** : Les corrections "unsafe" modifient le comportement du code. Utilisez-les avec précaution et testez après !

### 3. Formater le code (comme black)

```bash
# Formater tout le code
ruff format app/ tests/

# Avec uv
uv run ruff format app/ tests/

# Vérifier le formatage sans modifier
ruff format --check app/ tests/

# Avec uv
uv run ruff format --check app/ tests/
```

**Résultat** :
```
69 files reformatted
4 files unchanged
```

### 4. Nettoyage complet (commande tout-en-un)

```bash
# Avec Make
make clean-code

# Ou avec le script Python
python scripts/lint_and_format.py
```

**Ce que ça fait** :
1. ✅ Formate le code (indentation, espaces, quotes)
2. ✅ Trie les imports alphabétiquement
3. ✅ Supprime les imports inutilisés
4. ✅ Simplifie le code (compréhensions, f-strings)
5. ✅ Corrige les violations PEP 8

---

## 📋 Commandes Makefile

```bash
# Vérifier le code
make lint

# Corriger automatiquement
make lint-fix

# Formater le code
make format

# Vérifier le formatage
make format-check

# Nettoyage complet (recommandé)
make clean-code

# Vérifier tout sans modifier
make check-all
```

---

## 🔧 Configuration Ruff

### Fichier `ruff.toml`

```toml
# Version Python cible
target-version = "py311"

# Longueur de ligne max
line-length = 120

# Règles activées
[lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes (imports inutilisés, etc.)
    "I",      # isort (tri des imports)
    "N",      # pep8-naming (nommage)
    "UP",     # pyupgrade (modernisation)
    "B",      # flake8-bugbear (bugs potentiels)
    "SIM",    # flake8-simplify (simplifications)
]

# Règles ignorées
ignore = [
    "E501",   # Line too long (géré par line-length)
]

# Autoriser imports non utilisés dans __init__.py
[lint.per-file-ignores]
"__init__.py" = ["F401"]
```

---

## 🔄 Pre-commit Hooks

### Installation

```bash
# Installer pre-commit
pip install pre-commit

# Activer les hooks
pre-commit install
```

### Utilisation automatique

Maintenant, **à chaque commit**, Ruff vérifie et formate automatiquement :

```bash
git add app/main.py
git commit -m "feat: nouvelle fonctionnalité"

# → Pre-commit s'exécute automatiquement
🎨 Ruff Format.......................................Passed
🔍 Ruff Lint.........................................Passed
🧹 Nettoyer espaces..................................Passed
✅ Vérifier YAML.....................................Passed

# Commit créé ✅
```

### Forcer l'exécution

```bash
# Exécuter les hooks sans commiter
pre-commit run --all-files

# Mettre à jour les hooks
pre-commit autoupdate
```

---

## 📊 Règles Ruff Importantes

### E : Errors (pycodestyle)

```python
# ❌ E501: Ligne trop longue
def very_long_function_name_with_many_parameters(param1, param2, param3, param4, param5, param6, param7, param8):
    pass

# ✅ Correction
def very_long_function_name_with_many_parameters(
    param1, param2, param3, param4, 
    param5, param6, param7, param8
):
    pass
```

### F : Pyflakes

```python
# ❌ F401: Import non utilisé
from app.models.user import User, Agent, Service  # Service non utilisé

# ✅ Correction (Ruff supprime automatiquement)
from app.models.user import User, Agent
```

### I : Isort (tri des imports)

```python
# ❌ Imports désordonnés
from app.models.user import User
from typing import Optional
from datetime import datetime
from fastapi import APIRouter

# ✅ Correction automatique
from datetime import datetime
from typing import Optional

from fastapi import APIRouter

from app.models.user import User
```

### N : Naming (nommage)

```python
# ❌ N806: Variable devrait être en minuscule
MyVariable = 10

# ✅ Correction
my_variable = 10

# ❌ N802: Fonction devrait être en snake_case
def MyFunction():
    pass

# ✅ Correction
def my_function():
    pass
```

### B : Bugbear (bugs potentiels)

```python
# ❌ B006: Mutable default argument
def add_to_list(item, my_list=[]):
    my_list.append(item)
    return my_list

# ✅ Correction
def add_to_list(item, my_list=None):
    if my_list is None:
        my_list = []
    my_list.append(item)
    return my_list
```

### SIM : Simplify

```python
# ❌ SIM108: Use ternary operator
if condition:
    x = 1
else:
    x = 2

# ✅ Correction
x = 1 if condition else 2

# ❌ SIM105: Use contextlib.suppress()
try:
    os.remove(file)
except FileNotFoundError:
    pass

# ✅ Correction
from contextlib import suppress

with suppress(FileNotFoundError):
    os.remove(file)
```

---

## 🎯 Workflow Recommandé

### Avant chaque commit

```bash
# 1. Nettoyer le code
make clean-code

# 2. Vérifier que tout est OK
make check-all

# 3. Lancer les tests
pytest -m critical

# 4. Commiter
git add .
git commit -m "feat: ma nouvelle fonctionnalité"
```

### Avec pre-commit (automatique)

```bash
# Juste commiter, pre-commit fait le reste !
git add .
git commit -m "feat: ma nouvelle fonctionnalité"

# → Ruff s'exécute automatiquement
```

---

## 📈 Intégration CI/CD

### GitHub Actions (`.github/workflows/ci.yml`)

Ajouter une étape de vérification Ruff :

```yaml
- name: 🔍 Ruff (linting)
  run: |
    pip install ruff
    ruff check app/ tests/ --output-format=github

- name: 🎨 Ruff (formatage)
  run: |
    ruff format --check app/ tests/
```

**Résultat** : Le CI/CD échoue si le code n'est pas formaté correctement.

---

## 🔍 Commandes Utiles

```bash
# Lister toutes les règles disponibles
ruff linter

# Expliquer une règle spécifique
ruff rule E501

# Ignorer une règle dans un fichier
# pyright: ignore[E501]
# ruff: noqa: E501

# Ignorer une ligne
x = very_long_line_that_is_too_long  # noqa: E501

# Voir les règles activées
ruff config

# Statistiques
ruff check app/ --statistics
```

---

## 📊 Exemple Avant/Après

### Avant Ruff ❌

```python
# app/services/example.py
from app.models.user import User,Agent,Service
from typing import Optional,List
from datetime import datetime,date
from fastapi import APIRouter
import os, sys

def CreateUser(UserEmail:str,UserPassword:str)->User:
    
    if UserEmail=="":
        raise ValueError("Email vide")
    
    user=User(email=UserEmail,password=UserPassword)
    return user

def get_users(db):
    users=db.query(User).all()
    result=[]
    for u in users:
        result.append(u)
    return result
```

### Après Ruff ✅

```python
# app/services/example.py
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter

from app.models.user import Agent, Service, User


def create_user(user_email: str, user_password: str) -> User:
    if not user_email:
        raise ValueError("Email vide")

    return User(email=user_email, password=user_password)


def get_users(db):
    return db.query(User).all()
```

**Changements** :
- ✅ Imports triés et groupés
- ✅ Espaces autour des opérateurs
- ✅ Snake_case pour les fonctions
- ✅ Simplification du code
- ✅ Ligne vide entre les fonctions
- ✅ Suppression du code redondant

---

## 🎓 Bonnes Pratiques

### 1. Formater régulièrement

```bash
# Chaque jour
make clean-code
```

### 2. Vérifier avant de push

```bash
# Avant git push
make check-all
pytest -m critical
```

### 3. Utiliser pre-commit

```bash
# Une fois installé, tout est automatique
pre-commit install

# Les hooks s'exécutent à chaque commit
```

### 4. Ignorer intelligemment

```python
# Ignorer une ligne spécifique (avec raison)
long_url = "https://very-long-url..."  # noqa: E501 (URL nécessairement longue)

# Ignorer un fichier entier (ruff.toml)
[lint.per-file-ignores]
"migrations/*.py" = ["ALL"]
```

---

## 🔧 Configuration VS Code

### Installer l'extension Ruff

1. Ouvrir VS Code
2. Extensions → Rechercher "Ruff"
3. Installer "Ruff" (Astral Software)

### Configuration (`settings.json`)

```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": true,
      "source.organizeImports.ruff": true
    }
  }
}
```

**Résultat** : Le code est formaté automatiquement à chaque sauvegarde ! ✨

---

## 📊 Statistiques de Code

### Générer un rapport

```bash
# Nombre d'erreurs par type
ruff check app/ --statistics

# Format GitHub (pour CI/CD)
ruff check app/ --output-format=github

# Format JSON
ruff check app/ --output-format=json > ruff-report.json
```

### Exemple de rapport

```
Statistics:
  E501:  12  Line too long
  F401:   5  Import unused
  I001:   8  Imports not sorted
  N805:   3  First argument should be self
  UP007:  2  Use X | Y for Union types

Total: 30 errors in 15 files
```

---

## 🎯 Règles Spécifiques au Projet

### Imports obligatoires en premier

```python
# 1. Imports standard library
from datetime import datetime
from typing import Optional

# 2. Imports third-party
from fastapi import APIRouter
from sqlmodel import Session

# 3. Imports locaux
from app.models.user import User
from app.services.rh import RHService
```

### Docstrings Google Style

```python
def calculate_amortissement(
    valeur: Decimal,
    duree: int,
    methode: str = "LINEAIRE"
) -> Decimal:
    """Calcule l'amortissement annuel d'un matériel.
    
    Args:
        valeur: Valeur d'acquisition du matériel
        duree: Durée d'amortissement en années
        methode: Méthode de calcul (LINEAIRE ou DEGRESSIF)
    
    Returns:
        Montant de l'amortissement annuel
    
    Raises:
        ValueError: Si la durée est <= 0
    
    Example:
        >>> calculate_amortissement(Decimal("1500000"), 3, "LINEAIRE")
        Decimal('500000')
    """
    if duree <= 0:
        raise ValueError("Durée doit être > 0")
    
    return valeur / Decimal(duree)
```

---

## 🚨 Erreurs Courantes et Solutions

### Erreur : F401 - Import non utilisé

```python
# ❌ Problème
from app.models.user import User, Agent, Service

def get_user():
    return User()  # Agent et Service non utilisés

# ✅ Solution automatique (ruff check --fix)
from app.models.user import User

def get_user():
    return User()
```

### Erreur : E501 - Ligne trop longue

```python
# ❌ Problème
user = User(email="very.long.email.address@example.com", full_name="Very Long Full Name Here", role=UserRole.ADMIN, is_active=True)

# ✅ Solution
user = User(
    email="very.long.email.address@example.com",
    full_name="Very Long Full Name Here",
    role=UserRole.ADMIN,
    is_active=True
)
```

### Erreur : I001 - Imports non triés

```python
# ❌ Problème
from app.models.user import User
from datetime import datetime
from fastapi import APIRouter

# ✅ Solution automatique (ruff check --select I --fix)
from datetime import datetime

from fastapi import APIRouter

from app.models.user import User
```

---

## 🎯 Intégration dans le Workflow

### Pull Request Checklist

Avant de créer une PR :

```bash
# 1. Nettoyer le code
make clean-code

# 2. Vérifier
make check-all

# 3. Tests
pytest -m critical

# 4. Commit
git add .
git commit -m "feat: description"

# 5. Push
git push origin feature/ma-branche
```

### CI/CD vérifie automatiquement

Le pipeline GitHub Actions vérifiera :
- ✅ Code formaté correctement
- ✅ Pas d'imports inutilisés
- ✅ Respect des conventions PEP 8
- ✅ Tests passent

---

## 🏆 Objectifs de Qualité

### Métriques cibles

| Métrique | Cible | Actuel |
|----------|-------|--------|
| **Erreurs Ruff** | 0 | À mesurer |
| **Couverture tests** | 80% | ~85% |
| **Complexité cyclomatique** | <10 | À mesurer |
| **Docstrings** | 100% (fonctions publiques) | À améliorer |

### Commandes de mesure

```bash
# Compter les erreurs Ruff
ruff check app/ | grep "Found" 

# Couverture de code
pytest --cov=app --cov-report=term

# Complexité (avec radon)
pip install radon
radon cc app/ -s
```

---

## 🔧 Configuration Avancée

### Ignorer des fichiers spécifiques

```toml
# ruff.toml
exclude = [
    "migrations/",
    "scripts/old/",
    "app/legacy/",
]
```

### Règles par fichier

```toml
[lint.per-file-ignores]
"tests/*.py" = ["S101"]  # Autoriser assert dans tests
"scripts/*.py" = ["T201"]  # Autoriser print dans scripts
```

### Auto-fix sélectif

```bash
# Corriger uniquement les imports
ruff check --select I --fix app/

# Corriger uniquement pyupgrade
ruff check --select UP --fix app/

# Corriger tout sauf...
ruff check --fix --ignore E501 app/
```

---

## 📚 Ressources

### Documentation officielle
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Ruff Rules](https://docs.astral.sh/ruff/rules/)
- [Ruff Configuration](https://docs.astral.sh/ruff/configuration/)

### Tutoriels
- [Ruff vs Black](https://docs.astral.sh/ruff/formatter/)
- [Migration depuis Flake8](https://docs.astral.sh/ruff/faq/#how-does-ruff-compare-to-flake8)

---

## ✅ Checklist de Qualité

Avant chaque commit :

- [ ] `make clean-code` exécuté
- [ ] `make check-all` passe (0 erreurs)
- [ ] `pytest -m critical` passe
- [ ] Pas de `print()` dans le code (utiliser `logger`)
- [ ] Docstrings ajoutées aux nouvelles fonctions
- [ ] Type hints sur toutes les fonctions
- [ ] Pas de `# type: ignore` sans raison
- [ ] Pas de code commenté (supprimer)

---

**Un code propre est un code maintenable ! 🧹✨**

Prochaine étape : `make clean-code` pour nettoyer tout le projet !

