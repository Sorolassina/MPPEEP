"""
Service RAG (Retrieval Augmented Generation) pour le chatbot
Récupère des informations pertinentes de la base de données selon la question
"""

from sqlmodel import Session, select, or_, and_
from typing import Any
import re

from app.core.logging_config import get_logger
from app.models.performance import (
    ObjectifPerformance,
    IndicateurPerformance,
    OrientationStrategique,
    ResultatStrategique,
)
from app.models.personnel import Programme, Direction, Service
from app.models.user import User

logger = get_logger(__name__)


class ChatbotRAGService:
    """Service pour récupérer des données pertinentes de la base de données"""
    
    @staticmethod
    def extract_keywords(query: str) -> list[str]:
        """Extrait les mots-clés importants de la requête"""
        # Mots-clés liés aux différents domaines
        keywords = []
        
        # Normaliser la requête
        query_lower = query.lower()
        
        # Domaines
        if any(word in query_lower for word in ['performance', 'objectif', 'indicateur', 'kpi']):
            keywords.append('performance')
        if any(word in query_lower for word in ['programme', 'direction', 'service', 'structure']):
            keywords.append('structure')
        if any(word in query_lower for word in ['personnel', 'agent', 'employé', 'effectif']):
            keywords.append('personnel')
        if any(word in query_lower for word in ['budget', 'finance', 'coût', 'dépense']):
            keywords.append('budget')
        
        # Extraire les mots significatifs (plus de 3 caractères)
        words = re.findall(r'\b\w{4,}\b', query_lower)
        keywords.extend(words[:5])  # Limiter à 5 mots-clés
        
        return list(set(keywords))
    
    @staticmethod
    def get_performance_context(session: Session, query: str) -> str:
        """Récupère le contexte lié à la performance"""
        context_parts = []
        
        try:
            # Rechercher dans les objectifs
            query_lower = query.lower()
            objectifs = session.exec(
                select(ObjectifPerformance)
                .where(ObjectifPerformance.actif == True)
                .limit(10)
            ).all()
            
            if objectifs:
                context_parts.append("=== OBJECTIFS DE PERFORMANCE ===")
                for obj in objectifs[:3]:  # Limiter à 3 pour réduire la taille
                    if any(word in obj.titre.lower() for word in query_lower.split()[:3]):
                        desc = (obj.description or 'Sans description')[:100]  # Limiter la description
                        context_parts.append(f"- {obj.titre}: {desc}")
                        context_parts.append(f"  Statut: {obj.statut}, Progression: {obj.progression_pourcentage}%")
            
            # Rechercher dans les indicateurs
            indicateurs = session.exec(
                select(IndicateurPerformance)
                .where(IndicateurPerformance.actif == True)
                .limit(10)
            ).all()
            
            if indicateurs:
                context_parts.append("\n=== INDICATEURS DE PERFORMANCE ===")
                for ind in indicateurs[:3]:  # Limiter à 3
                    if any(word in ind.nom.lower() for word in query_lower.split()[:3]):
                        desc = (ind.description or 'Sans description')[:100]  # Limiter la description
                        context_parts.append(f"- {ind.nom}: {desc}")
                        context_parts.append(f"  Valeur: {ind.valeur_actuelle} {ind.unite or ''}")
            
            # Rechercher dans les orientations stratégiques
            orientations = session.exec(
                select(OrientationStrategique)
                .where(OrientationStrategique.actif == True)
                .limit(5)
            ).all()
            
            if orientations:
                context_parts.append("\n=== ORIENTATIONS STRATÉGIQUES ===")
                for orient in orientations[:3]:  # Limiter à 3
                    context_parts.append(f"- {orient.libelle}")
                    if orient.description:
                        context_parts.append(f"  {orient.description[:150]}...")  # Réduire la taille
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du contexte performance: {e}")
        
        return "\n".join(context_parts)
    
    @staticmethod
    def get_structure_context(session: Session, query: str) -> str:
        """Récupère le contexte lié à la structure organisationnelle"""
        context_parts = []
        
        try:
            query_lower = query.lower()
            
            # Programmes
            programmes = session.exec(
                select(Programme)
                .where(Programme.actif == True)
                .limit(10)
            ).all()
            
            if programmes:
                context_parts.append("=== PROGRAMMES ===")
                for prog in programmes[:3]:  # Limiter à 3
                    if any(word in prog.libelle.lower() for word in query_lower.split()[:3]):
                        context_parts.append(f"- {prog.code}: {prog.libelle}")
                        if prog.description:
                            context_parts.append(f"  {prog.description[:100]}...")  # Réduire la taille
            
            # Directions
            directions = session.exec(
                select(Direction)
                .where(Direction.actif == True)
                .limit(10)
            ).all()
            
            if directions:
                context_parts.append("\n=== DIRECTIONS ===")
                for dir in directions[:5]:
                    if any(word in dir.libelle.lower() for word in query_lower.split()[:3]):
                        context_parts.append(f"- {dir.code}: {dir.libelle}")
            
            # Services
            services = session.exec(
                select(Service)
                .where(Service.actif == True)
                .limit(10)
            ).all()
            
            if services:
                context_parts.append("\n=== SERVICES ===")
                for serv in services[:5]:
                    if any(word in serv.libelle.lower() for word in query_lower.split()[:3]):
                        context_parts.append(f"- {serv.code}: {serv.libelle}")
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du contexte structure: {e}")
        
        return "\n".join(context_parts)
    
    @staticmethod
    def get_modules_info() -> str:
        """Retourne les informations sur les modules disponibles"""
        return """=== MODULES DISPONIBLES DANS SYGEP ===

1. MODULE RH (Ressources Humaines)
   - Gestion des demandes: congés, missions, formations
   - Workflows personnalisés avec validation hiérarchique
   - Suivi et historique des demandes
   - Accès: Page d'accueil → "Gestion des ressources humaines"

2. MODULE PERSONNEL
   - Gestion des agents et de leurs informations
   - Grades et catégories
   - Structure organisationnelle (Programmes, Directions, Services)
   - Documents et carrière
   - Accès: Via le module RH ou les paramètres système

3. MODULE PERFORMANCE
   - Objectifs de performance (stratégiques, opérationnels, financiers, RH, qualité, client)
   - Indicateurs de performance (KPIs)
   - Orientations stratégiques et résultats stratégiques
   - Rapports et tableaux de bord
   - Accès: Page d'accueil → "Suivi de la performance"
   - Actions disponibles dans le module:
     * "Orientations stratégiques" - Gérer les orientations
     * "Résultats stratégiques" - Gérer les résultats
     * "Gérer les objectifs" - Créer/modifier des objectifs
     * "Configurer les indicateurs" - Créer/modifier des indicateurs
     * "Générer un rapport" - Créer des rapports de performance

4. MODULE BUDGET
   - SIGOBE (Système Intégré de Gestion des Opérations Budgétaires et Économiques)
   - Fiches hiérarchiques budgétaires
   - Programmes budgétaires
   - Rapports et exports
   - Accès: Page d'accueil → "Suivi-exécution budgétaire"

5. MODULE STOCK
   - Articles et catégories
   - Lots périssables avec dates d'expiration
   - Amortissement du matériel
   - Mouvements (entrées, sorties, transferts)
   - Inventaires
   - Fournisseurs
   - Accès: Page d'accueil → "Gestion des stocks"

6. MODULE RÉFÉRENTIELS (Organisation)
   - Services
   - Grades
   - Programmes
   - Directions
   - Accès: Paramètres système → "Organisation"

7. MODULE WORKFLOWS
   - Configuration des workflows personnalisés
   - Rôles personnalisés
   - Templates de workflows
   - Types de demandes
   - Accès: Paramètres système → "Workflows"

8. MODULE MESSAGERIE
   - Communication entre utilisateurs
   - Conversations et messages
   - Accès: Bouton flottant de messagerie en bas à droite de l'écran
"""
    
    @staticmethod
    def get_creation_guide(query: str) -> str:
        """Retourne un guide de création ou d'aide basé sur la question"""
        query_lower = query.lower()
        
        # Actions communes - détection plus flexible
        action_verbs = ['créer', 'créer', 'ajouter', 'faire', 'comment', 'comment faire', 'procédure', 'processus', 'étapes', 'étapes']
        has_action = any(verb in query_lower for verb in action_verbs)
        has_modify = any(word in query_lower for word in ['modifier', 'éditer', 'changer', 'mettre à jour', 'mise à jour'])
        has_delete = any(word in query_lower for word in ['supprimer', 'effacer', 'retirer', 'enlever', 'suppression'])
        has_view = any(word in query_lower for word in ['voir', 'consulter', 'afficher', 'lister', 'liste', 'affiche'])
        has_report = any(word in query_lower for word in ['rapport', 'générer', 'exporter', 'télécharger', 'export'])
        has_question = any(word in query_lower for word in ['quoi', 'qu\'est', 'qu\'est-ce', 'définition', 'expliquer', 'explique'])
        
        # ========== MODULE PERFORMANCE ==========
        if 'indicateur' in query_lower and has_action:
            return """=== GUIDE DE CRÉATION D'UN INDICATEUR DE PERFORMANCE ===

ÉTAPES DE NAVIGATION:
1. Allez sur la page d'accueil
2. Cliquez sur "Suivi de la performance" dans la section "Modules disponibles"
3. Dans la page Performance, cliquez sur "Configurer les indicateurs" dans la section "Actions rapides"
4. Cliquez sur le bouton "➕ Nouvel Indicateur"

CHAMPS DU FORMULAIRE (dans l'ordre):
- Objectif associé * (OBLIGATOIRE): Un indicateur doit être rattaché à un objectif de performance existant
- Nom de l'indicateur * (OBLIGATOIRE): Nom descriptif de l'indicateur (max 200 caractères)
- Description (optionnel): Description détaillée de l'indicateur
- Catégorie (optionnel): Qualité, Efficacité, Financier, RH, Opérationnel
- Fréquence de mesure (optionnel): Journalier, Hebdomadaire, Mensuel, Trimestriel, Annuel
- Valeur cible * (OBLIGATOIRE): La valeur cible à atteindre (nombre décimal)
- Valeur actuelle (optionnel): La valeur actuelle (par défaut: 0)
- Unité * (OBLIGATOIRE): Unité de mesure (%, €, h, unités, etc.)
- Seuil alerte min (optionnel): Valeur minimale déclenchant une alerte
- Seuil alerte max (optionnel): Valeur maximale déclenchant une alerte
- Service responsable (optionnel): Service en charge de l'indicateur
- Responsable * (OBLIGATOIRE): Personne responsable de l'indicateur (sélectionné après le service)
- Source des données (optionnel): Origine des données (ex: Système, Enquêtes, Comptabilité)
- Commentaires (optionnel): Notes complémentaires

IMPORTANT: 
- Les champs marqués * sont obligatoires
- Un indicateur DOIT être lié à un objectif de performance existant
- Si aucun objectif n'existe, il faut d'abord créer un objectif"""

        if 'objectif' in query_lower and has_action:
            return """=== GUIDE DE CRÉATION D'UN OBJECTIF DE PERFORMANCE ===

ÉTAPES DE NAVIGATION:
1. Allez sur la page d'accueil
2. Cliquez sur "Suivi de la performance" dans la section "Modules disponibles"
3. Dans la page Performance, cliquez sur "Gérer les objectifs" dans la section "Actions rapides"
4. Cliquez sur le bouton pour créer un nouvel objectif

INFORMATIONS IMPORTANTES:
- Un objectif peut être de type: Stratégique, Opérationnel, Financier, RH, Qualité, Client
- Un objectif stratégique peut être lié à un résultat stratégique
- Un objectif opérationnel peut être lié à un objectif global (stratégique)
- Les objectifs ont des dates de début et de fin
- Les objectifs ont une valeur cible et une valeur actuelle avec une unité"""

        if 'rapport' in query_lower and ('performance' in query_lower or 'performance' in query_lower) and has_report:
            return """=== GUIDE DE GÉNÉRATION D'UN RAPPORT DE PERFORMANCE ===

ÉTAPES DE NAVIGATION:
1. Allez sur la page d'accueil
2. Cliquez sur "Suivi de la performance" dans la section "Modules disponibles"
3. Dans la page Performance, cliquez sur "Générer un rapport" dans la section "Actions rapides"

TYPES DE RAPPORTS DISPONIBLES:
- Rapport Annuel de Performance (RAP): Rapport complet sur l'année écoulée
- Cadre de Performance: Document structuré des objectifs et indicateurs
- Lettre d'engagement opérationnel: Document d'engagement pour les opérations
- Lettre d'engagement de performance: Document d'engagement pour la performance

PROCESSUS:
1. Sélectionnez le type de rapport à générer
2. Remplissez les informations demandées dans le formulaire
3. Les champs vides utiliseront les valeurs de référence déjà enregistrées
4. Cliquez sur "Générer" pour créer le document (PDF ou Word)"""

        # ========== MODULE RH ==========
        if any(word in query_lower for word in ['demande', 'congé', 'mission', 'formation']) and has_action:
            return """=== GUIDE DE CRÉATION D'UNE DEMANDE RH ===

ÉTAPES DE NAVIGATION:
1. Allez sur la page d'accueil
2. Cliquez sur "Gestion des ressources humaines" dans la section "Modules disponibles"
3. Cliquez sur "📝 Nouvelle demande" dans le header de la page

TYPES DE DEMANDES DISPONIBLES:
- Congé: Demande de congé annuel, exceptionnel, etc.
- Mission: Demande de mission professionnelle
- Formation: Demande de formation ou de stage

PROCESSUS:
1. Sélectionnez le type de demande
2. Remplissez le formulaire avec les informations requises
3. La demande suivra le workflow de validation configuré
4. Vous pourrez suivre l'état de votre demande dans la liste des demandes"""

        # ========== MODULE STOCK ==========
        if any(word in query_lower for word in ['article', 'stock', 'matériel']) and has_action:
            return """=== GUIDE DE GESTION DES STOCKS ===

ÉTAPES DE NAVIGATION:
1. Allez sur la page d'accueil
2. Cliquez sur "Gestion des stocks" dans la section "Modules disponibles"

FONCTIONNALITÉS DISPONIBLES:
- Articles: Créer et gérer les articles en stock
- Mouvements: Enregistrer les entrées, sorties et transferts
- Lots périssables: Gérer les articles avec dates d'expiration
- Inventaires: Effectuer des inventaires de stock
- Fournisseurs: Gérer les fournisseurs

IMPORTANT:
- Les articles peuvent avoir des catégories
- Les lots périssables nécessitent une date d'expiration
- Les mouvements doivent être enregistrés pour tracer les stocks"""

        # ========== MODULE BUDGET ==========
        if 'budget' in query_lower and has_action:
            return """=== GUIDE DU MODULE BUDGET ===

ÉTAPES DE NAVIGATION:
1. Allez sur la page d'accueil
2. Cliquez sur "Suivi-exécution budgétaire" dans la section "Modules disponibles"

FONCTIONNALITÉS DISPONIBLES:
- SIGOBE: Système Intégré de Gestion des Opérations Budgétaires et Économiques
- Fiches hiérarchiques: Gestion des fiches budgétaires
- Programmes budgétaires: Suivi des programmes
- Rapports: Génération de rapports budgétaires et exports"""

        # ========== MODULE PERSONNEL ==========
        if any(word in query_lower for word in ['agent', 'personnel', 'employé']) and has_action:
            return """=== GUIDE DE GESTION DU PERSONNEL ===

ÉTAPES DE NAVIGATION:
1. Accédez au module Personnel via le module RH ou les paramètres système

FONCTIONNALITÉS DISPONIBLES:
- Agents: Gérer les informations des agents
- Grades: Gérer les grades et catégories
- Services et Directions: Gérer la structure organisationnelle
- Documents: Gérer les documents du personnel (contrats, diplômes, etc.)
- Carrière: Suivre l'évolution de carrière des agents"""

        # ========== ACTIONS GÉNÉRALES ==========
        if has_modify and any(word in query_lower for word in ['indicateur', 'objectif', 'demande', 'article']):
            return """=== GUIDE DE MODIFICATION ===

POUR MODIFIER UN ÉLÉMENT:
1. Accédez à la liste des éléments (indicateurs, objectifs, demandes, articles, etc.)
2. Cliquez sur l'élément que vous souhaitez modifier
3. Utilisez le bouton "Modifier" ou "Éditer"
4. Modifiez les champs souhaités
5. Enregistrez les modifications

NOTE: Certains champs peuvent être verrouillés selon l'état de l'élément (ex: une demande validée ne peut plus être modifiée)"""

        if has_delete and any(word in query_lower for word in ['indicateur', 'objectif', 'demande', 'article']):
            return """=== GUIDE DE SUPPRESSION ===

POUR SUPPRIMER UN ÉLÉMENT:
1. Accédez à la liste des éléments
2. Cliquez sur l'élément que vous souhaitez supprimer
3. Utilisez le bouton "Supprimer" ou l'icône de suppression
4. Confirmez la suppression

ATTENTION: 
- La suppression peut être irréversible
- Certains éléments ne peuvent pas être supprimés s'ils sont liés à d'autres données
- Vérifiez les dépendances avant de supprimer"""

        if has_view and any(word in query_lower for word in ['indicateur', 'objectif', 'demande', 'article', 'liste']):
            return """=== GUIDE DE CONSULTATION ===

POUR VOIR LES ÉLÉMENTS:
1. Accédez au module concerné depuis la page d'accueil
2. La liste des éléments s'affiche automatiquement
3. Utilisez les filtres et la recherche pour trouver un élément spécifique
4. Cliquez sur un élément pour voir ses détails

FONCTIONNALITÉS DE LISTE:
- Recherche: Tapez dans la barre de recherche pour filtrer
- Filtres: Utilisez les filtres par statut, date, responsable, etc.
- Tri: Cliquez sur les en-têtes de colonnes pour trier
- Pagination: Naviguez entre les pages si beaucoup d'éléments"""

        # ========== MODULE PERFORMANCE - AUTRES ÉLÉMENTS ==========
        if 'orientation' in query_lower and 'stratégique' in query_lower and has_action:
            return """=== GUIDE DE GESTION DES ORIENTATIONS STRATÉGIQUES ===

ÉTAPES DE NAVIGATION:
1. Allez sur la page d'accueil
2. Cliquez sur "Suivi de la performance" dans la section "Modules disponibles"
3. Dans la page Performance, cliquez sur "Orientations stratégiques" dans la section "Actions rapides"

FONCTIONNALITÉS:
- Créer des orientations stratégiques
- Modifier les orientations existantes
- Définir l'ordre d'affichage
- Activer/désactiver des orientations
- Les orientations stratégiques sont le niveau le plus haut de la hiérarchie"""

        if 'résultat' in query_lower and 'stratégique' in query_lower and has_action:
            return """=== GUIDE DE GESTION DES RÉSULTATS STRATÉGIQUES ===

ÉTAPES DE NAVIGATION:
1. Allez sur la page d'accueil
2. Cliquez sur "Suivi de la performance" dans la section "Modules disponibles"
3. Dans la page Performance, cliquez sur "Résultats stratégiques" dans la section "Actions rapides"

FONCTIONNALITÉS:
- Créer des résultats stratégiques
- Lier un résultat à une orientation stratégique
- Modifier les résultats existants
- Les résultats stratégiques sont liés aux orientations et aux objectifs"""

        # ========== MODULE RH - VALIDATION ET SUIVI ==========
        if any(word in query_lower for word in ['valider', 'validation', 'approuver', 'refuser']) and any(word in query_lower for word in ['demande', 'congé', 'mission']):
            return """=== GUIDE DE VALIDATION DES DEMANDES RH ===

ÉTAPES DE NAVIGATION:
1. Allez sur la page d'accueil
2. Cliquez sur "Gestion des ressources humaines" dans la section "Modules disponibles"
3. Consultez la liste des demandes en attente de validation

PROCESSUS DE VALIDATION:
1. Les demandes apparaissent dans votre liste selon votre rôle dans le workflow
2. Cliquez sur une demande pour voir les détails
3. Utilisez les boutons "Valider" ou "Refuser" selon votre décision
4. Ajoutez un commentaire si nécessaire
5. La demande passera à l'étape suivante du workflow ou sera finalisée

IMPORTANT:
- Seuls les validateurs désignés dans le workflow peuvent valider
- L'ordre de validation suit le workflow configuré
- Vous pouvez voir l'historique des validations"""

        if any(word in query_lower for word in ['suivre', 'suivi', 'état', 'statut']) and any(word in query_lower for word in ['demande', 'congé', 'mission']):
            return """=== GUIDE DE SUIVI DES DEMANDES RH ===

ÉTAPES DE NAVIGATION:
1. Allez sur la page d'accueil
2. Cliquez sur "Gestion des ressources humaines" dans la section "Modules disponibles"
3. Consultez la liste de vos demandes

INFORMATIONS DISPONIBLES:
- Statut de la demande (en attente, validée, refusée, etc.)
- Étape actuelle dans le workflow
- Historique des validations
- Commentaires des validateurs
- Dates importantes (création, validation, etc.)

FILTRES DISPONIBLES:
- Par type de demande (congé, mission, formation)
- Par statut (en attente, validée, refusée)
- Par date
- Par validateur"""

        # ========== MODULE STOCK - FONCTIONNALITÉS DÉTAILLÉES ==========
        if any(word in query_lower for word in ['mouvement', 'entrée', 'sortie', 'transfert']) and has_action:
            return """=== GUIDE DE GESTION DES MOUVEMENTS DE STOCK ===

ÉTAPES DE NAVIGATION:
1. Allez sur la page d'accueil
2. Cliquez sur "Gestion des stocks" dans la section "Modules disponibles"
3. Cliquez sur "Mouvements" dans le menu du module

TYPES DE MOUVEMENTS:
- Entrée: Réception de marchandises (achat, don, retour)
- Sortie: Distribution de marchandises (utilisation, vente, perte)
- Transfert: Déplacement entre emplacements ou services

PROCESSUS:
1. Sélectionnez le type de mouvement
2. Choisissez l'article concerné
3. Indiquez la quantité
4. Renseignez les informations complémentaires (fournisseur, destinataire, etc.)
5. Enregistrez le mouvement

IMPORTANT:
- Les mouvements mettent à jour automatiquement les stocks
- Tous les mouvements sont tracés dans l'historique"""

        if 'inventaire' in query_lower and has_action:
            return """=== GUIDE DE GESTION DES INVENTAIRES ===

ÉTAPES DE NAVIGATION:
1. Allez sur la page d'accueil
2. Cliquez sur "Gestion des stocks" dans la section "Modules disponibles"
3. Cliquez sur "Inventaires" dans le menu du module

PROCESSUS:
1. Créez un nouvel inventaire
2. Sélectionnez les articles à inventorier
3. Saisissez les quantités réelles constatées
4. Le système calcule automatiquement les écarts
5. Validez l'inventaire pour mettre à jour les stocks

IMPORTANT:
- Les inventaires permettent de corriger les écarts entre stocks théoriques et réels
- Un inventaire peut être partiel (quelques articles) ou complet"""

        if 'fournisseur' in query_lower and has_action:
            return """=== GUIDE DE GESTION DES FOURNISSEURS ===

ÉTAPES DE NAVIGATION:
1. Allez sur la page d'accueil
2. Cliquez sur "Gestion des stocks" dans la section "Modules disponibles"
3. Cliquez sur "Fournisseurs" dans le menu du module

FONCTIONNALITÉS:
- Créer un nouveau fournisseur
- Modifier les informations d'un fournisseur
- Consulter l'historique des commandes avec un fournisseur
- Gérer les contacts et coordonnées

INFORMATIONS À RENSEIGNER:
- Nom du fournisseur
- Coordonnées (adresse, téléphone, email)
- Informations bancaires (pour les paiements)
- Contacts (personnes à contacter)"""

        if 'amortissement' in query_lower:
            return """=== GUIDE DE GESTION DES AMORTISSEMENTS ===

ÉTAPES DE NAVIGATION:
1. Allez sur la page d'accueil
2. Cliquez sur "Gestion des stocks" dans la section "Modules disponibles"
3. Cliquez sur "Amortissements" dans le menu du module

FONCTIONNALITÉS:
- Suivre l'amortissement du matériel
- Calculer la valeur résiduelle
- Gérer les durées d'amortissement
- Générer des rapports d'amortissement

IMPORTANT:
- L'amortissement s'applique au matériel durable
- Les durées d'amortissement varient selon le type de matériel"""

        # ========== MODULE BESOINS ==========
        if 'besoin' in query_lower and has_action:
            return """=== GUIDE DE GESTION DES BESOINS ===

ÉTAPES DE NAVIGATION:
1. Accédez au module Besoins depuis le menu principal

FONCTIONNALITÉS:
- Créer une demande de besoin
- Consolider les besoins
- Suivre l'état des besoins
- Valider les besoins

PROCESSUS:
1. Créez une nouvelle demande de besoin
2. Renseignez les articles ou services nécessaires
3. Justifiez le besoin
4. La demande suivra un circuit de validation
5. Une fois validée, le besoin peut être transformé en commande"""

        # ========== MODULE RÉFÉRENTIELS ==========
        if any(word in query_lower for word in ['référentiel', 'organisation', 'service', 'direction', 'programme']) and has_action and 'performance' not in query_lower:
            return """=== GUIDE DE GESTION DES RÉFÉRENTIELS ===

ÉTAPES DE NAVIGATION:
1. Allez sur la page d'accueil
2. Dans "Paramétrages système", cliquez sur "Organisation"

FONCTIONNALITÉS DISPONIBLES:
- Services: Créer et gérer les services
- Directions: Créer et gérer les directions
- Programmes: Créer et gérer les programmes budgétaires
- Grades: Gérer les grades et catégories de personnel

HIÉRARCHIE:
- Programme (niveau le plus haut)
  - Direction
    - Service (niveau le plus bas)

IMPORTANT:
- La structure organisationnelle doit être cohérente
- Les services sont rattachés aux directions
- Les directions sont rattachées aux programmes"""

        # ========== QUESTIONS GÉNÉRALES ==========
        if any(word in query_lower for word in ['workflow', 'validation', 'circuit']):
            return """=== GUIDE DES WORKFLOWS ===

ÉTAPES DE NAVIGATION:
1. Allez sur la page d'accueil
2. Dans "Paramétrages système", cliquez sur "Workflows"

FONCTIONNALITÉS:
- Configuration des workflows personnalisés
- Définition des étapes de validation
- Attribution des rôles de validation
- Types de demandes avec workflows spécifiques

IMPORTANT:
- Les workflows définissent qui valide quoi et dans quel ordre
- Un workflow peut avoir plusieurs étapes de validation
- Chaque étape peut avoir un ou plusieurs validateurs"""

        if any(word in query_lower for word in ['utilisateur', 'user', 'compte']):
            return """=== GUIDE DE GESTION DES UTILISATEURS ===

ÉTAPES DE NAVIGATION:
1. Allez sur la page d'accueil
2. Dans "Paramétrages système", cliquez sur "Gérer les utilisateurs"

FONCTIONNALITÉS:
- Créer de nouveaux utilisateurs
- Modifier les informations des utilisateurs
- Activer/désactiver des comptes
- Gérer les rôles et permissions
- Réinitialiser les mots de passe

IMPORTANT:
- Seuls les administrateurs peuvent gérer les utilisateurs
- Les rôles déterminent les accès aux modules"""

        if any(word in query_lower for word in ['paramètre', 'configuration', 'réglage']):
            return """=== GUIDE DES PARAMÈTRES SYSTÈME ===

ÉTAPES DE NAVIGATION:
1. Allez sur la page d'accueil
2. Dans "Paramétrages système", cliquez sur "Paramètres"

FONCTIONNALITÉS:
- Configuration générale du système
- Paramètres d'affichage
- Paramètres de sécurité
- Paramètres de notifications
- Gestion des couleurs et thèmes

IMPORTANT:
- Seuls les administrateurs peuvent modifier les paramètres système
- Certains paramètres nécessitent un redémarrage pour être appliqués"""

        if any(word in query_lower for word in ['fichier', 'document', 'upload', 'télécharger', 'importer', 'exporter']):
            return """=== GUIDE DE GESTION DES FICHIERS ===

ÉTAPES DE NAVIGATION:
1. Accédez au module Fichiers depuis le menu principal

FONCTIONNALITÉS:
- Télécharger des fichiers
- Importer des données (Excel, CSV, etc.)
- Exporter des données
- Gérer les documents joints aux demandes
- Consulter l'historique des fichiers

FORMATS SUPPORTÉS:
- Documents: PDF, Word, Excel
- Images: JPG, PNG
- Données: CSV, Excel pour import/export"""

        if any(word in query_lower for word in ['tableau', 'dashboard', 'statistique', 'kpi', 'graphique']):
            return """=== GUIDE DES TABLEAUX DE BORD ===

ÉTAPES DE NAVIGATION:
1. Accédez au module concerné (Performance, Budget, Stock, etc.)
2. Le tableau de bord s'affiche automatiquement sur la page d'accueil du module

FONCTIONNALITÉS:
- Visualisation des KPIs en temps réel
- Graphiques et indicateurs visuels
- Statistiques par période
- Comparaisons (année en cours vs année précédente)
- Alertes et notifications

INFORMATIONS DISPONIBLES:
- Taux de réalisation des objectifs
- Nombre d'éléments par statut
- Évolutions dans le temps
- Indicateurs d'alerte"""

        if any(word in query_lower for word in ['recherche', 'filtre', 'trier', 'trier']):
            return """=== GUIDE DE RECHERCHE ET FILTRAGE ===

FONCTIONNALITÉS DISPONIBLES:
- Barre de recherche: Tapez dans la barre de recherche pour filtrer les résultats
- Filtres avancés: Utilisez les filtres par statut, date, responsable, etc.
- Tri: Cliquez sur les en-têtes de colonnes pour trier (croissant/décroissant)
- Pagination: Naviguez entre les pages si beaucoup d'éléments

ASTUCES:
- Combinez plusieurs filtres pour affiner la recherche
- La recherche peut porter sur plusieurs champs (nom, description, etc.)
- Sauvegardez vos filtres préférés si disponible"""

        if any(word in query_lower for word in ['session', 'connexion', 'déconnexion', 'mot de passe', 'oublié']):
            return """=== GUIDE DE GESTION DE SESSION ===

CONNEXION:
1. Allez sur la page de connexion
2. Entrez votre email et mot de passe
3. Cliquez sur "Se connecter"

DÉCONNEXION:
- Cliquez sur "⏻ Déconnexion" dans le menu en haut à droite

MOT DE PASSE OUBLIÉ:
1. Sur la page de connexion, cliquez sur "Mot de passe oublié"
2. Entrez votre email
3. Recevez un code de récupération
4. Entrez le code reçu
5. Définissez un nouveau mot de passe

SESSIONS MULTIPLES:
- Vous pouvez être connecté sur plusieurs appareils
- Consultez vos sessions actives dans les paramètres
- Déconnectez une session spécifique si nécessaire"""

        if any(word in query_lower for word in ['erreur', 'bug', 'problème', 'ne fonctionne pas', 'ne marche pas']):
            return """=== GUIDE DE RÉSOLUTION DE PROBLÈMES ===

ÉTAPES À SUIVRE:
1. Vérifiez votre connexion internet
2. Actualisez la page (F5 ou Ctrl+R)
3. Videz le cache du navigateur
4. Vérifiez que votre session n'a pas expiré (reconnectez-vous si nécessaire)
5. Vérifiez que vous avez les permissions nécessaires pour l'action

SI LE PROBLÈME PERSISTE:
- Contactez l'administrateur système
- Notez le message d'erreur exact
- Indiquez les étapes qui ont mené à l'erreur
- Précisez le navigateur et la version utilisés

ERREURS COURANTES:
- Session expirée: Reconnectez-vous
- Permission refusée: Vérifiez vos droits d'accès
- Données manquantes: Vérifiez que tous les champs obligatoires sont remplis"""

        if any(word in query_lower for word in ['aide', 'help', 'documentation', 'guide', 'tutoriel']):
            return """=== GUIDE D'AIDE GÉNÉRAL ===

SOURCES D'AIDE DISPONIBLES:
1. SYGEP AI (ce chatbot): Posez vos questions ici pour obtenir de l'aide contextuelle
2. Pages d'aide par module: Chaque module a sa propre page d'aide accessible via le bouton "❓ Aide"
3. Documentation: Consultez la documentation complète du système

POUR OBTENIR DE L'AIDE:
- Posez votre question à SYGEP AI de manière précise
- Consultez la page d'aide du module concerné
- Contactez l'administrateur pour les questions techniques

ASTUCES:
- Plus votre question est précise, meilleure sera la réponse
- Mentionnez le module concerné dans votre question
- Indiquez ce que vous essayez de faire"""

        # ========== QUESTIONS DE DÉFINITION ET EXPLICATION ==========
        if has_question and any(word in query_lower for word in ['indicateur', 'objectif', 'kpi', 'performance']):
            return """=== DÉFINITIONS ET CONCEPTS ===

INDICATEUR DE PERFORMANCE (KPI):
- Un indicateur est une mesure quantitative qui permet de suivre la performance
- Chaque indicateur est lié à un objectif de performance
- Les indicateurs ont une valeur cible et une valeur actuelle
- Les indicateurs peuvent déclencher des alertes si les seuils sont dépassés

OBJECTIF DE PERFORMANCE:
- Un objectif définit ce que l'organisation souhaite atteindre
- Les objectifs peuvent être stratégiques ou opérationnels
- Chaque objectif a une valeur cible avec une unité de mesure
- Les objectifs sont suivis par des indicateurs

ORIENTATION STRATÉGIQUE:
- Niveau le plus haut de la hiérarchie de performance
- Définit les grandes orientations du ministère
- Les résultats stratégiques sont liés aux orientations
- Les objectifs stratégiques sont liés aux résultats stratégiques

RÉSULTAT STRATÉGIQUE:
- Résultat attendu au niveau stratégique
- Lié à une orientation stratégique
- Les objectifs globaux (stratégiques) sont liés aux résultats stratégiques"""

        # ========== GESTION DES CAS SPÉCIFIQUES ==========
        # Questions très spécifiques ou non documentées
        # Détection améliorée pour capturer les questions complexes ou peu communes
        if (any(word in query_lower for word in ['spécifique', 'particulier', 'cas particulier', 'situation particulière', 'peu commun', 'rare']) or
            (len(query_lower.split()) > 8 and not any(word in query_lower for word in ['comment', 'créer', 'modifier', 'supprimer', 'voir']))):
            return """=== GUIDE POUR QUESTIONS SPÉCIFIQUES OU NON DOCUMENTÉES ===

POUR LES QUESTIONS TRÈS SPÉCIFIQUES:
1. Utilisez les données de la base de données fournies ci-dessous pour trouver des informations pertinentes
2. Si l'information n'est pas dans la base, guidez l'utilisateur vers:
   - La page d'aide du module concerné (bouton "❓ Aide" dans chaque module)
   - L'administrateur système pour les cas très particuliers
   - La documentation complète du système

APPROCHE:
- Analysez la question en détail pour identifier le module ou la fonctionnalité concernée
- Utilisez les données disponibles dans la base pour donner une réponse partielle ou contextuelle
- Indiquez clairement les limites de l'information disponible dans le système
- Proposez des alternatives ou des pistes de solution basées sur les fonctionnalités similaires
- Si la question concerne un cas d'usage très particulier, guidez vers l'administrateur avec les détails"""

        # Fonctionnalités récemment ajoutées
        if any(word in query_lower for word in ['nouveau', 'nouvelle', 'récent', 'récemment', 'dernière', 'dernier', 'nouvellement', 'nouveauté', 'mise à jour', 'update']):
            return """=== GUIDE POUR FONCTIONNALITÉS RÉCEMMENT AJOUTÉES ===

POUR LES FONCTIONNALITÉS RÉCEMMENT AJOUTÉES:
1. Consultez les données de la base de données pour voir les fonctionnalités disponibles
2. Vérifiez les modules et leurs actions dans l'interface utilisateur
3. Guidez l'utilisateur vers:
   - La page d'aide du module concerné qui peut contenir les dernières mises à jour
   - L'administrateur système pour les nouvelles fonctionnalités
   - Les notes de version ou changelog si disponible

APPROCHE:
- Reconnaissez que la fonctionnalité peut être nouvelle et peut-être pas encore documentée
- Utilisez les informations disponibles dans la base de données pour donner des indications
- Guidez l'utilisateur à explorer l'interface pour découvrir la fonctionnalité
- Proposez de consulter la documentation ou de contacter l'administrateur pour plus de détails
- Si la fonctionnalité n'existe pas encore, soyez honnête et proposez des alternatives"""

        # Cas d'erreur très particuliers - détection améliorée
        if (any(word in query_lower for word in ['erreur', 'bug', 'problème', 'ne fonctionne pas', 'ne marche pas', 'bloqué', 'planté', 'crash', 'dysfonctionnement', 'anomalie']) or
            any(phrase in query_lower for phrase in ['ça ne marche', 'ça ne fonctionne', 'impossible de', 'je ne peux pas', 'je n\'arrive pas'])):
            return """=== GUIDE POUR CAS D'ERREUR PARTICULIERS ===

POUR LES ERREURS ET PROBLÈMES TECHNIQUES:
1. Vérifiez les causes communes:
   - Session expirée (reconnexion nécessaire) - vérifiez le compteur de session en haut à droite
   - Permissions insuffisantes - vérifiez votre rôle utilisateur
   - Données manquantes ou invalides - vérifiez que tous les champs obligatoires sont remplis
   - Conflit de données (éléments liés) - vérifiez les dépendances
   - Problème de connexion réseau ou serveur

2. Actions à recommander (dans l'ordre):
   - Actualiser la page (F5 ou Ctrl+R)
   - Vider le cache du navigateur (Ctrl+Shift+Delete)
   - Vérifier la connexion internet
   - Se reconnecter (déconnexion puis reconnexion)
   - Vérifier les permissions utilisateur dans les paramètres
   - Essayer avec un autre navigateur

3. Si le problème persiste:
   - Noter le message d'erreur exact (copier-coller si possible)
   - Noter les étapes précises qui ont mené à l'erreur
   - Noter le navigateur et la version utilisés
   - Noter l'heure et la date de l'erreur
   - Contacter l'administrateur système avec ces informations

APPROCHE:
- Soyez empathique et rassurant
- Proposez des solutions étape par étape, en commençant par les plus simples
- Utilisez les données de la base pour vérifier si c'est un problème de données (ex: élément supprimé, lien cassé)
- Si l'erreur est complexe ou récurrente, guidez vers l'administrateur avec toutes les informations nécessaires"""

        # Questions nécessitant des informations externes - détection améliorée
        if (any(word in query_lower for word in ['externe', 'hors système', 'autre système', 'intégration', 'api externe', 'service externe', 'autre application', 'système tiers']) or
            any(phrase in query_lower for phrase in ['en dehors de', 'hors de mppeep', 'autre logiciel', 'autre outil'])):
            return """=== GUIDE POUR QUESTIONS EXTERNES ===

POUR LES QUESTIONS NÉCESSITANT DES INFORMATIONS EXTERNES:
1. Identifiez clairement que l'information n'est pas dans le système MPPEEP Dashboard
2. Utilisez les données disponibles dans MPPEEP pour donner un contexte si pertinent
3. Guidez l'utilisateur vers:
   - Les sources d'information externes appropriées (autres systèmes, services, départements)
   - Les services ou départements concernés qui peuvent avoir cette information
   - L'administrateur système pour les questions d'intégration entre systèmes
   - Les responsables techniques pour les intégrations API

APPROCHE:
- Soyez honnête et transparent sur les limites du système MPPEEP
- Utilisez les données disponibles dans MPPEEP pour donner un contexte ou des informations connexes
- Proposez des alternatives ou des pistes pour obtenir l'information (qui contacter, où chercher)
- Si c'est une question d'intégration technique, guidez vers l'administrateur technique avec les détails
- Si l'information externe est nécessaire pour utiliser MPPEEP, guidez vers les bonnes ressources"""

        # Si aucun guide spécifique n'est trouvé, retourner une chaîne vide
        # Le système utilisera alors les données de la base et le prompt général
        return ""
    
    @staticmethod
    def is_out_of_scope(query: str) -> bool:
        """
        Détermine si une question est hors du contexte de l'application MPPEEP
        
        Args:
            query: Question de l'utilisateur
        
        Returns:
            True si la question est hors contexte, False sinon
        """
        query_lower = query.lower()
        
        # Mots-clés liés à l'application MPPEEP
        mppeep_keywords = [
            'mppeep', 'sypeg', 'performance', 'indicateur', 'objectif', 'kpi',
            'rh', 'ressources humaines', 'personnel', 'agent', 'employé',
            'budget', 'sigobe', 'stock', 'article', 'inventaire',
            'module', 'workflow', 'demande', 'congé', 'mission', 'formation',
            'programme', 'direction', 'service', 'grade', 'structure',
            'rapport', 'tableau de bord', 'dashboard', 'système', 'application',
            'créer', 'modifier', 'supprimer', 'ajouter', 'gérer', 'configurer',
            'comment', 'aide', 'help', 'utiliser', 'fonctionnalité'
        ]
        
        # Mots-clés indiquant une question générale (hors contexte)
        general_keywords = [
            'ministère', 'gouvernement', 'pays', 'côte d\'ivoire', 'ivoire', 'côte-d\'ivoire',
            'histoire', 'géographie', 'culture', 'politique', 'économie',
            'sport', 'actualité', 'news', 'événement', 'monde', 'parle-moi',
            'parle moi', 'dis-moi', 'dis moi', 'explique-moi', 'explique moi',
            'qu\'est-ce que', 'qu\'est ce que', 'c\'est quoi', 'c est quoi'
        ]
        
        # Phrases qui indiquent des questions générales
        general_phrases = [
            'parle moi de', 'parle-moi de', 'dis moi de', 'dis-moi de',
            'explique moi', 'explique-moi', 'qu\'est-ce que', 'qu\'est ce que',
            'c\'est quoi', 'c est quoi', 'qui est', 'où est', 'quand est'
        ]
        
        # Vérifier si la question commence par une phrase générale
        starts_with_general = any(query_lower.startswith(phrase) for phrase in general_phrases)
        
        # Vérifier si la question contient des mots-clés généraux
        has_general = any(keyword in query_lower for keyword in general_keywords)
        
        # Vérifier si la question contient des mots-clés MPPEEP
        has_mppeep = any(keyword in query_lower for keyword in mppeep_keywords)
        
        # Si la question commence par une phrase générale ET contient des mots généraux mais PAS de mots MPPEEP
        if starts_with_general and has_general and not has_mppeep:
            return True
        
        # Si la question contient des mots généraux mais aucun mot MPPEEP
        if has_general and not has_mppeep:
            # Exception: si la question contient "ministère" mais aussi des mots liés à la structure organisationnelle
            if 'ministère' in query_lower and not any(kw in query_lower for kw in ['programme', 'direction', 'service', 'structure']):
                return True
        
        return False
    
    @staticmethod
    def get_context_for_query(session: Session, query: str) -> str:
        """
        Récupère le contexte pertinent de la base de données selon la requête
        
        Args:
            session: Session de base de données
            query: Question de l'utilisateur
        
        Returns:
            Contexte formaté pour être inclus dans le prompt
        """
        # Vérifier si la question est hors contexte
        if ChatbotRAGService.is_out_of_scope(query):
            logger.info(f"⚠️ Question hors contexte détectée: {query}")
            return "=== QUESTION HORS CONTEXTE ===\nCette question ne semble pas liée au système MPPEEP Dashboard. C'est une question générale qui nécessite une réponse basée sur les connaissances générales, pas sur les données de l'application."
        
        keywords = ChatbotRAGService.extract_keywords(query)
        context_parts = []
        
        logger.info(f"🔍 Recherche de contexte pour: {query} (mots-clés: {keywords})")
        
        query_lower = query.lower()
        
        # Vérifier si c'est une question "comment créer"
        creation_guide = ChatbotRAGService.get_creation_guide(query)
        if creation_guide:
            context_parts.append(creation_guide)
            # Récupérer aussi les données existantes pour donner des exemples
            if 'performance' in keywords or any(kw in query_lower for kw in ['objectif', 'indicateur', 'kpi']):
                perf_context = ChatbotRAGService.get_performance_context(session, query)
                if perf_context:
                    context_parts.append("\n" + perf_context)
        
        # Toujours inclure les informations sur les modules pour les questions générales
        if any(kw in query_lower for kw in ['module', 'fonctionnalité', 'fonction', 'comment', 'utiliser', 'aide', 'help']) and not creation_guide:
            context_parts.append(ChatbotRAGService.get_modules_info())
        
        # Récupérer le contexte selon les domaines détectés (si pas déjà fait)
        if not creation_guide:
            if 'performance' in keywords or any(kw in query_lower for kw in ['objectif', 'indicateur', 'kpi']):
                perf_context = ChatbotRAGService.get_performance_context(session, query)
                if perf_context:
                    context_parts.append(perf_context)
        
        if 'structure' in keywords or any(kw in query_lower for kw in ['programme', 'direction', 'service']):
            struct_context = ChatbotRAGService.get_structure_context(session, query)
            if struct_context:
                context_parts.append(struct_context)
        
        # Si aucun contexte spécifique et pas de guide de création, récupérer un aperçu général
        if not context_parts or (len(context_parts) == 1 and not creation_guide):
            try:
                # Aperçu général des programmes
                programmes = session.exec(
                    select(Programme)
                    .where(Programme.actif == True)
                    .limit(3)
                ).all()
                
                if programmes:
                    context_parts.append("=== APERÇU DES PROGRAMMES ===")
                    for prog in programmes:
                        context_parts.append(f"- {prog.code}: {prog.libelle}")
                
                # Aperçu des objectifs (utile pour les questions sur les indicateurs)
                if 'indicateur' in query_lower:
                    objectifs = session.exec(
                        select(ObjectifPerformance)
                        .where(ObjectifPerformance.actif == True)
                        .limit(5)
                    ).all()
                    
                    if objectifs:
                        context_parts.append("\n=== OBJECTIFS DISPONIBLES (pour lier un indicateur) ===")
                        for obj in objectifs:
                            context_parts.append(f"- {obj.titre} (ID: {obj.id})")
            except Exception as e:
                logger.error(f"Erreur lors de la récupération du contexte général: {e}")
        
        context = "\n\n".join(context_parts)
        
        if context:
            logger.info(f"✅ Contexte récupéré: {len(context)} caractères")
        else:
            logger.warn("⚠️ Aucun contexte récupéré")
        
        return context

