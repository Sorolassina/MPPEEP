# app/models/stock.py
"""
Modèles de données pour le système de gestion des stocks
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlmodel import Field, SQLModel

# ============================================
# RÉFÉRENTIELS
# ============================================


class CategorieArticle(SQLModel, table=True):
    """Catégories d'articles (Fournitures, Matériel IT, Mobilier, etc.)"""

    __tablename__ = "categorie_article"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, max_length=20)
    libelle: str = Field(max_length=200)
    description: str | None = None


class Fournisseur(SQLModel, table=True):
    """Fournisseurs"""

    __tablename__ = "fournisseur"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, max_length=50)
    nom: str = Field(max_length=200)
    telephone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=100)
    adresse: str | None = None
    actif: bool = Field(default=True)


# ============================================
# ARTICLES
# ============================================


class Article(SQLModel, table=True):
    """Articles en stock"""

    __tablename__ = "article"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True, max_length=50)
    designation: str = Field(max_length=200)
    description: str | None = None

    # Classification
    categorie_id: int | None = Field(default=None, foreign_key="categorie_article.id")
    unite: str = Field(default="Unité", max_length=20)  # Unité, Pièce, Carton, Lot, etc.

    # Stock
    quantite_stock: Decimal = Field(default=0, max_digits=10, decimal_places=2)
    quantite_min: Decimal = Field(default=0, max_digits=10, decimal_places=2)  # Seuil d'alerte
    quantite_max: Decimal = Field(default=0, max_digits=10, decimal_places=2)  # Stock maximum

    # Prix
    prix_unitaire: Decimal | None = Field(default=None, max_digits=15, decimal_places=2)

    # Localisation
    emplacement: str | None = Field(default=None, max_length=100)  # Magasin A - Rayon 3

    # ========================================
    # NOUVEAUTÉ : GESTION ARTICLES PÉRISSABLES
    # ========================================
    est_perissable: bool = Field(default=False)  # Article périssable (denrées, médicaments, etc.)
    duree_conservation_jours: int | None = Field(default=None)  # Durée de conservation standard
    seuil_alerte_peremption_jours: int = Field(default=30)  # Alerte X jours avant péremption

    # ========================================
    # NOUVEAUTÉ : GESTION AMORTISSEMENT MATÉRIEL
    # ========================================
    est_amortissable: bool = Field(default=False)  # Matériel amortissable (équipements, véhicules, etc.)
    date_acquisition: date | None = None  # Date d'achat du matériel
    valeur_acquisition: Decimal | None = Field(default=None, max_digits=15, decimal_places=2)  # Prix d'achat initial
    duree_amortissement_annees: int | None = Field(default=None)  # Durée d'amortissement (en années)
    taux_amortissement: Decimal | None = Field(
        default=None, max_digits=5, decimal_places=2
    )  # Taux d'amortissement annuel (%)
    valeur_residuelle: Decimal | None = Field(default=None, max_digits=15, decimal_places=2)  # Valeur résiduelle finale
    methode_amortissement: str | None = Field(default="LINEAIRE", max_length=20)  # LINEAIRE, DEGRESSIF, UNITE_OEUVRE

    # État
    actif: bool = Field(default=True)

    # Audit
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ============================================
# MOUVEMENTS DE STOCK
# ============================================


class MouvementStock(SQLModel, table=True):
    """Mouvements de stock (entrées/sorties)"""

    __tablename__ = "mouvement_stock"

    id: int | None = Field(default=None, primary_key=True)

    # Article concerné
    article_id: int = Field(foreign_key="article.id")

    # Type de mouvement
    type_mouvement: str = Field(max_length=20)  # ENTREE, SORTIE, AJUSTEMENT, INVENTAIRE

    # Quantités
    quantite: Decimal = Field(max_digits=10, decimal_places=2)
    quantite_avant: Decimal = Field(max_digits=10, decimal_places=2)  # Stock avant mouvement
    quantite_apres: Decimal = Field(max_digits=10, decimal_places=2)  # Stock après mouvement

    # Détails
    motif: str | None = Field(default=None, max_length=100)  # Achat, Distribution, Perte, etc.
    reference_document: str | None = Field(default=None, max_length=100)  # N° bon de commande, etc.

    # Fournisseur (pour les entrées)
    fournisseur_id: int | None = Field(default=None, foreign_key="fournisseur.id")

    # Bénéficiaire (pour les sorties)
    beneficiaire: str | None = Field(default=None, max_length=200)  # Service/Agent bénéficiaire

    # Prix réel du mouvement (peut différer du prix de l'article en cas de réduction)
    prix_unitaire_reel: Decimal | None = Field(default=None, max_digits=15, decimal_places=2)
    montant_total: Decimal | None = Field(
        default=None, max_digits=15, decimal_places=2
    )  # quantite * prix_unitaire_reel

    # Document justificatif (bon de commande, bon de livraison, etc.)
    document_path: str | None = Field(default=None, max_length=500)
    document_filename: str | None = Field(default=None, max_length=200)

    # Observations
    observations: str | None = None

    # Traçabilité
    user_id: int | None = Field(default=None, foreign_key="user.id")
    date_mouvement: date = Field(default_factory=date.today)
    created_at: datetime = Field(default_factory=datetime.now)


# ============================================
# DEMANDES DE STOCK
# ============================================


