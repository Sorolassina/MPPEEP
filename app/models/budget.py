# app/models/budget.py
"""
Modèles pour la gestion budgétaire et les conférences budgétaires
"""
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, date
from decimal import Decimal


class NatureDepense(SQLModel, table=True):
    """
    Nature de dépenses (BS, P, I, T)
    """
    __tablename__ = "nature_depense"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)  # BS, P, I, T
    libelle: str  # Biens & Services, Personnel, Investissement, Transferts
    description: Optional[str] = None
    actif: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Activite(SQLModel, table=True):
    """
    Activités budgétaires (actions, projets)
    Chargées depuis Excel
    """
    __tablename__ = "activite"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True)
    libelle: str
    programme_id: Optional[int] = Field(default=None, foreign_key="programme.id")
    direction_id: Optional[int] = Field(default=None, foreign_key="direction.id")
    nature_depense_id: Optional[int] = Field(default=None, foreign_key="nature_depense.id")
    description: Optional[str] = None
    actif: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FicheTechnique(SQLModel, table=True):
    """
    Fiche technique pour conférence budgétaire
    Document central de demande budgétaire par programme
    """
    __tablename__ = "fiche_technique"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Identification
    numero_fiche: str = Field(index=True, unique=True)  # FT-2025-P01-001
    annee_budget: int  # 2025, 2026, etc.
    programme_id: int = Field(foreign_key="programme.id")
    direction_id: Optional[int] = Field(default=None, foreign_key="direction.id")
    
    # Budget année précédente (N-1)
    budget_anterieur: Decimal = Field(default=0, decimal_places=2)  # En FCFA
    
    # Demande pour année N
    enveloppe_demandee: Decimal = Field(default=0, decimal_places=2)  # Budget de base
    complement_demande: Decimal = Field(default=0, decimal_places=2)  # Demandes supplémentaires
    
    # Engagements
    engagement_etat: Decimal = Field(default=0, decimal_places=2)  # Projets État
    financement_bailleurs: Decimal = Field(default=0, decimal_places=2)  # Bailleurs de fonds
    
    # Total
    budget_total_demande: Decimal = Field(default=0, decimal_places=2)  # Calculé automatiquement
    
    # Justification
    note_justificative: Optional[str] = None
    observations: Optional[str] = None
    
    # Statut
    statut: str = "Brouillon"  # Brouillon, Soumis, Validé, Rejeté, Approuvé
    phase: str = "Conférence interne"  # Conférence interne, Conférence ministérielle
    
    # Dates
    date_creation: date = Field(default_factory=date.today)
    date_soumission: Optional[date] = None
    date_validation: Optional[date] = None
    
    # Traçabilité
    created_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    updated_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    validated_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    # Metadata
    actif: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LigneBudgetaire(SQLModel, table=True):
    """
    Ligne de détail budgétaire dans une fiche technique
    Détaille les dépenses par activité et nature
    """
    __tablename__ = "ligne_budgetaire"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    fiche_technique_id: int = Field(foreign_key="fiche_technique.id")
    
    # Identification
    activite_id: Optional[int] = Field(default=None, foreign_key="activite.id")
    nature_depense_id: int = Field(foreign_key="nature_depense.id")
    libelle: str  # Description de la ligne
    
    # Montants (en FCFA)
    budget_n_moins_1: Decimal = Field(default=0, decimal_places=2)  # Année précédente
    budget_demande: Decimal = Field(default=0, decimal_places=2)  # Demandé pour N
    budget_valide: Decimal = Field(default=0, decimal_places=2)  # Validé après conférence
    
    # Justification
    justification: Optional[str] = None
    priorite: str = "Normale"  # Faible, Normale, Élevée, Critique
    
    # Metadata
    ordre: int = Field(default=0)  # Pour l'ordre d'affichage
    actif: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentBudget(SQLModel, table=True):
    """
    Documents et pièces jointes pour les fiches techniques
    """
    __tablename__ = "document_budget"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    fiche_technique_id: int = Field(foreign_key="fiche_technique.id")
    
    # Document
    type_document: str  # Devis, Facture, Note justificative, Plan d'action, etc.
    nom_fichier: str
    file_path: str
    taille_octets: int
    
    # Metadata
    uploaded_by_user_id: int = Field(foreign_key="user.id")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    actif: bool = True


