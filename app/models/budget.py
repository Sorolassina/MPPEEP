# app/models/budget.py
"""
Modèles pour la gestion budgétaire
"""

from datetime import date, datetime
from decimal import Decimal

from sqlmodel import Field, SQLModel


class NatureDepense(SQLModel, table=True):
    """
    Nature de dépenses (BS, P, I, T)
    """

    __tablename__ = "nature_depense"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)  # BS, P, I, T
    libelle: str  # Biens & Services, Personnel, Investissement, Transferts
    description: str | None = None
    actif: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Activite(SQLModel, table=True):
    """
    Activités budgétaires (actions, projets)
    Chargées depuis Excel
    """

    __tablename__ = "activite"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True)
    libelle: str
    programme_id: int | None = Field(default=None, foreign_key="programme.id")
    direction_id: int | None = Field(default=None, foreign_key="direction.id")
    nature_depense_id: int | None = Field(default=None, foreign_key="nature_depense.id")
    description: str | None = None
    actif: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FicheTechnique(SQLModel, table=True):
    """
    Fiche technique budgétaire
    Document central de demande budgétaire par programme
    """

    __tablename__ = "fiche_technique"

    id: int | None = Field(default=None, primary_key=True)

    # Identification
    numero_fiche: str = Field(index=True, unique=True)  # FT-2025-P01-001
    annee_budget: int  # 2025, 2026, etc.
    programme_id: int = Field(foreign_key="programme.id")
    direction_id: int | None = Field(default=None, foreign_key="direction.id")

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
    note_justificative: str | None = None
    observations: str | None = None

    # Statut
    statut: str = "Brouillon"  # Brouillon, Soumis, Validé, Rejeté, Approuvé
    phase: str = "Préparation"  # Préparation, Révision, Validation

    # Dates
    date_creation: date = Field(default_factory=date.today)
    date_soumission: date | None = None
    date_validation: date | None = None

    # Traçabilité
    created_by_user_id: int | None = Field(default=None, foreign_key="user.id")
    updated_by_user_id: int | None = Field(default=None, foreign_key="user.id")
    validated_by_user_id: int | None = Field(default=None, foreign_key="user.id")

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

    id: int | None = Field(default=None, primary_key=True)
    fiche_technique_id: int = Field(foreign_key="fiche_technique.id")

    # Identification
    activite_id: int | None = Field(default=None, foreign_key="activite.id")
    nature_depense_id: int = Field(foreign_key="nature_depense.id")
    libelle: str  # Description de la ligne

    # Montants (en FCFA)
    budget_n_moins_1: Decimal = Field(default=0, decimal_places=2)  # Année précédente
    budget_demande: Decimal = Field(default=0, decimal_places=2)  # Demandé pour N
    budget_valide: Decimal = Field(default=0, decimal_places=2)  # Validé après révision

    # Justification
    justification: str | None = None
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

    id: int | None = Field(default=None, primary_key=True)
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

    id: int | None = Field(default=None, primary_key=True)
    fiche_technique_id: int = Field(foreign_key="fiche_technique.id")

    # Changement
    action: str  # Création, Modification, Validation, Rejet, Approbation
    ancien_statut: str | None = None
    nouveau_statut: str | None = None

    montant_avant: Decimal | None = Field(default=None, decimal_places=2)
    montant_apres: Decimal | None = Field(default=None, decimal_places=2)

    commentaire: str | None = None

    # Traçabilité
    user_id: int = Field(foreign_key="user.id")
    date_action: datetime = Field(default_factory=datetime.utcnow)


class ExecutionBudgetaire(SQLModel, table=True):
    """
    Suivi de l'exécution budgétaire en cours d'année
    Mandatement, engagements, disponible
    """

    __tablename__ = "execution_budgetaire"

    id: int | None = Field(default=None, primary_key=True)

    # Période
    annee: int
    mois: int  # 1-12
    periode: str  # "2025-06" pour faciliter les requêtes

    # Hiérarchie
    programme_id: int = Field(foreign_key="programme.id")
    direction_id: int | None = Field(default=None, foreign_key="direction.id")
    nature_depense_id: int | None = Field(default=None, foreign_key="nature_depense.id")

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
    updated_by_user_id: int | None = Field(default=None, foreign_key="user.id")
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

    id: int | None = Field(default=None, primary_key=True)
    fiche_technique_id: int = Field(foreign_key="fiche_technique.id")

    # Nature de dépense
    nature_depense: str | None = Field(default=None, max_length=100)  # "BIENS ET SERVICES", "INVESTISSEMENTS", etc.

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
    justificatifs: str | None = None

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

    id: int | None = Field(default=None, primary_key=True)
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

    id: int | None = Field(default=None, primary_key=True)
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
    justificatifs: str | None = None

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

    id: int | None = Field(default=None, primary_key=True)
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
    justificatifs: str | None = None

    # Metadata
    ordre: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentLigneBudgetaire(SQLModel, table=True):
    """
    Documents justificatifs attachés aux lignes budgétaires
    Chaque document est renommé selon le format: CodeAction_CodeActivité_CodeLigne_NomOriginal.ext
    """

    __tablename__ = "documents_lignes_budgetaires"

    id: int | None = Field(default=None, primary_key=True)
    ligne_budgetaire_id: int = Field(foreign_key="lignes_budgetaires_detail.id")
    fiche_technique_id: int = Field(foreign_key="fiche_technique.id")

    # Informations du fichier
    nom_fichier_original: str = Field(max_length=255)  # Nom original
    nom_fichier_stocke: str = Field(max_length=500)  # Format: CodeAction_CodeActivité_CodeLigne_NomOriginal.ext
    chemin_fichier: str = Field(max_length=1000)  # Chemin complet: uploads/budget/lignes/{ligne_id}/...
    type_fichier: str = Field(max_length=50)  # Extension: .pdf, .xlsx, etc.
    taille_octets: int = Field(default=0)  # Taille en octets

    # Codes pour identification rapide et traçabilité
    code_action: str = Field(max_length=50)
    code_activite: str = Field(max_length=50)
    code_ligne: str = Field(max_length=50)

    # Metadata
    uploaded_by_user_id: int = Field(foreign_key="user.id")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    actif: bool = Field(default=True)


