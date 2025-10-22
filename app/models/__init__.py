"""
Models de l'application
"""

from app.models.activity import Activity
from app.models.besoins import BesoinAgent, ConsolidationBesoin, SuiviBesoin
from app.models.budget import (
    ActionBudgetaire,
    Activite,
    ActiviteBudgetaire,
    DocumentBudget,
    DocumentLigneBudgetaire,
    ExecutionBudgetaire,
    FicheTechnique,
    HistoriqueBudget,
    LigneBudgetaire,
    LigneBudgetaireDetail,
    NatureDepense,
    ServiceBeneficiaire,
    SigobeChargement,
    SigobeExecution,
    SigobeKpi,
)
from app.models.file import File
from app.models.personnel import (
    AgentComplet,
    Direction,
    DocumentAgent,
    EvaluationAgent,
    GradeComplet,
    HistoriqueCarriere,
    Programme,
    Service,
)
from app.models.performance import (
    EvaluationPerformance,
    IndicateurPerformance,
    ObjectifPerformance,
    ProgrammePerformance,
    RapportPerformance,
)
from app.models.rh import Agent, Grade, HRRequest, WorkflowHistory, WorkflowStep
from app.models.session import UserSession
from app.models.workflow_config import (
    CustomRole,
    CustomRoleAssignment,
    RequestTypeCustom,
    WorkflowConfigHistory,
    WorkflowTemplate,
    WorkflowTemplateStep,
)
from app.models.stock import (
    Article,
    CategorieArticle,
    DemandeStock,
    Fournisseur,
    Inventaire,
    LigneInventaire,
    MouvementStock,
)
from app.models.system_settings import SystemSettings
from app.models.user import User

__all__ = [
    "ActionBudgetaire",
    "Activite",
    "ActiviteBudgetaire",
    "Activity",
    "Agent",
    "AgentComplet",
    "Article",
    "BesoinAgent",
    "CategorieArticle",
    "ConsolidationBesoin",
    "CustomRole",
    "CustomRoleAssignment",
    "DemandeStock",
    "Direction",
    "DocumentAgent",
    "DocumentBudget",
    "DocumentLigneBudgetaire",
    "EvaluationAgent",
    "EvaluationPerformance",
    "ExecutionBudgetaire",
    "FicheTechnique",
    "File",
    "Fournisseur",
    "Grade",
    "GradeComplet",
    "HRRequest",
    "HistoriqueBudget",
    "HistoriqueCarriere",
    "IndicateurPerformance",
    "Inventaire",
    "LigneBudgetaire",
    "LigneBudgetaireDetail",
    "LigneInventaire",
    "MouvementStock",
    "NatureDepense",
    "ObjectifPerformance",
    "Programme",
    "ProgrammePerformance",
    "RapportPerformance",
    "RequestTypeCustom",
    "Service",
    "ServiceBeneficiaire",
    "SigobeChargement",
    "SigobeExecution",
    "SigobeKpi",
    "SuiviBesoin",
    "SystemSettings",
    "User",
    "UserSession",
    "WorkflowConfigHistory",
    "WorkflowHistory",
    "WorkflowStep",
    "WorkflowTemplate",
    "WorkflowTemplateStep",
]