class HistoriqueBudget(SQLModel, table=True):
    """
    Historique des modifications d'une fiche technique
    Traçabilité complète
    """
    __tablename__ = "historique_budget"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    fiche_technique_id: int = Field(foreign_key="fiche_technique.id")
    
    # Changement
    action: str  # Création, Modification, Validation, Rejet, Approbation
    ancien_statut: Optional[str] = None
    nouveau_statut: Optional[str] = None
    
    montant_avant: Optional[Decimal] = Field(default=None, decimal_places=2)
    montant_apres: Optional[Decimal] = Field(default=None, decimal_places=2)
    
    commentaire: Optional[str] = None
    
    # Traçabilité
    user_id: int = Field(foreign_key="user.id")
    date_action: datetime = Field(default_factory=datetime.utcnow)


class ExecutionBudgetaire(SQLModel, table=True):
    """
    Suivi de l'exécution budgétaire en cours d'année
    Mandatement, engagements, disponible
    """
    __tablename__ = "execution_budgetaire"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Période
    annee: int
    mois: int  # 1-12
    periode: str  # "2025-06" pour faciliter les requêtes
    
    # Hiérarchie
    programme_id: int = Field(foreign_key="programme.id")
    direction_id: Optional[int] = Field(default=None, foreign_key="direction.id")
    nature_depense_id: Optional[int] = Field(default=None, foreign_key="nature_depense.id")
    
    # Montants (en FCFA)
    budget_vote: Decimal = Field(default=0, decimal_places=2)  # Budget voté
    engagements: Decimal = Field(default=0, decimal_places=2)  # Engagements pris
    mandats_vises: Decimal = Field(default=0, decimal_places=2)  # Mandats visés
    mandats_pec: Decimal = Field(default=0, decimal_places=2)  # Mandats PEC (Pris En Charge)
    disponible: Decimal = Field(default=0, decimal_places=2)  # Budget - Engagements
    
    # Taux calculés (%)
    taux_engagement: Decimal = Field(default=0, decimal_places=2)  # Engagements / Budget
    taux_mandatement: Decimal = Field(default=0, decimal_places=2)  # Mandats PEC / Budget
    taux_execution: Decimal = Field(default=0, decimal_places=2)  # Global
    
    # Metadata
    date_maj: datetime = Field(default_factory=datetime.utcnow)
    updated_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ConferenceBudgetaire(SQLModel, table=True):
    """
    Session de conférence budgétaire (interne ou ministérielle)
    """
    __tablename__ = "conference_budgetaire"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Identification
    numero_conference: str = Field(index=True)  # CB-2025-INT-001
    type_conference: str  # "Interne" ou "Ministérielle"
    annee_budget: int  # 2025, 2026
    
    # Programme concerné
    programme_id: Optional[int] = Field(default=None, foreign_key="programme.id")
    
    # Dates
    date_conference: date
    heure_debut: Optional[str] = None
    heure_fin: Optional[str] = None
    
    # Participants
    organisateur_user_id: int = Field(foreign_key="user.id")
    participants: Optional[str] = None  # JSON ou texte avec liste participants
    
    # Résultats
    ordre_du_jour: Optional[str] = None
    compte_rendu: Optional[str] = None
    decisions: Optional[str] = None
    
    # Statut
    statut: str = "Planifiée"  # Planifiée, En cours, Terminée, Annulée
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# NOUVEAUX MODÈLES POUR FICHE TECHNIQUE HIÉRARCHIQUE
# ============================================

