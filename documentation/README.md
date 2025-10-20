# 📚 Documentation MPPEEP Dashboard

## 🎯 Bienvenue

Cette documentation complète vous guidera à travers tous les aspects du système MPPEEP Dashboard, depuis son démarrage jusqu'à la compréhension détaillée de chaque module.

---

## 📖 DOCUMENTS DISPONIBLES

### 1. **[Démarrage de l'Application](01_DEMARRAGE_APPLICATION.md)** 🚀

**Contenu** :
- Lancement de l'application avec Uvicorn
- Chargement du module principal
- Initialisation de la base de données
- Création de l'instance FastAPI
- Configuration des middlewares
- Enregistrement des routes
- Parcours complet jusqu'à la page de login

**Pour qui ?**
- Nouveaux développeurs découvrant le projet
- DevOps configurant l'environnement
- Débogage des problèmes de démarrage

**Durée de lecture** : 20-30 minutes

---

### 2. **[Parcours d'une Requête Client](02_PARCOURS_REQUETE_CLIENT.md)** 🔄

**Contenu** :
- Réception de la requête HTTP
- Traitement par les middlewares
- Routage FastAPI
- Résolution des dépendances
- Authentification JWT
- Exécution de la route
- Requêtes SQL
- Rendu du template Jinja2
- Construction de la réponse
- Affichage dans le navigateur

**Pour qui ?**
- Développeurs backend
- Développeurs fullstack
- Debugging des problèmes de performance

**Durée de lecture** : 30-40 minutes

---

### 3. **[Détails des Modules](03_MODULES_DETAILS.md)** 🏗️

**Contenu** :
- **Module CORE** : Configuration, sécurité, enums, logging
- **Module DATABASE** : Session, connexion, création des tables
- **Module MODELS** : Tous les modèles SQLModel (User, Agent, HRRequest, Article, etc.)
- **Module SERVICES** : Logique métier (RHService, HierarchyService, StockService)

**Pour qui ?**
- Développeurs backend
- Architectes logiciels
- Mainteneurs du code

**Durée de lecture** : 45-60 minutes

---

### 4. **[Modules Frontend et API](04_MODULES_FRONTEND_API.md)** 🎨

**Contenu** :
- **Module API ENDPOINTS** : Routes FastAPI détaillées (auth, rh, stock, etc.)
- **Module TEMPLATES** : Structure Jinja2, layouts, composants
- **Module STATIC** : CSS, JavaScript, organisation des assets
- Exemples de code complets
- Bonnes pratiques de sécurité et performance

**Pour qui ?**
- Développeurs frontend
- Développeurs fullstack
- Intégrateurs web

**Durée de lecture** : 40-50 minutes

---

## 🗂️ STRUCTURE DU PROJET

```
mppeep/
├── app/
│   ├── api/                 # Routes et endpoints API
│   │   └── v1/
│   │       ├── router.py    # Router principal
│   │       └── endpoints/   # Modules API
│   │           ├── auth.py
│   │           ├── rh.py
│   │           ├── stock.py
│   │           ├── personnel.py
│   │           ├── budget.py
│   │           ├── performance.py
│   │           ├── referentiels.py
│   │           └── workflow_admin.py
│   │
│   ├── core/                # Configuration et utilitaires
│   │   ├── config.py        # Configuration globale
│   │   ├── security.py      # Sécurité (JWT, bcrypt)
│   │   ├── enums.py         # Énumérations
│   │   └── logging_config.py
│   │
│   ├── db/                  # Base de données
│   │   └── session.py       # Gestion des sessions
│   │
│   ├── models/              # Modèles SQLModel
│   │   ├── user.py
│   │   ├── personnel.py
│   │   ├── rh.py
│   │   ├── workflow_config.py
│   │   ├── stock.py
│   │   ├── budget.py
│   │   └── performance.py
│   │
│   ├── services/            # Logique métier
│   │   ├── rh.py
│   │   ├── hierarchy_service.py
│   │   ├── stock_service.py
│   │   ├── workflow_config_service.py
│   │   └── activity_service.py
│   │
│   ├── static/              # Fichiers statiques
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   │
│   └── templates/           # Templates Jinja2
│       ├── layouts/
│       ├── components/
│       └── pages/
│
├── documentation/           # 📚 Cette documentation
│   ├── README.md
│   ├── 01_DEMARRAGE_APPLICATION.md
│   ├── 02_PARCOURS_REQUETE_CLIENT.md
│   ├── 03_MODULES_DETAILS.md
│   └── 04_MODULES_FRONTEND_API.md
│
├── scripts/                 # Scripts utilitaires
├── tests/                   # Tests
├── main.py                  # Point d'entrée
├── requirements.txt         # Dépendances
└── README.md
```

