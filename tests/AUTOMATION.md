# 🤖 Automatisation des Tests avec Pytest

## 🎯 Vue d'Ensemble

Ce guide explique comment **automatiser complètement** vos tests avec des modules pytest avancés.

**Résultat :**
- ✅ Tests relancés automatiquement quand vous modifiez le code
- ✅ Tests parallèles (10x plus rapides)
- ✅ Rapports HTML visuels
- ✅ Couverture de code automatique
- ✅ Interface CLI améliorée

---

## 📦 Installation Rapide

```bash
# Installer tous les modules de test en une commande
cd mppeep
uv sync --extra dev

# Ou installer manuellement
uv add --dev pytest pytest-watch pytest-xdist pytest-cov pytest-html pytest-sugar pytest-timeout
```

---

## 🔄 1. pytest-watch (Auto-Reload) ⭐

**Le plus utile pour le développement quotidien !**

### C'est Quoi ?

Relance **automatiquement** les tests quand vous modifiez un fichier.

**Comme `uvicorn --reload` mais pour les tests !**

### Utilisation

```bash
# Lancer le mode watch
ptw

# Avec options
ptw --verbose               # Mode verbose
ptw --clear                 # Clear console à chaque run
ptw tests/unit/             # Seulement les tests unitaires
ptw -- -v --cov=app         # Options pytest après --
ptw --runner "pytest -n auto"  # Avec parallélisation
```

### Workflow Développement Idéal

```
Terminal 1 : ptw --clear
→ Tests s'exécutent automatiquement

Terminal 2 : uvicorn app.main:app --reload
→ Application tourne

Vous modifiez user_service.py
→ Terminal 1 : Tests relancés automatiquement ✅
→ Terminal 2 : Application redémarre ✅
→ Feedback instantané !
```

---

## ⚡ 2. pytest-xdist (Tests Parallèles)

### C'est Quoi ?

Exécute les tests sur **plusieurs CPU en parallèle**.

### Utilisation

```bash
# Auto : utilise tous les CPU
pytest -n auto

# 4 workers
pytest -n 4

# Avec couverture
pytest -n auto --cov=app

# Distribution intelligente
pytest -n auto --dist loadscope  # Groupe par classe
pytest -n auto --dist loadfile   # Groupe par fichier
```

### Performance

```
100 tests sur 1 CPU  : 60 secondes
100 tests sur 8 CPU  : 8 secondes  (7.5x plus rapide) ✅
```

---

## 📊 3. pytest-cov (Couverture de Code)

### C'est Quoi ?

Montre **quelles lignes sont testées** et lesquelles manquent.

### Utilisation

```bash
# Rapport terminal simple
pytest --cov=app

# Avec lignes manquantes
pytest --cov=app --cov-report=term-missing

# Rapport HTML interactif
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Rapport XML (pour CI/CD)
pytest --cov=app --cov-report=xml

# Exiger un minimum de couverture
pytest --cov=app --cov-fail-under=90  # Échoue si < 90%
```

### Output

```
Name                           Stmts   Miss  Cover   Missing
------------------------------------------------------------
app/services/user_service.py      50      2    96%   45-46
app/api/v1/endpoints/auth.py      80      5    94%   12, 34-37
------------------------------------------------------------
TOTAL                            145      7    95%
```

---

## 📝 4. pytest-html (Rapports HTML)

### Utilisation

```bash
# Rapport HTML
pytest --html=reports/test_report.html --self-contained-html

# Avec captures d'écran (si tests E2E)
pytest --html=reports/test_report.html --capture=no
```

### Contenu du Rapport

- ✅ Résumé (passed/failed/skipped)
- ✅ Temps d'exécution par test
- ✅ Logs détaillés des erreurs
- ✅ Graphiques
- ✅ Filtres interactifs

---

## 🎨 5. pytest-sugar (Interface Jolie)

### Avant

```
test_auth.py::test_login PASSED                          [ 33%]
test_auth.py::test_logout PASSED                         [ 66%]
test_auth.py::test_register FAILED                       [100%]
```

### Après (avec sugar)

```
test_auth.py ✓✓✗                                         67% ██████▉···

Tests passed: 2/3 (66.67%)
Tests failed: 1/3 (33.33%)
```

---

## ⏱️ 6. pytest-timeout (Timeout Auto)

### Utilisation

```bash
# Timeout global de 10 secondes
pytest --timeout=10

# Timeout par test
@pytest.mark.timeout(5)
def test_slow_operation():
    # Max 5 secondes
    ...
```

---

## 🚀 Workflow Complet d'Automatisation

### Développement Local

#### Terminal 1 : Tests en Auto-Reload

```bash
ptw --clear --runner "pytest -n auto --cov=app --cov-report=term-missing"
```

**Ce qui se passe :**
- ✅ Tests relancés automatiquement à chaque modification
- ✅ Exécutés en parallèle (rapide)
- ✅ Affiche la couverture
- ✅ Console nettoyée à chaque run

