# 📑 Index de la Documentation MPPEEP

## 🔍 Navigation Rapide

### Par Sujet

#### 🚀 Démarrage et Configuration
- [Démarrage de l'application](01_DEMARRAGE_APPLICATION.md#-vue-densemble)
- [Configuration des middlewares](01_DEMARRAGE_APPLICATION.md#-6-enregistrement-des-middlewares)
- [Initialisation de la base de données](01_DEMARRAGE_APPLICATION.md#-3-initialisation-de-la-base-de-données)
- [Variables d'environnement](03_MODULES_DETAILS.md#appcoreconfig py)

#### 🔐 Authentification et Sécurité
- [Système de login](01_DEMARRAGE_APPLICATION.md#-10-accès-à-la-page-login)
- [JWT et cookies](04_MODULES_FRONTEND_API.md#fichier-appapiv1endpointsauthpy)
- [Hachage des mots de passe](03_MODULES_DETAILS.md#appcoresecuritypy)
- [Protection des routes](04_MODULES_FRONTEND_API.md#utilisation-dans-dautres-routes)

#### 🔄 Flux de requêtes
- [Parcours complet d'une requête](02_PARCOURS_REQUETE_CLIENT.md#-vue-densemble)
- [Middlewares](02_PARCOURS_REQUETE_CLIENT.md#-phase-2--middlewares-traitement-pré-route)
- [Routage](02_PARCOURS_REQUETE_CLIENT.md#-phase-3--routage)
- [Dépendances](02_PARCOURS_REQUETE_CLIENT.md#-phase-4--résolution-des-dépendances)
- [Rendu des templates](02_PARCOURS_REQUETE_CLIENT.md#-phase-6--rendu-du-template-jinja2)

#### 🏗️ Architecture
- [Structure globale du projet](README.md#-structure-du-projet)
- [Architecture des routes](04_MODULES_FRONTEND_API.md#architecture-des-routes)
- [Architecture des templates](04_MODULES_FRONTEND_API.md#architecture-des-templates)
- [Organisation des services](03_MODULES_DETAILS.md#-module-4--services-logique-métier)

#### 💾 Base de données et Modèles
- [Configuration SQLModel](03_MODULES_DETAILS.md#-module-2--database-base-de-données)
- [Modèle User](03_MODULES_DETAILS.md#appmodelsuserpy)
- [Modèle Agent](03_MODULES_DETAILS.md#appmodelspersonnelpy)
- [Modèle HRRequest](03_MODULES_DETAILS.md#appmodelsrhpy)
- [Modèle Article](03_MODULES_DETAILS.md#appmodelsstockpy)
- [Workflow personnalisé](03_MODULES_DETAILS.md#appmodelsworkflow_configpy)

#### 📋 Modules Métier
- [Module RH](04_MODULES_FRONTEND_API.md#fichier-appapiv1endpointsrhpy)
- [Module Stock](04_MODULES_FRONTEND_API.md#fichier-appapiv1endpointsstockpy)
- [Module Personnel](README.md#-modules-principaux)
- [Module Budget](README.md#-modules-principaux)
- [Module Performance](README.md#-modules-principaux)

#### 🎨 Frontend
- [Templates Jinja2](04_MODULES_FRONTEND_API.md#-module-6--templates-htmljinja2)
- [Layout de base](04_MODULES_FRONTEND_API.md#fichier-apptemplatelayoutsbasehtml)
- [Composants réutilisables](04_MODULES_FRONTEND_API.md#fichier-apptemplatecomponentspage_headerhtml)
- [CSS globaux](04_MODULES_FRONTEND_API.md#fichier-appstaticcsstylecss)
- [JavaScript global](04_MODULES_FRONTEND_API.md#fichier-appstaticjsappjs)

#### 🔧 Services et Logique Métier
- [RHService](03_MODULES_DETAILS.md#appservicesrhpy)
- [HierarchyService](03_MODULES_DETAILS.md#appserviceshierarchy_servicepy)
- [StockService](03_MODULES_DETAILS.md#appservicesstock_servicepy)
- [Workflow Config Service](03_MODULES_DETAILS.md#appservicesworkflow_config_servicepy)

#### 🍃 Fonctionnalités Avancées
- [Articles périssables](03_MODULES_DETAILS.md#appmodelsstockpy)
- [Amortissement](03_MODULES_DETAILS.md#appmodelsstockpy)
- [Workflows personnalisés](03_MODULES_DETAILS.md#appmodelsworkflow_configpy)
- [Validation hiérarchique](03_MODULES_DETAILS.md#appserviceshierarchy_servicepy)

---

## 📖 Par Document

### 📘 01_DEMARRAGE_APPLICATION.md
**Thème** : Du lancement à la page de login

**Chapitres** :
1. Lancement de l'application
2. Chargement du module principal
3. Initialisation de la base de données
4. Création de l'instance FastAPI
5. Configuration des fichiers statiques
6. Enregistrement des middlewares
7. Enregistrement des routes
8. Gestionnaire d'exception personnalisé
9. Route racine et redirection
10. Accès à la page login
11. Rendu final dans le navigateur
12. Résumé du flux complet

**Concepts clés** :
- ASGI, Uvicorn
- FastAPI
- SQLModel
- Jinja2
- Middleware
- Lifespan Events

---

### 📘 02_PARCOURS_REQUETE_CLIENT.md
**Thème** : De la requête à la réponse

**Phases** :
1. Réception de la requête
2. Middlewares (pré-traitement)
3. Routage
4. Résolution des dépendances
5. Exécution de la route
6. Rendu du template
7. Construction de la réponse
8. Envoi de la réponse
9. Rendu dans le navigateur
10. Page affichée

**Exemple suivi** :
`GET /api/v1/rh/demandes/new`

**Durées typiques** :
- Serveur : ~110ms
- Navigateur : ~50ms
- **Total : ~160ms**

---

### 📘 03_MODULES_DETAILS.md
**Thème** : Architecture et modèles

**Modules couverts** :
1. **CORE** : Configuration, sécurité, enums, logging
2. **DATABASE** : Session, connexion, création des tables
3. **MODELS** : User, Agent, HRRequest, Article, Workflow, etc.
4. **SERVICES** : RH, Hierarchy, Stock, Workflow Config

**Points forts** :
- Exemples de code complets
- Requêtes SQL détaillées
- Explication des relations
- Validation Pydantic

---

### 📘 04_MODULES_FRONTEND_API.md
**Thème** : API et interface utilisateur

**Modules couverts** :
5. **API ENDPOINTS** : Routes FastAPI (auth, rh, stock, etc.)
6. **TEMPLATES** : Jinja2, layouts, composants
7. **STATIC** : CSS, JavaScript, assets

**Exemples inclus** :
- Routes d'authentification complètes
- Création de demande RH
- Gestion de stock avancée
- Templates avec macros
- CSS organisé
- JavaScript utilitaires

---

### 📘 README.md
**Thème** : Vue d'ensemble et démarrage rapide

**Contenu** :
- Vue d'ensemble des 4 documents
- Structure du projet
- Démarrage rapide
- Modules principaux
- Sécurité
- Fonctionnalités clés
- Technologies utilisées
- Performances
- Tests
- Conventions de code
- Debugging
- Contribution
- Support

---

## 🎯 Par Niveau

### 👶 Débutant
**Objectif** : Comprendre les bases et démarrer

1. [README.md](README.md) - Vue d'ensemble
2. [Démarrage rapide](README.md#-démarrage-rapide)
3. [Structure du projet](README.md#-structure-du-projet)
4. [Démarrage de l'application](01_DEMARRAGE_APPLICATION.md)
5. [Concepts clés](01_DEMARRAGE_APPLICATION.md#-concepts-clés)

**Durée** : 1-2 heures

---

### 🧑‍💻 Intermédiaire
**Objectif** : Comprendre le flux et l'architecture

1. [Parcours d'une requête](02_PARCOURS_REQUETE_CLIENT.md)
2. [Modèles de base](03_MODULES_DETAILS.md#-module-3--models-modèles-de-données)
3. [Services principaux](03_MODULES_DETAILS.md#-module-4--services-logique-métier)
4. [Routes API](04_MODULES_FRONTEND_API.md#-module-5--api-endpoints-routes)
5. [Templates](04_MODULES_FRONTEND_API.md#-module-6--templates-htmljinja2)

**Durée** : 3-4 heures

---

### 🚀 Avancé
**Objectif** : Maîtriser l'architecture complète

1. Tous les documents dans l'ordre
2. [Workflows personnalisés](03_MODULES_DETAILS.md#appmodelsworkflow_configpy)
3. [HierarchyService complet](03_MODULES_DETAILS.md#appserviceshierarchy_servicepy)
4. [Gestion de stock avancée](03_MODULES_DETAILS.md#appservicesstock_servicepy)
5. [Sécurité](README.md#-sécurité)
6. [Performances](README.md#-performances)

**Durée** : 6-8 heures

---

## 🔎 Recherche par Mot-clé

### A
- **Amortissement** : [03_MODULES_DETAILS.md](03_MODULES_DETAILS.md#appmodelsstockpy)
- **Authentification** : [04_MODULES_FRONTEND_API.md](04_MODULES_FRONTEND_API.md#fichier-appapiv1endpointsauthpy)
- **API** : [04_MODULES_FRONTEND_API.md](04_MODULES_FRONTEND_API.md#-module-5--api-endpoints-routes)

### B
- **bcrypt** : [03_MODULES_DETAILS.md](03_MODULES_DETAILS.md#appcoresecuritypy)
- **Base de données** : [03_MODULES_DETAILS.md](03_MODULES_DETAILS.md#-module-2--database-base-de-données)

### C
- **CSS** : [04_MODULES_FRONTEND_API.md](04_MODULES_FRONTEND_API.md#fichier-appstaticcsstylecss)
- **Configuration** : [03_MODULES_DETAILS.md](03_MODULES_DETAILS.md#appcoreconfig py)
- **Cookie** : [04_MODULES_FRONTEND_API.md](04_MODULES_FRONTEND_API.md#fichier-appapiv1endpointsauthpy)

### D
- **Dépendances** : [02_PARCOURS_REQUETE_CLIENT.md](02_PARCOURS_REQUETE_CLIENT.md#-phase-4--résolution-des-dépendances)
- **Debugging** : [README.md](README.md#-debugging)

### E
- **Enums** : [03_MODULES_DETAILS.md](03_MODULES_DETAILS.md#appcoreenumspy)

### F
- **FastAPI** : [01_DEMARRAGE_APPLICATION.md](01_DEMARRAGE_APPLICATION.md#-4-création-de-linstance-fastapi)

### H
- **HierarchyService** : [03_MODULES_DETAILS.md](03_MODULES_DETAILS.md#appserviceshierarchy_servicepy)

### J
- **Jinja2** : [04_MODULES_FRONTEND_API.md](04_MODULES_FRONTEND_API.md#-module-6--templates-htmljinja2)
- **JWT** : [04_MODULES_FRONTEND_API.md](04_MODULES_FRONTEND_API.md#fichier-appapiv1endpointsauthpy)

### L
- **Logging** : [03_MODULES_DETAILS.md](03_MODULES_DETAILS.md#appcorelogging_configpy)
- **Lot périssable** : [03_MODULES_DETAILS.md](03_MODULES_DETAILS.md#appmodelsstockpy)

### M
- **Middleware** : [01_DEMARRAGE_APPLICATION.md](01_DEMARRAGE_APPLICATION.md#-6-enregistrement-des-middlewares)
- **Modèles** : [03_MODULES_DETAILS.md](03_MODULES_DETAILS.md#-module-3--models-modèles-de-données)

### P
- **Péremption** : [03_MODULES_DETAILS.md](03_MODULES_DETAILS.md#appmodelsstockpy)
- **Performance** : [README.md](README.md#-performances)

### R
- **Routes** : [04_MODULES_FRONTEND_API.md](04_MODULES_FRONTEND_API.md#architecture-des-routes)
- **RHService** : [03_MODULES_DETAILS.md](03_MODULES_DETAILS.md#appservicesrhpy)

### S
- **Sécurité** : [README.md](README.md#-sécurité)
- **Services** : [03_MODULES_DETAILS.md](03_MODULES_DETAILS.md#-module-4--services-logique-métier)
- **SQLModel** : [03_MODULES_DETAILS.md](03_MODULES_DETAILS.md#architecture-sqlmodel)
- **Stock** : [04_MODULES_FRONTEND_API.md](04_MODULES_FRONTEND_API.md#fichier-appapiv1endpointsstockpy)

### T
- **Templates** : [04_MODULES_FRONTEND_API.md](04_MODULES_FRONTEND_API.md#-module-6--templates-htmljinja2)

### U
- **Uvicorn** : [01_DEMARRAGE_APPLICATION.md](01_DEMARRAGE_APPLICATION.md#-1-lancement-de-lapplication)

### W
- **Workflow** : [03_MODULES_DETAILS.md](03_MODULES_DETAILS.md#appmodelsworkflow_configpy)

---

## 🗺️ Parcours de Lecture Recommandés

### 📍 Parcours "Je découvre le projet"
1. [README.md](README.md) - 15 min
2. [01_DEMARRAGE_APPLICATION.md](01_DEMARRAGE_APPLICATION.md) - 30 min
3. [Structure du projet](README.md#-structure-du-projet) - 10 min
4. **Total** : ~1 heure

### 📍 Parcours "Je développe du backend"
1. [README.md](README.md) - 15 min
2. [02_PARCOURS_REQUETE_CLIENT.md](02_PARCOURS_REQUETE_CLIENT.md) - 40 min
3. [03_MODULES_DETAILS.md](03_MODULES_DETAILS.md) - 60 min
4. [API Endpoints](04_MODULES_FRONTEND_API.md#-module-5--api-endpoints-routes) - 30 min
5. **Total** : ~2h30

### 📍 Parcours "Je développe du frontend"
1. [README.md](README.md) - 15 min
2. [Templates](04_MODULES_FRONTEND_API.md#-module-6--templates-htmljinja2) - 30 min
3. [CSS/JS](04_MODULES_FRONTEND_API.md#-module-7--static-cssjs) - 20 min
4. [Parcours d'une requête](02_PARCOURS_REQUETE_CLIENT.md) - 40 min
5. **Total** : ~2 heures

### 📍 Parcours "Je configure l'infrastructure"
1. [README.md](README.md) - 15 min
2. [Démarrage de l'application](01_DEMARRAGE_APPLICATION.md) - 30 min
3. [Configuration](03_MODULES_DETAILS.md#appcoreconfig py) - 15 min
4. [Base de données](03_MODULES_DETAILS.md#-module-2--database-base-de-données) - 20 min
5. [Debugging](README.md#-debugging) - 10 min
6. **Total** : ~1h30

---

## 📊 Statistiques de la Documentation

- **Documents principaux** : 5
- **Pages totales** : ~150 pages
- **Exemples de code** : 100+
- **Diagrammes** : 10+
- **Temps de lecture total** : 6-8 heures
- **Dernière mise à jour** : 19 octobre 2025

---

## 🔗 Liens Rapides

### Documentation Externe
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [Jinja2](https://jinja.palletsprojects.com/)
- [Pydantic](https://docs.pydantic.dev/)

### Fichiers Clés du Projet
- [main.py](../app/main.py)
- [router.py](../app/api/v1/router.py)
- [config.py](../app/core/config.py)
- [session.py](../app/db/session.py)

---

**Bonne navigation ! 📖**