# ============================================
# SIGOBE - Système d'Information de Gestion et d'Observation Budgétaire
# ============================================


class SigobeChargement(SQLModel, table=True):
    """
    Historique des chargements SIGOBE
    Trace chaque import de fichier d'exécution budgétaire
    """

    __tablename__ = "sigobe_chargement"

    id: int | None = Field(default=None, primary_key=True)

    # Période
    annee: int
    trimestre: int | None = None  # 1, 2, 3, 4 (null si annuel)
    periode_libelle: str  # "T1 2024", "Annuel 2024", etc.

    # Métadonnées fichier
    nom_fichier: str
    taille_octets: int
    chemin_fichier: str

    # Résumé import
    nb_lignes_importees: int = 0
    nb_programmes: int = 0
    nb_actions: int = 0

    # Statut
    statut: str = "En cours"  # En cours, Terminé, Erreur
    message_erreur: str | None = None

    # Traçabilité
    uploaded_by_user_id: int = Field(foreign_key="user.id")
    date_chargement: datetime = Field(default_factory=datetime.utcnow)


class SigobeExecution(SQLModel, table=True):
    """
    Données d'exécution budgétaire SIGOBE
    Lignes détaillées d'exécution par programme/action/activité
    """

    __tablename__ = "sigobe_execution"

    id: int | None = Field(default=None, primary_key=True)

    # Lien avec le chargement
    chargement_id: int = Field(foreign_key="sigobe_chargement.id", index=True)

    # Période et classification
    annee: int = Field(index=True)
    trimestre: int | None = None
    periode: date | None = None  # Date de période si disponible
    section: str | None = None  # Section budgétaire
    categorie: str | None = None  # Catégorie
    type_credit: str | None = None  # Type de crédit

    # Hiérarchie budgétaire (jusqu'à 6 niveaux)
    programmes: str | None = Field(max_length=500, index=True)
    actions: str | None = Field(max_length=500, index=True)
    rprog: str | None = Field(max_length=500)  # Responsable programme
    type_depense: str | None = Field(max_length=200, index=True)  # Nature dépense
    activites: str | None = Field(max_length=500)
    taches: str | None = Field(max_length=500)

    # Montants financiers (en FCFA)
    budget_vote: Decimal | None = Field(default=0, decimal_places=2, max_digits=18)
    budget_actuel: Decimal | None = Field(default=0, decimal_places=2, max_digits=18)
    engagements_emis: Decimal | None = Field(default=0, decimal_places=2, max_digits=18)
    disponible_eng: Decimal | None = Field(default=0, decimal_places=2, max_digits=18)
    mandats_emis: Decimal | None = Field(default=0, decimal_places=2, max_digits=18)
    mandats_vise_cf: Decimal | None = Field(default=0, decimal_places=2, max_digits=18)
    mandats_pec: Decimal | None = Field(default=0, decimal_places=2, max_digits=18)

    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SigobeKpi(SQLModel, table=True):
    """
    KPIs agrégés SIGOBE
    Pré-calculs pour le dashboard (performance)
    """

    __tablename__ = "sigobe_kpi"

    id: int | None = Field(default=None, primary_key=True)

    # Période
    annee: int = Field(index=True)
    trimestre: int | None = None

    # Dimension (Programme, Nature, Global)
    dimension: str = Field(index=True)  # "global", "programme", "nature"
    dimension_code: str | None = None  # Code programme ou nature
    dimension_libelle: str | None = None

    # KPIs calculés
    budget_vote_total: Decimal = Field(default=0, decimal_places=2, max_digits=18)
    budget_actuel_total: Decimal = Field(default=0, decimal_places=2, max_digits=18)
    engagements_total: Decimal = Field(default=0, decimal_places=2, max_digits=18)
    mandats_total: Decimal = Field(default=0, decimal_places=2, max_digits=18)

    taux_engagement: Decimal | None = Field(default=0, decimal_places=4, max_digits=8)  # %
    taux_mandatement: Decimal | None = Field(default=0, decimal_places=4, max_digits=8)  # %
    taux_execution: Decimal | None = Field(default=0, decimal_places=4, max_digits=8)  # %

    # Traçabilité
    chargement_id: int = Field(foreign_key="sigobe_chargement.id")
    date_calcul: datetime = Field(default_factory=datetime.utcnow)