---

#### Terminal 2 : Application

```bash
uvicorn app.main:app --reload
```

---

### CI/CD (GitHub Actions)

Dans `.github/workflows/ci.yml` :

```yaml
- name: Tests avec couverture
  run: |
    pytest -n auto --cov=app --cov-report=xml --cov-report=html --html=reports/pytest.html
```

**Résultat :**
- ✅ Tests parallèles (rapides sur CI)
- ✅ Rapport de couverture (Codecov)
- ✅ Rapport HTML (artefact téléchargeable)

---

## 📋 Commandes Recommandées

### Développement Quotidien

```bash
# Mode watch (recommandé pour dev)
ptw --clear

# Tests rapides (parallèles)
pytest -n auto

# Tests avec couverture
pytest --cov=app --cov-report=term-missing
```

---

### Avant un Commit

```bash
# Suite complète
pytest -n auto --cov=app --cov-report=term-missing --cov-fail-under=80

# Ou avec rapport HTML
pytest -n auto --cov=app --cov-report=html --html=reports/report.html
```

---

### CI/CD

```bash
# Maximum de vérifications
pytest -n auto \
    --cov=app \
    --cov-report=xml \
    --cov-report=html \
    --html=reports/pytest.html \
    --self-contained-html \
    --timeout=30 \
    --maxfail=5
```

---

## ⚙️ Configuration pytest.ini

Activez les options par défaut :

```ini
[pytest]
addopts =
    -v                        # Verbose
    -ra                       # Résumé
    --tb=short               # Traceback court
    -n auto                  # ← Décommenter pour parallélisation auto
    --cov=app               # ← Décommenter pour couverture auto
    --cov-report=term-missing
    --html=reports/pytest.html
    --self-contained-html
```

---

## 🎯 Combinaisons Puissantes

### TDD (Test-Driven Development)

```bash
# Terminal 1 : Tests en watch
ptw --clear

# Terminal 2 : Application
uvicorn app.main:app --reload

# Workflow :
1. Écrire un test (test_new_feature.py)
2. Le test échoue automatiquement (red)
3. Implémenter la feature (user_service.py)
4. Le test passe automatiquement (green) ✅
5. Refactorer si besoin
```

---

### Performance Testing

```bash
# Identifier les tests lents
pytest --durations=10

# Marquer et exclure les tests lents
pytest -m "not slow"

# Timeout pour éviter les tests infinis
pytest --timeout=10
```

---

### Rapport Complet

```bash
# Générer tous les rapports
pytest -n auto \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=html \
    --html=reports/pytest_report.html \
    --self-contained-html

# Résultat :
# - htmlcov/index.html (couverture)
# - reports/pytest_report.html (résultats tests)
```

---

## 📊 Tableau Comparatif

| Module | Fonction | Gain |
|--------|----------|------|
| **pytest-watch** | Auto-reload | ⏱️ Temps de feedback |
| **pytest-xdist** | Parallélisation | ⚡ 5-10x plus rapide |
| **pytest-cov** | Couverture | 📊 Qualité du code |
| **pytest-html** | Rapports | 📝 Documentation |
| **pytest-sugar** | Interface | 👁️ Lisibilité |
| **pytest-timeout** | Sécurité | 🛡️ Évite blocages |

---

## 💡 Exemples Pratiques

### Exemple 1 : Développement d'une Feature

```bash
# 1. Lancer le watch
ptw --clear tests/unit/

# 2. Créer le test
# tests/unit/test_new_feature.py

def test_new_feature():
    result = my_function()
    assert result == "expected"

# → Test échoue automatiquement (fonction n'existe pas)

# 3. Implémenter
# app/services/my_service.py

def my_function():
    return "expected"

# → Test passe automatiquement ✅
```

---

### Exemple 2 : Vérifier Avant un Commit

```bash
# Suite complète avec couverture minimum
pytest -n auto --cov=app --cov-fail-under=80

# Si < 80% → Échec
# Si ≥ 80% → Succès ✅
```

---

### Exemple 3 : Rapport pour l'Équipe

```bash
# Générer un rapport complet
pytest -n auto \
    --cov=app \
    --cov-report=html \
    --html=reports/weekly_report.html \
    --self-contained-html

# Partager :
# - htmlcov/index.html
# - reports/weekly_report.html
```

---

## 🎮 Commandes Pratiques

