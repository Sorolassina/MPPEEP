# 👥 Système de Gestion du Personnel

## Vue d'ensemble

Le module de gestion du personnel est un système complet pour gérer les ressources humaines de la fonction publique, incluant :

- ✅ Gestion complète des agents (CRUD)
- ✅ Structure organisationnelle hiérarchique (Programme → Direction → Service)
- ✅ Grades de la fonction publique (A1-A4, B1-B4, C1-C4, D1-D4)
- ✅ Gestion des documents administratifs
- ✅ Historique de carrière (promotions, mutations, etc.)
- ✅ Évaluations annuelles
- ✅ Suivi des congés annuels

---

## 📊 Architecture des Données

### 1. Structure Organisationnelle

```
Programme (ex: Administration générale)
    ↓
Direction (ex: Direction des Ressources Humaines)
    ↓
Service (ex: Service de la Carrière)
```

### 2. Modèle Agent Complet

Un agent possède :

**Identification**
- Matricule (unique)
- Numéro CNI, Passeport
- Photo

**État Civil**
- Nom, prénom, nom de jeune fille
- Date et lieu de naissance
- Nationalité, sexe
- Situation familiale
- Nombre d'enfants

**Coordonnées**
- Emails (professionnel et personnel)
- Téléphones
- Adresse complète

**Carrière**
- Date de recrutement/prise de service
- Date de départ à la retraite prévue
- Position administrative (en activité, détachement, etc.)
- Grade et échelon
- Indice salarial

**Affectation**
- Programme, Direction, Service
- Fonction occupée
- Lien avec compte utilisateur (optionnel)

**Congés**
- Solde de congés annuels
- Congés alloués cette année

---

## 🎓 Grades de la Fonction Publique

### Catégorie A - Cadres supérieurs
- **A4** : Administrateur civil principal (indices 1200-1400)
- **A3** : Administrateur civil (indices 1000-1199)
- **A2** : Attaché d'administration principal (indices 800-999)
- **A1** : Attaché d'administration (indices 600-799)

### Catégorie B - Cadres moyens
- **B4** : Secrétaire d'administration principal (indices 550-650)
- **B3** : Secrétaire d'administration (indices 480-549)
- **B2** : Contrôleur principal (indices 420-479)
- **B1** : Contrôleur (indices 360-419)

### Catégorie C - Agents d'exécution
- **C4** : Agent administratif principal (indices 330-380)
- **C3** : Agent administratif (indices 290-329)
- **C2** : Commis principal (indices 250-289)
- **C1** : Commis (indices 210-249)

### Catégorie D - Personnel de soutien
- **D4** : Agent de bureau principal (indices 190-220)
- **D3** : Agent de bureau (indices 170-189)
- **D2** : Huissier principal (indices 150-169)
- **D1** : Huissier (indices 130-149)

---

## 📁 Types de Documents

- 🆔 Carte nationale d'identité
- 🛂 Passeport
- 📄 Acte de naissance
- 🎓 Diplôme
- 📜 Certificat
- 📝 Contrat
- 📋 Arrêté de nomination
- ⬆️ Décision d'avancement
- 📊 Fiche de notation
- 🏥 Certificat médical
- ✅ Attestation de travail
- 📎 Autre document

---

## 🚀 Installation et Initialisation

### 1. Créer les tables

```bash
python scripts/migrate_personnel_tables.py
```

### 2. Initialiser les grades

```bash
python scripts/init_grades_fonction_publique.py
```

### 3. Initialiser la structure organisationnelle

```bash
python scripts/init_structure_orga.py
```

---

## 🎯 Fonctionnalités Disponibles

### Gestion des Agents

**Page principale : `/api/v1/personnel/`**

- ✅ Affichage de la liste des agents
- ✅ Recherche en temps réel (matricule, nom, prénom)
- ✅ Statistiques (total agents, actifs, par catégorie)
- ✅ Filtrage et pagination
- ✅ Actions : Voir détails, Modifier, Désactiver

### Fiche Agent

**Page détail : `/api/v1/personnel/{agent_id}`**

- ✅ Informations complètes de l'agent
- ✅ Grade et affectation
- ✅ Liste des documents joints
- ✅ Historique de carrière
- ✅ Évaluations annuelles
- ✅ Solde de congés

### API REST

**GET `/api/v1/personnel/api/agents`**
- Liste des agents avec pagination
- Paramètres : `skip`, `limit`, `search`, `actif`

