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
    VALIDATION_N1 = "Validation N1"          # chef service / hiérarchie 1
    VALIDATION_N2 = "Validation N2"          # chef direction / hiérarchie 2 (optionnel)
    VALIDATION_DRH = "Validation DRH"        # DRH
    SIGNATURE_DG = "Signature DG"            # Signature Directeur Général
    SIGNATURE_DAF = "Signature DAF"          # Directeur administratif / Autorité (optionnel)
    ARCHIVED = "Archivé"                     # Archivé (terminé)
    REJECTED = "Rejeté"                      # Rejeté

class UserType(str, Enum):
    """
    Types d'utilisateurs
    Stockés comme VARCHAR dans la base de données
    """
    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"
    GUEST = "guest"
    
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
    BUDGET = "budget"
    DEPENSES = "depenses"
    REVENUS = "revenus"
    PERSONNEL = "personnel"
    RAPPORT_ACTIVITE = "rapport_activite"
    BENEFICIAIRES = "beneficiaires"
    INDICATEURS = "indicateurs"
    AUTRE = "autre"
    
    def __str__(self):
        return self.value


class FileStatus(str, Enum):
    """
    Statuts de traitement des fichiers
    """
    UPLOADED = "uploaded"          # Fichier téléchargé
    PROCESSING = "processing"      # En cours de traitement
    PROCESSED = "processed"        # Traité avec succès
    ERROR = "error"                # Erreur de traitement
    ARCHIVED = "archived"          # Archivé
    
    def __str__(self):
        return self.value


class ProgramType(str, Enum):
    """
    Types de programmes
    """
    EDUCATION = "education"
    SANTE = "sante"
    AGRICULTURE = "agriculture"
    INFRASTRUCTURE = "infrastructure"
    PROTECTION_SOCIALE = "protection_sociale"
    ENVIRONNEMENT = "environnement"
    GOUVERNANCE = "gouvernance"
    AUTRE = "autre"
    
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
]