```bash
# Tests de base
pytest                                # Tous les tests
pytest -v                             # Verbose
pytest tests/unit/                    # Dossier spécifique
pytest tests/unit/test_user.py       # Fichier spécifique
pytest -k "auth"                      # Tests contenant "auth"
pytest -m unit                        # Marker "unit"

# Avec automatisation
ptw                                   # Watch mode
pytest -n auto                        # Parallèle
pytest --cov=app                      # Couverture
pytest --html=report.html            # Rapport HTML

# Combinaisons
ptw -- -n auto --cov=app             # Watch + Parallèle + Couverture
pytest -n auto --cov=app --cov-fail-under=90  # Parallèle + Couverture minimum
pytest -n auto --html=report.html --self-contained-html  # Parallèle + Rapport

# Debug
pytest -x                             # Stop au premier échec
pytest --pdb                          # Debugger Python
pytest --lf                           # Last failed (seulement les tests échoués)
pytest --ff                           # Failed first (échoués d'abord)
```

---

## 📈 Statistiques de Performance

### Sans Automatisation

```
Workflow manuel :
1. Modifier le code
2. Basculer vers terminal
3. Taper : pytest
4. Attendre 60 secondes
5. Voir le résultat
6. Retour au code

Temps total : ~90 secondes par itération
```

---

### Avec Automatisation Complète

```
Workflow automatisé :
1. Modifier le code
2. Tests relancés automatiquement (ptw)
3. Exécution parallèle (8 secondes)
4. Résultat visible immédiatement

Temps total : ~10 secondes par itération ✅
```

**Gain : 9x plus rapide ! 🚀**

---

## 🎯 Setup Recommandé

### pyproject.toml

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "pytest-xdist>=3.5.0",
    "pytest-watch>=4.2.0",
    "pytest-html>=4.1.0",
    "pytest-sugar>=1.0.0",
    "pytest-timeout>=2.2.0",
]
```

---

### pytest.ini

```ini
[pytest]
addopts =
    -v
    -ra
    --tb=short
    # Activer pour auto-parallélisation
    # -n auto
    # Activer pour couverture auto
    # --cov=app
    # --cov-report=term-missing
```

---

### .gitignore

```gitignore
# Rapports de tests
htmlcov/
reports/
.coverage
coverage.xml
*.html
```

---

## 🎓 Cas d'Usage

### 1. Développement Rapide (TDD)

```bash
# Terminal watch
ptw --clear tests/unit/

# Workflow :
1. Écrire test → Rouge ❌
2. Coder → Vert ✅
3. Refactorer → Toujours vert ✅
```

---

### 2. Pull Request

```bash
# Vérification complète avant PR
pytest -n auto --cov=app --cov-fail-under=85 --html=pr_report.html
```

---

### 3. CI/CD

```bash
# GitHub Actions
pytest -n auto --cov=app --cov-report=xml --html=reports/ci_report.html --timeout=30
```

---

### 4. Rapport Hebdomadaire

```bash
# Générer rapport complet
pytest -n auto --cov=app --cov-report=html --html=reports/weekly_$(date +%Y%m%d).html
```

---

## 🔧 Troubleshooting

### ptw ne fonctionne pas

```bash
# Vérifier l'installation
ptw --version

# Réinstaller
uv add pytest-watch --dev --force
```

---

### Tests parallèles échouent

```bash
# Certains tests ne sont pas thread-safe
# Solution : désactiver pour ces tests
pytest tests/unit/  # Sans -n auto

# Ou marquer les tests
@pytest.mark.no_parallel
def test_not_thread_safe():
    ...
```

---

### Couverture à 0%

```bash
# Vérifier que le module app est importable
pytest --cov=app --cov-report=term

# Si 0%, vérifier PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest --cov=app
```

---

## ✅ Commandes Recommandées

### Développement Quotidien

```bash
# Mode watch (meilleur pour TDD)
ptw --clear
```

---

### Avant Commit

```bash
# Suite complète rapide
pytest -n auto --cov=app --cov-fail-under=80
```

---

### Avant Push

```bash
# Suite complète avec rapports
pytest -n auto --cov=app --cov-report=html --html=reports/pre-push.html
```

---

### CI/CD

```bash
# Maximum de checks
pytest -n auto \
    --cov=app \
    --cov-report=xml \
    --cov-report=html \
    --html=reports/ci_report.html \
    --self-contained-html \
    --timeout=30 \
    --maxfail=5
```

---

## 🎉 Résumé

| Module | Commande | Usage |
|--------|----------|-------|
| **pytest-watch** | `ptw` | Développement TDD |
| **pytest-xdist** | `pytest -n auto` | Tests rapides |
| **pytest-cov** | `pytest --cov=app` | Qualité code |
| **pytest-html** | `pytest --html=report.html` | Documentation |
| **pytest-sugar** | `pytest` (auto) | Meilleure UI |
| **pytest-timeout** | `pytest --timeout=10` | Sécurité |

---

## 🚀 Prochaines Étapes

1. ✅ Installer les modules : `uv sync --extra dev`
2. ✅ Lancer en mode watch : `ptw --clear`
3. ✅ Développer avec TDD
4. ✅ Commiter avec couverture validée

**Vos tests sont maintenant automatisés à 100% ! 🎊**
