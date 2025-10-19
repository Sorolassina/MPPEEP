"""
Énumérations utilisées dans l'application
Les valeurs sont stockées en texte dans la base de données
"""
from enum import Enum


# --- Enums ---
class RequestType(str, Enum):
    CONGE = "Congé"
    PERMISSION = "Permission"
    FORMATION = "Formation"
    BESOIN_ACTE = "Besoin d'acte administratif"

class ActeAdministratifType(str, Enum):
    """Types d'actes administratifs disponibles"""
    ATTESTATION_TRAVAIL = "Attestation de travail"
    CERTIFICAT_PRESENCE = "Certificat de présence"
    ATTESTATION_SALAIRE = "Attestation de salaire"
    ORDRE_MISSION = "Ordre de mission"
    DECISION_CONGE = "Décision de congé"
    DECISION_AVANCEMENT = "Décision d'avancement"
    DECISION_AFFECTATION = "Décision d'affectation"
    DECISION_RECRUTEMENT = "Décision de recrutement"
    ACTE_NAISSANCE = "Acte de naissance"
    CASIER_JUDICIAIRE = "Casier judiciaire"
    CERTIFICAT_NATIONALITE = "Certificat de nationalité"
    AUTRE = "Autre acte administratif"

class WorkflowState(str, Enum):
    DRAFT = "Brouillon"                      # brouillon (agent)
    SUBMITTED = "Soumis"                     # soumis
    VALIDATION_N1 = "Validation N+1"         # Validation niveau 1
    VALIDATION_N2 = "Validation N+2"         # Validation niveau 2
    VALIDATION_N3 = "Validation N+3"         # Validation niveau 3
    VALIDATION_N4 = "Validation N+4"         # Validation niveau 4
    VALIDATION_N5 = "Validation N+5"         # Validation niveau 5
    VALIDATION_N6 = "Validation N+6"         # Validation niveau 6
    ARCHIVED = "Archivé"                     # Archivé (terminé)
    REJECTED = "Rejeté"                      # Rejeté

class UserType(str, Enum):
    """
    Types d'utilisateurs
    Stockés comme VARCHAR dans la base de données
    """
    ADMIN = "admin"
    USER = "agent"
    N1 = "chef service"
    N2 = "directeur"
    DRH = "directeur des ressources humaines"
    DAF = "directeur administratif et financier"
    INVITE = "invité"
    
    def __str__(self):
        return self.value


class UserStatus(str, Enum):
    """
    Statuts d'utilisateur
    """
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
    
    def __str__(self):
        return self.value


class Environment(str, Enum):
    """
    Environnements de déploiement
    """
    DEVELOPMENT = "dev"
    STAGING = "staging"
    PRODUCTION = "production"
    
    def __str__(self):
        return self.value


class FileType(str, Enum):
    """
    Types de fichiers supportés
    """
    FICHE_SYNTHETIQUE = "fiche synthetique"
    BUDGET = "données budgétaires"
    FICHE_PERSONNEL = "fiche personnel"
    RAPPORT_ACTIVITE = "rapport d'activite"
    LISTE_BENEFICIAIRES = "liste des beneficiaires"
    INDICATEURS_PERFORMANCE = "indicateurs de performance"
    AUTRE = "autre"
    
    def __str__(self):
        return self.value


class FileStatus(str, Enum):
    """
    Statuts de traitement des fichiers
    """
    UPLOADED = "téléchargé"          # Fichier téléchargé
    PROCESSING = "en traitement"      # En cours de traitement
    PROCESSED = "traité"        # Traité avec succès
    ERROR = "erreur"                # Erreur de traitement
    ARCHIVED = "archivé"          # Archivé
    
    def __str__(self):
        return self.value


class ProgramType(str, Enum):
    """
    Types de programmes
    """
    ADMINISTRATION_GENERALE = "administration générale"
    GESTION_ETABLISSEMENTS_PUBLICS_NATIONAUX = "gestion des établissements publics nationaux"
    PORTEFEUILLE_ETAT = "portefeuille de l'état"
    
    
    def __str__(self):
        return self.value

class DirectionType(str, Enum):
    """
    Types de programmes
    """
    MOYENS_GENERAUX = "moyens généraux"
    RESSOURCES_HUMAINES = "ressources humaines"
    BUDGET = "budget"
    
    
    def __str__(self):
        return self.value

class ServiceType(str, Enum):
    """
    Types de programmes
    """
    SOCIALE = "Social"
    BUDGET_RAPPORTAGE = "Budget et rapportage"
    COMPTABILITE = "comptabilité"
    INFORMATIQUE = "informatique"
    FORMATION = "formation"
    STOCK = "stock"
    SECURITE = "sécurité"
    AUTRE = "autre"
    
    def __str__(self):
        return self.value

class GradeCategory(str, Enum):
    """Catégories de grades de la fonction publique"""
    A = "Catégorie A - Cadres supérieurs"
    B = "Catégorie B - Cadres moyens"
    C = "Catégorie C - Agents d'exécution"
    D = "Catégorie D - Personnel de soutien"
    
    def __str__(self):
        return self.value

class PositionAdministrative(str, Enum):
    """Position administrative de l'agent"""
    EN_ACTIVITE = "En activité"
    DETACHEMENT = "Détachement"
    DISPONIBILITE = "Disponibilité"
    CONGE_LONGUE_DUREE = "Congé de longue durée"
    SOUS_LES_DRAPEAUX = "Sous les drapeaux"
    HORS_CADRE = "Hors cadre"
    SUSPENSION = "Suspension"
    RETRAITE = "Retraite"
    
    def __str__(self):
        return self.value

class SituationFamiliale(str, Enum):
    """Situation familiale"""
    CELIBATAIRE = "Célibataire"
    MARIE = "Marié(e)"
    DIVORCE = "Divorcé(e)"
    VEUF = "Veuf(ve)"
    UNION_LIBRE = "Union libre"
    
    def __str__(self):
        return self.value

class TypeDocument(str, Enum):
    """Types de documents agent"""
    CNI = "Carte nationale d'identité"
    PASSEPORT = "Passeport"
    ACTE_NAISSANCE = "Acte de naissance"
    DIPLOME = "Diplôme"
    CERTIFICAT = "Certificat"
    CONTRAT = "Contrat"
    ARRETE_NOMINATION = "Arrêté de nomination"
    DECISION_AVANCEMENT = "Décision d'avancement"
    FICHE_NOTATION = "Fiche de notation"
    CERTIFICAT_MEDICAL = "Certificat médical"
    ATTESTATION_TRAVAIL = "Attestation de travail"
    AUTRE = "Autre document"
    
    def __str__(self):
        return self.value

# Pour faciliter les imports
__all__ = [
    "RequestType",
    "ActeAdministratifType",
    "WorkflowState",
    "UserType",
    "UserStatus",
    "Environment",
    "FileType",
    "FileStatus",
    "ProgramType",
    "DirectionType",
    "ServiceType",
    "GradeCategory",
    "PositionAdministrative",
    "SituationFamiliale",
    "TypeDocument"
]