class ActionBudgetaire(SQLModel, table=True):
    """
    Action budgétaire (niveau 1 de la hiérarchie)
    Ex: "Pilotage, suivi et évaluation de l'administration douanière"
    """
    __tablename__ = "actions_budgetaires"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    fiche_technique_id: int = Field(foreign_key="fiche_technique.id")
    
    # Nature de dépense
    nature_depense: Optional[str] = Field(default=None, max_length=100)  # "BIENS ET SERVICES", "INVESTISSEMENTS", etc.
    
    # Code et libellé
    code: str = Field(max_length=20)  # Ex: "2208401"
    libelle: str = Field(max_length=500)  # Ex: "Action : 2208401 Pilotage, suivi et évaluation..."
    
    # Montants (en FCFA) - N = année précédente, N+1 = année suivante
    budget_vote_n: Decimal = Field(default=0, decimal_places=2)
    budget_actuel_n: Decimal = Field(default=0, decimal_places=2)
    enveloppe_n_plus_1: Decimal = Field(default=0, decimal_places=2)
    complement_solicite: Decimal = Field(default=0, decimal_places=2)
    budget_souhaite: Decimal = Field(default=0, decimal_places=2)
    engagement_etat: Decimal = Field(default=0, decimal_places=2)
    autre_complement: Decimal = Field(default=0, decimal_places=2)
    projet_budget_n_plus_1: Decimal = Field(default=0, decimal_places=2)
    
    # Justificatifs
    justificatifs: Optional[str] = None
    
    # Metadata
    ordre: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ServiceBeneficiaire(SQLModel, table=True):
    """
    Service bénéficiaire (niveau 2 de la hiérarchie)
    Ex: "Service Bénéficiaire : DR BOUAKE"
    """
    __tablename__ = "services_beneficiaires"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    fiche_technique_id: int = Field(foreign_key="fiche_technique.id")
    action_id: int = Field(foreign_key="actions_budgetaires.id")
    
    # Code et libellé
    code: str = Field(max_length=20)  # Ex: "DR_BOUAKE"
    libelle: str = Field(max_length=500)  # Ex: "Service Bénéficiaire : DR BOUAKE"
    
    # Metadata
    ordre: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ActiviteBudgetaire(SQLModel, table=True):
    """
    Activité budgétaire (niveau 3 de la hiérarchie)
    Ex: "Activité: 17011200103 Cordonner les activités de l'administration douanière à Bouaké"
    """
    __tablename__ = "activites_budgetaires"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    fiche_technique_id: int = Field(foreign_key="fiche_technique.id")
    service_beneficiaire_id: int = Field(foreign_key="services_beneficiaires.id")
    
    # Code et libellé
    code: str = Field(max_length=20)  # Ex: "17011200103"
    libelle: str = Field(max_length=500)  # Ex: "Activité: 17011200103 Cordonner les activités..."
    
    # Montants (en FCFA) - Même structure que Action
    budget_vote_n: Decimal = Field(default=0, decimal_places=2)
    budget_actuel_n: Decimal = Field(default=0, decimal_places=2)
    enveloppe_n_plus_1: Decimal = Field(default=0, decimal_places=2)
    complement_solicite: Decimal = Field(default=0, decimal_places=2)
    budget_souhaite: Decimal = Field(default=0, decimal_places=2)
    engagement_etat: Decimal = Field(default=0, decimal_places=2)
    autre_complement: Decimal = Field(default=0, decimal_places=2)
    projet_budget_n_plus_1: Decimal = Field(default=0, decimal_places=2)
    
    # Justificatifs
    justificatifs: Optional[str] = None
    
    # Metadata
    ordre: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LigneBudgetaireDetail(SQLModel, table=True):
    """
    Ligne budgétaire détaillée (niveau 4 - le plus bas niveau)
    Ex: "601100 Achats de petits matériels, fournitures de bureau et documentation"
    """
    __tablename__ = "lignes_budgetaires_detail"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    fiche_technique_id: int = Field(foreign_key="fiche_technique.id")
    activite_id: int = Field(foreign_key="activites_budgetaires.id")
    
    # Code et libellé
    code: str = Field(max_length=20)  # Ex: "601100"
    libelle: str = Field(max_length=500)  # Ex: "601100 Achats de petits matériels..."
    
    # Montants (en FCFA) - Même structure que Action/Activite
    budget_vote_n: Decimal = Field(default=0, decimal_places=2)
    budget_actuel_n: Decimal = Field(default=0, decimal_places=2)
    enveloppe_n_plus_1: Decimal = Field(default=0, decimal_places=2)
    complement_solicite: Decimal = Field(default=0, decimal_places=2)
    budget_souhaite: Decimal = Field(default=0, decimal_places=2)
    engagement_etat: Decimal = Field(default=0, decimal_places=2)
    autre_complement: Decimal = Field(default=0, decimal_places=2)
    projet_budget_n_plus_1: Decimal = Field(default=0, decimal_places=2)
    
    # Justificatifs
    justificatifs: Optional[str] = None
    
    # Metadata
    ordre: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