class DemandeStock(SQLModel, table=True):
    """Demandes de sortie/approvisionnement de stock"""

    __tablename__ = "demande_stock"

    id: int | None = Field(default=None, primary_key=True)

    # Numéro de demande
    numero: str = Field(index=True, max_length=50)  # DEM-2025-001

    # Type
    type_demande: str = Field(max_length=20)  # SORTIE, APPROVISIONNEMENT

    # Demandeur
    demandeur_id: int = Field(foreign_key="user.id")
    service_demandeur: str | None = Field(default=None, max_length=100)

    # Article demandé
    article_id: int = Field(foreign_key="article.id")
    quantite_demandee: Decimal = Field(max_digits=10, decimal_places=2)

    # Justification
    motif: str = Field(max_length=200)
    description: str | None = None

    # Document justificatif
    document_path: str | None = Field(default=None, max_length=500)
    document_filename: str | None = Field(default=None, max_length=200)

    # État
    statut: str = Field(default="EN_ATTENTE", max_length=20)  # EN_ATTENTE, VALIDEE, REJETEE, SERVIE

    # Validation
    valideur_id: int | None = Field(default=None, foreign_key="user.id")
    date_validation: date | None = None
    commentaire_validation: str | None = None

    # Traçabilité
    date_demande: date = Field(default_factory=date.today)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ============================================
# INVENTAIRE
# ============================================


class Inventaire(SQLModel, table=True):
    """Inventaires physiques"""

    __tablename__ = "inventaire"

    id: int | None = Field(default=None, primary_key=True)

    # Référence
    numero: str = Field(index=True, max_length=50)  # INV-2025-001
    libelle: str = Field(max_length=200)

    # Période
    date_debut: date
    date_fin: date | None = None

    # État
    statut: str = Field(default="EN_COURS", max_length=20)  # EN_COURS, CLOTURE

    # Observations
    observations: str | None = None

    # Traçabilité
    responsable_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class LigneInventaire(SQLModel, table=True):
    """Lignes d'inventaire (comptage par article)"""

    __tablename__ = "ligne_inventaire"

    id: int | None = Field(default=None, primary_key=True)

    # Inventaire parent
    inventaire_id: int = Field(foreign_key="inventaire.id")

    # Article
    article_id: int = Field(foreign_key="article.id")

    # Quantités
    quantite_theorique: Decimal = Field(max_digits=10, decimal_places=2)  # Stock système
    quantite_physique: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)  # Comptage réel
    ecart: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)  # Différence

    # Observations
    observations: str | None = None

    # Traçabilité
    compteur_id: int | None = Field(default=None, foreign_key="user.id")
    date_comptage: date | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ============================================
# NOUVEAUTÉ : GESTION DES LOTS PÉRISSABLES
# ============================================


class LotPerissable(SQLModel, table=True):
    """Suivi des lots d'articles périssables avec dates de péremption"""

    __tablename__ = "lot_perissable"

    id: int | None = Field(default=None, primary_key=True)

    # Article concerné
    article_id: int = Field(foreign_key="article.id")

    # Identification du lot
    numero_lot: str = Field(max_length=100, index=True)  # Numéro de lot fournisseur

    # Dates
    date_fabrication: date | None = None  # Date de fabrication
    date_reception: date = Field(default_factory=date.today)  # Date de réception
    date_peremption: date  # Date de péremption (OBLIGATOIRE)

    # Quantités
    quantite_initiale: Decimal = Field(max_digits=10, decimal_places=2)  # Quantité à la réception
    quantite_restante: Decimal = Field(max_digits=10, decimal_places=2)  # Quantité actuelle

    # Statut
    statut: str = Field(default="ACTIF", max_length=20)  # ACTIF, ALERTE, PERIME, EPUISE

    # Fournisseur
    fournisseur_id: int | None = Field(default=None, foreign_key="fournisseur.id")

    # Observations
    observations: str | None = None

    # Traçabilité
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ============================================
# NOUVEAUTÉ : AMORTISSEMENT DU MATÉRIEL
# ============================================


class Amortissement(SQLModel, table=True):
    """Historique des amortissements annuels du matériel"""

    __tablename__ = "amortissement"

    id: int | None = Field(default=None, primary_key=True)

    # Article concerné (matériel)
    article_id: int = Field(foreign_key="article.id")

    # Période
    annee: int = Field(index=True)  # Année d'amortissement
    periode: str = Field(max_length=50)  # Ex: "2025", "T1-2025", etc.

    # Calculs
    valeur_brute: Decimal = Field(max_digits=15, decimal_places=2)  # Valeur d'acquisition
    amortissement_cumule_debut: Decimal = Field(
        max_digits=15, decimal_places=2
    )  # Amortissement cumulé en début de période
    amortissement_periode: Decimal = Field(max_digits=15, decimal_places=2)  # Amortissement de la période
    amortissement_cumule_fin: Decimal = Field(max_digits=15, decimal_places=2)  # Amortissement cumulé en fin de période
    valeur_nette_comptable: Decimal = Field(max_digits=15, decimal_places=2)  # VNC = Valeur brute - Amort. cumulé

    # Détails de calcul
    taux_applique: Decimal = Field(max_digits=5, decimal_places=2)  # Taux utilisé (%)
    methode: str = Field(max_length=20)  # LINEAIRE, DEGRESSIF, UNITE_OEUVRE
    base_calcul: Decimal | None = Field(default=None, max_digits=15, decimal_places=2)  # Base de calcul si dégressif

    # Statut
    statut: str = Field(default="CALCULE", max_length=20)  # CALCULE, VALIDE, CLOTURE
    totalement_amorti: bool = Field(default=False)  # True si VNC = Valeur résiduelle

    # Observations
    observations: str | None = None

    # Traçabilité
    calcule_par_user_id: int | None = Field(default=None, foreign_key="user.id")
    date_calcul: date = Field(default_factory=date.today)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
