# 🚀 BIENVENUE DANS LA DOCUMENTATION MPPEEP DASHBOARD

## 📖 Par où commencer ?

Vous êtes nouveau sur le projet MPPEEP Dashboard ? Ce guide vous orientera vers les bons documents selon votre profil et vos besoins.

---

## 👤 Quel est votre profil ?

### 🎓 Je découvre le projet (Manager, Product Owner, Testeur)

**Commencez ici** :
1. **[../README.md](../README.md)** - README principal de l'application (15 min)
   - Vue d'ensemble du projet
   - Fonctionnalités principales
   - Technologies utilisées
   
2. **[README.md](README.md)** - Index de la documentation (10 min)
   - Vue d'ensemble des documents
   - Structure du projet
   
3. **[05_ARCHITECTURE_COMPLETE.md](05_ARCHITECTURE_COMPLETE.md)** - Diagrammes et schémas (30 min)
   - Architecture globale
   - Flux de données
   - Schéma de base de données

**📚 Total : ~1 heure**

---

### 👨‍💻 Je suis développeur Backend

**Parcours recommandé** :

1. **[../README.md](../README.md)** - Installation et démarrage (20 min)
   
2. **[01_DEMARRAGE_APPLICATION.md](01_DEMARRAGE_APPLICATION.md)** - Démarrage complet (30 min)
   - Chargement des modules
   - Initialisation DB
   - Configuration FastAPI
   
3. **[02_PARCOURS_REQUETE_CLIENT.md](02_PARCOURS_REQUETE_CLIENT.md)** - Flux requête → réponse (40 min)
   - Middlewares
   - Routage
   - Dépendances
   - Services
   
4. **[03_MODULES_DETAILS.md](03_MODULES_DETAILS.md)** - Modèles et services (60 min)
   - SQLModel
   - Services métier
   - Workflow personnalisé
   
5. **[04_MODULES_FRONTEND_API.md](04_MODULES_FRONTEND_API.md)** - Endpoints API (50 min)
   - Routes détaillées
   - Exemples de code
   
6. **[05_ARCHITECTURE_COMPLETE.md](05_ARCHITECTURE_COMPLETE.md)** - Architecture (40 min)
   - Schémas complets
   - Relations DB

**📚 Total : ~4 heures**

---

### 🎨 Je suis développeur Frontend

**Parcours recommandé** :

1. **[../README.md](../README.md)** - Installation et démarrage (20 min)
   
2. **[04_MODULES_FRONTEND_API.md](04_MODULES_FRONTEND_API.md)** - Templates et API (50 min)
   - Templates Jinja2
   - CSS/JavaScript
   - Composants réutilisables
   
3. **[02_PARCOURS_REQUETE_CLIENT.md](02_PARCOURS_REQUETE_CLIENT.md)** - Rendu des pages (30 min)
   - Comment les templates sont rendus
   - Chargement des ressources
   
4. **[05_ARCHITECTURE_COMPLETE.md](05_ARCHITECTURE_COMPLETE.md)** - Flux de données (20 min)
   - Comprendre les flux
   - États et cycles de vie

**📚 Total : ~2 heures**

---

### 🔧 Je configure l'infrastructure (DevOps, SysAdmin)

**Parcours recommandé** :

1. **[../README.md](../README.md)** - Installation et configuration (30 min)
   - Prérequis
   - Variables d'environnement
   - Démarrage
   
2. **[01_DEMARRAGE_APPLICATION.md](01_DEMARRAGE_APPLICATION.md)** - Initialisation (30 min)
   - Base de données
   - Middlewares
   - Configuration
   
3. **[DEPLOYMENT.md](DEPLOYMENT.md)** - Déploiement (si existe)
   
4. **[../tests/README.md](../tests/README.md)** - Tests CI/CD (20 min)
   - Tests critiques
   - Configuration pytest

**📚 Total : ~1h30**

---

### 🐛 Je débogue un problème

**Guide de dépannage rapide** :

#### Problème de démarrage
→ **[01_DEMARRAGE_APPLICATION.md](01_DEMARRAGE_APPLICATION.md)** - Section "Logs Console Typiques"

#### Erreur 401 (Non authentifié)
→ **[04_MODULES_FRONTEND_API.md](04_MODULES_FRONTEND_API.md)** - Section "Authentification"

#### Erreur 422 (Validation)
→ **[02_PARCOURS_REQUETE_CLIENT.md](02_PARCOURS_REQUETE_CLIENT.md)** - Section "Gestionnaire d'Exception"

#### Workflow ne fonctionne pas
→ **[03_MODULES_DETAILS.md](03_MODULES_DETAILS.md)** - Section "HierarchyService"
→ **[05_ARCHITECTURE_COMPLETE.md](05_ARCHITECTURE_COMPLETE.md)** - Section "Workflow Personnalisé"

#### Performance lente
→ **[02_PARCOURS_REQUETE_CLIENT.md](02_PARCOURS_REQUETE_CLIENT.md)** - Section "Métriques de Performance"

---

## 📚 TOUS LES DOCUMENTS