**POST `/api/v1/personnel/api/agents`**
- Créer un nouvel agent
- Body : JSON avec toutes les informations

**GET `/api/v1/personnel/api/agents/{agent_id}`**
- Récupérer un agent spécifique

**PUT `/api/v1/personnel/api/agents/{agent_id}`**
- Mettre à jour un agent

**DELETE `/api/v1/personnel/api/agents/{agent_id}`**
- Désactiver un agent (soft delete)

**GET `/api/v1/personnel/api/programmes`**
- Liste des programmes

**GET `/api/v1/personnel/api/directions?programme_id=X`**
- Liste des directions (optionnel: filtrées par programme)

**GET `/api/v1/personnel/api/services?direction_id=X`**
- Liste des services (optionnel: filtrés par direction)

**GET `/api/v1/personnel/api/grades?categorie=A`**
- Liste des grades (optionnel: filtrés par catégorie)

**POST `/api/v1/personnel/api/agents/{agent_id}/documents`**
- Uploader un document pour un agent
- Form data: `type_document`, `titre`, `description`, `file`

---

## 💡 Idées d'Améliorations Futures

### Gestion de Carrière
- ✨ Suivi automatique des promotions basé sur l'ancienneté
- ✨ Alertes pour les retraites à venir
- ✨ Gestion des mutations inter-services
- ✨ Tableau de bord carrière par agent

### Gestion des Congés
- ✨ Demandes de congés intégrées au workflow
- ✨ Calcul automatique des soldes
- ✨ Calendrier de planification des congés
- ✨ Gestion des congés de maladie

### Évaluations
- ✨ Formulaires d'évaluation personnalisables
- ✨ Workflow de validation d'évaluation
- ✨ Statistiques et analyses d'évaluations
- ✨ Objectifs SMART par agent

### Formation
- ✨ Catalogue de formations
- ✨ Inscriptions et suivi des formations
- ✨ Certifications obtenues
- ✨ Plan de développement individuel

### Paie
- ✨ Calcul automatique des salaires
- ✨ Bulletins de paie
- ✨ Déclarations sociales
- ✨ Historique des rémunérations

### Présence
- ✨ Pointage (badge, biométrie)
- ✨ Gestion des absences
- ✨ Heures supplémentaires
- ✨ Tableaux de bord de présence

### Sanctions & Récompenses
- ✨ Registre des sanctions disciplinaires
- ✨ Médailles et distinctions
- ✨ Lettres de félicitations
- ✨ Historique des sanctions/récompenses

### Organigramme
- ✨ Visualisation graphique de l'organigramme
- ✨ Arbre hiérarchique interactif
- ✨ Export en PDF
- ✨ Annuaire du personnel

---

## 🔒 Sécurité et Permissions

### Rôles Recommandés

**DRH (Directeur des Ressources Humaines)**
- Accès complet au module personnel
- Création, modification, suppression d'agents
- Gestion des grades et structures
- Accès à tous les documents

**N2 (Chef de Direction)**
- Consultation des agents de sa direction
- Saisie d'évaluations
- Upload de documents

**N1 (Chef de Service)**
- Consultation des agents de son service
- Demandes d'actes administratifs

**AGENT**
- Consultation de sa propre fiche
- Mise à jour de ses coordonnées
- Consultation de ses documents

---

## 📈 Statistiques et Rapports

### Indicateurs Clés (KPI)

- 📊 Effectif total et actif
- 📊 Répartition par catégorie de grade
- 📊 Répartition par service/direction
- 📊 Pyramide des âges
- 📊 Taux de rotation du personnel
- 📊 Ancienneté moyenne
- 📊 Taux d'absentéisme

### Rapports Disponibles

- 📄 Liste nominative du personnel
- 📄 État des effectifs par structure
- 📄 Situation des congés
- 📄 Bilan des formations
- 📄 Synthèse des évaluations
- 📄 Prévisions de départs à la retraite

---

## 🛠️ Technologies Utilisées

- **Backend** : FastAPI, SQLModel, Pydantic
- **Base de données** : SQLite (SQLAlchemy)
- **Frontend** : HTML5, CSS3, JavaScript (Vanilla)
- **Templates** : Jinja2
- **Upload de fichiers** : FastAPI UploadFile
- **Validation** : Pydantic

---

## 📞 Support

Pour toute question ou suggestion d'amélioration, veuillez consulter la documentation ou contacter l'équipe de développement.

---

*Dernière mise à jour : Octobre 2025*