---

## 🚀 DÉMARRAGE RAPIDE

### Prérequis

- Python 3.10+
- pip ou poetry
- SQLite (inclus avec Python)

### Installation

```bash
# 1. Cloner le projet
cd mppeep

# 2. Créer un environnement virtuel
python -m venv .venv

# 3. Activer l'environnement
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

# 4. Installer les dépendances
pip install -r requirements.txt

# 5. Lancer l'application
uvicorn app.main:app --reload --host 0.0.0.0 --port 9000
```

### Accès

- **Interface web** : http://localhost:9000
- **Documentation API** : http://localhost:9000/docs (Swagger)
- **Logs** : Affichés dans la console

---

## 📊 MODULES PRINCIPAUX

| Module | Description | Technologies |
|--------|-------------|--------------|
| **Authentification** | Login, JWT, gestion des sessions | FastAPI, JWT, bcrypt |
| **RH** | Demandes RH, workflows dynamiques | FastAPI, SQLModel, Jinja2 |
| **Personnel** | Gestion des agents | SQLModel, Pydantic |
| **Stock** | Articles, lots périssables, amortissement | Decimal, SQLite |
| **Budget** | SIGOBE, fiches budgétaires | FastAPI, Excel |
| **Performance** | KPIs, objectifs, indicateurs | SQLModel, Chart.js |
| **Workflow** | Configuration workflows personnalisés | SQLModel, JavaScript |

---

## 🔐 SÉCURITÉ

### Authentification
- **JWT** : Tokens avec expiration
- **Cookies httpOnly** : Protection contre XSS
- **bcrypt** : Hachage des mots de passe

### Validation
- **Pydantic** : Validation côté serveur
- **JavaScript** : Validation côté client
- **Exceptions personnalisées** : Messages clairs et traduits

### Protection
- **SQL paramétré** : Protection contre injection SQL
- **CORS** : Configuration stricte en production
- **Dépendances** : `get_current_user` sur toutes les routes protégées

---

## 🎯 FONCTIONNALITÉS CLÉS

### ✅ Workflows Personnalisés
- Création de rôles personnalisés
- Attribution de rôles aux agents
- Templates de workflows configurables
- Types de demandes dynamiques
- Circuit de validation flexible (N+1, N+2, ..., N+6)

### ✅ Gestion de Stock Avancée
- Articles périssables avec dates de péremption
- Alertes automatiques avant péremption
- Amortissement du matériel (linéaire, dégressif)
- Plans d'amortissement complets
- Suivi par lot (FEFO)

### ✅ Gestion RH Complète
- Demandes de congé, mission, formation
- Validation hiérarchique
- Historique complet des validations
- Dashboard avec KPIs dynamiques
- Satisfaction des besoins d'actes

### ✅ Administration Flexible
- Gestion des utilisateurs
- Configuration des paramètres système
- Référentiels (services, grades, programmes)
- Logs d'activité
- Aide contextuelle

---

## 🛠️ TECHNOLOGIES UTILISÉES

### Backend
- **FastAPI** : Framework web moderne et rapide
- **SQLModel** : ORM combinant SQLAlchemy et Pydantic
- **SQLite** : Base de données (production : PostgreSQL recommandé)
- **Uvicorn** : Serveur ASGI haute performance
- **JWT** : Authentification stateless
- **bcrypt** : Hachage de mots de passe

### Frontend
- **Jinja2** : Moteur de templates
- **HTML5** : Structure sémantique
- **CSS3** : Styles modernes (variables CSS, flexbox, grid)
- **JavaScript Vanilla** : Interactivité (Fetch API, async/await)
- **Chart.js** : Graphiques et visualisations