| Document | Description | Niveau | Durée |
|----------|-------------|--------|-------|
| **[../README.md](../README.md)** | README principal de l'application | Tous | 15 min |
| **[README.md](README.md)** | Index de la documentation | Tous | 10 min |
| **[INDEX.md](INDEX.md)** | Navigation par mot-clé | Référence | - |
| **[01_DEMARRAGE_APPLICATION.md](01_DEMARRAGE_APPLICATION.md)** | Démarrage complet | Débutant | 30 min |
| **[02_PARCOURS_REQUETE_CLIENT.md](02_PARCOURS_REQUETE_CLIENT.md)** | Flux requête HTTP | Intermédiaire | 40 min |
| **[03_MODULES_DETAILS.md](03_MODULES_DETAILS.md)** | Modèles et services | Avancé | 60 min |
| **[04_MODULES_FRONTEND_API.md](04_MODULES_FRONTEND_API.md)** | API et templates | Intermédiaire | 50 min |
| **[05_ARCHITECTURE_COMPLETE.md](05_ARCHITECTURE_COMPLETE.md)** | Architecture globale | Tous | 40 min |

**Temps total de lecture** : ~4h30

---

## 🎯 Objectifs par document

### 01_DEMARRAGE_APPLICATION.md
**Vous apprendrez** :
- Comment l'application démarre
- Quelles fonctions sont appelées
- Comment la base de données est initialisée
- Comment accéder à la page de login

### 02_PARCOURS_REQUETE_CLIENT.md
**Vous apprendrez** :
- Le parcours complet d'une requête HTTP
- Comment les middlewares fonctionnent
- Comment l'authentification est vérifiée
- Comment un template est rendu

### 03_MODULES_DETAILS.md
**Vous apprendrez** :
- La structure des modèles de données
- Comment les services encapsulent la logique métier
- Comment le workflow personnalisé fonctionne
- Exemples de code complets

### 04_MODULES_FRONTEND_API.md
**Vous apprendrez** :
- Comment créer une nouvelle route API
- Comment structurer un template Jinja2
- Comment organiser le CSS/JavaScript
- Bonnes pratiques frontend

### 05_ARCHITECTURE_COMPLETE.md
**Vous apprendrez** :
- L'architecture globale du système
- Les schémas de base de données
- Les flux de données
- Les patterns utilisés

---

## 🔎 Recherche Rapide

### Je cherche...

**"Comment créer une nouvelle route API ?"**
→ [04_MODULES_FRONTEND_API.md](04_MODULES_FRONTEND_API.md) - Section "API Endpoints"

**"Comment fonctionne l'authentification JWT ?"**
→ [02_PARCOURS_REQUETE_CLIENT.md](02_PARCOURS_REQUETE_CLIENT.md) - Phase 4
→ [04_MODULES_FRONTEND_API.md](04_MODULES_FRONTEND_API.md) - Section "auth.py"

**"Comment créer un nouveau modèle SQLModel ?"**
→ [03_MODULES_DETAILS.md](03_MODULES_DETAILS.md) - Section "Models"

**"Comment configurer un workflow personnalisé ?"**
→ [03_MODULES_DETAILS.md](03_MODULES_DETAILS.md) - Section "workflow_config.py"
→ [05_ARCHITECTURE_COMPLETE.md](05_ARCHITECTURE_COMPLETE.md) - Section "Workflow Personnalisé"

**"Comment gérer les articles périssables ?"**
→ [03_MODULES_DETAILS.md](03_MODULES_DETAILS.md) - Section "stock.py"
→ [05_ARCHITECTURE_COMPLETE.md](05_ARCHITECTURE_COMPLETE.md) - Section "Flux - Lots périssables"

**"Comment calculer l'amortissement ?"**
→ [03_MODULES_DETAILS.md](03_MODULES_DETAILS.md) - Section "StockService"

---

## 📊 Résumé Visuel

```
START HERE
    │
    ├─ 🎓 Débutant / Manager
    │   └─→ README.md → 05_ARCHITECTURE_COMPLETE.md
    │
    ├─ 👨‍💻 Backend Developer
    │   └─→ 01 → 02 → 03 → 04 → 05
    │
    ├─ 🎨 Frontend Developer
    │   └─→ 04 → 02 → 05
    │
    ├─ 🔧 DevOps
    │   └─→ README.md → 01 → Tests/README.md
    │
    └─ 🐛 Debugging
        └─→ INDEX.md (recherche par mot-clé)
```

---

## ✅ Checklist de Compréhension

Après avoir lu la documentation, vous devriez pouvoir :

- [ ] Expliquer comment l'application démarre
- [ ] Tracer une requête HTTP de bout en bout
- [ ] Comprendre le système de workflow personnalisé
- [ ] Créer un nouveau modèle SQLModel
- [ ] Créer une nouvelle route API
- [ ] Créer un nouveau template Jinja2
- [ ] Comprendre les mécanismes de sécurité
- [ ] Configurer un environnement de développement
- [ ] Lancer les tests critiques
- [ ] Lire et comprendre les logs

---

## 🎯 Prochaines Étapes

Après la lecture :

1. **Pratiquer** : Cloner le projet et l'installer localement
2. **Explorer** : Naviguer dans le code avec les exemples
3. **Modifier** : Faire une petite modification et voir l'effet
4. **Tester** : Lancer les tests et voir les résultats
5. **Contribuer** : Créer votre première Pull Request !

---

**Bonne lecture et bienvenue dans l'équipe MPPEEP ! 🎉**

📧 Questions ? Consultez l'[INDEX.md](INDEX.md) ou contactez l'équipe technique.