### DevOps
- **Git** : Contrôle de version
- **Python venv** : Environnements virtuels
- **pip** : Gestion des dépendances

---

## 📈 PERFORMANCES

### Backend
- ⚡ Requêtes SQL optimisées avec index
- ⚡ Sessions DB réutilisées (pool de connexions)
- ⚡ Logs structurés avec Request-ID
- ⚡ Temps de réponse moyen : ~100ms

### Frontend
- ⚡ CSS optimisé (pas de framework lourd)
- ⚡ JavaScript asynchrone (pas de blocage)
- ⚡ Templates compilés et mis en cache
- ⚡ Chargement de page : ~160ms

---

## 🧪 TESTS

```bash
# Tests unitaires
pytest tests/

# Tests avec couverture
pytest --cov=app tests/

# Tests d'intégration
pytest tests/integration/
```

---

## 📝 CONVENTIONS DE CODE

### Python
- **PEP 8** : Style guide Python
- **Type hints** : Obligatoires
- **Docstrings** : Pour toutes les fonctions publiques
- **Nommage** :
  - Classes : `PascalCase`
  - Fonctions/Variables : `snake_case`
  - Constantes : `UPPER_SNAKE_CASE`

### SQL
- **Noms de tables** : `snake_case` (ex: `agent_complet`)
- **Clés étrangères** : `<table>_id` (ex: `user_id`)
- **Index** : Sur les colonnes fréquemment recherchées

### Frontend
- **CSS** : BEM ou classes utilitaires
- **JavaScript** : Camel case, JSDoc
- **HTML** : Sémantique, accessibilité (ARIA)

---

## 🐛 DEBUGGING

### Logs
```bash
# Logs en temps réel
tail -f logs/mppeep_YYYYMMDD.log

# Filtrer les erreurs
grep "ERROR" logs/mppeep_YYYYMMDD.log

# Rechercher par Request-ID
grep "xY7k9mN2" logs/mppeep_YYYYMMDD.log
```

### Mode Debug
```python
# Dans app/core/config.py
DEBUG = True

# Dans app/db/session.py
engine = create_engine(
    DATABASE_URL,
    echo=True  # Affiche toutes les requêtes SQL
)
```

### Outils
- **FastAPI Docs** : http://localhost:9000/docs
- **Browser DevTools** : Network, Console, Sources
- **Python Debugger** : `breakpoint()` ou `pdb`

---

## 🤝 CONTRIBUTION

### Processus
1. Créer une branche : `git checkout -b feature/nom-feature`
2. Coder et tester
3. Commit : `git commit -m "feat: description"`
4. Push : `git push origin feature/nom-feature`
5. Créer une Pull Request

### Conventions de commit
- `feat:` Nouvelle fonctionnalité
- `fix:` Correction de bug
- `docs:` Documentation
- `style:` Formatage (pas de changement de code)
- `refactor:` Refactoring
- `test:` Tests
- `chore:` Maintenance

---

## 📞 SUPPORT

### Questions ?
- 📧 Email : support@mppeep.gov
- 📖 Documentation : Ce dossier
- 🐛 Issues : GitHub Issues

### Ressources
- [Documentation FastAPI](https://fastapi.tiangolo.com/)
- [Documentation SQLModel](https://sqlmodel.tiangolo.com/)
- [Documentation Jinja2](https://jinja.palletsprojects.com/)

---

## 📜 LICENCE

© 2025 MPPEEP - Tous droits réservés

---

## 🎓 POUR ALLER PLUS LOIN

### Lectures recommandées
1. **01_DEMARRAGE_APPLICATION.md** - Comprendre le démarrage
2. **02_PARCOURS_REQUETE_CLIENT.md** - Suivre une requête
3. **03_MODULES_DETAILS.md** - Architecture des modèles et services
4. **04_MODULES_FRONTEND_API.md** - Frontend et API

### Prochaines étapes
- [ ] Ajouter des tests unitaires
- [ ] Migrer vers PostgreSQL en production
- [ ] Implémenter le cache Redis
- [ ] Ajouter l'export PDF des rapports
- [ ] Créer une API mobile
- [ ] Internationalisation (i18n)

---

**Bonne lecture et bon développement ! 🚀**

*Dernière mise à jour : 19 octobre 2025*

