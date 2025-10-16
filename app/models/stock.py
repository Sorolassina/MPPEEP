# app/models/stock.py
"""
Modèles de données pour le système de gestion des stocks
"""
from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from decimal import Decimal

from sqlmodel import SQLModel, Field


# ============================================
# RÉFÉRENTIELS
# ============================================

class CategorieArticle(SQLModel, table=True):
    """Catégories d'articles (Fournitures, Matériel IT, Mobilier, etc.)"""
    __tablename__ = "categorie_article"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, max_length=20)
    libelle: str = Field(max_length=200)
    description: Optional[str] = None


class Fournisseur(SQLModel, table=True):
    """Fournisseurs"""
    __tablename__ = "fournisseur"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, max_length=50)
    nom: str = Field(max_length=200)
    telephone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=100)
    adresse: Optional[str] = None
    actif: bool = Field(default=True)


# ============================================
# ARTICLES
# ============================================

class Article(SQLModel, table=True):
    """Articles en stock"""
    __tablename__ = "article"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True, max_length=50)
    designation: str = Field(max_length=200)
    description: Optional[str] = None
    
    # Classification
    categorie_id: Optional[int] = Field(default=None, foreign_key="categorie_article.id")
    unite: str = Field(default="Unité", max_length=20)  # Unité, Pièce, Carton, Lot, etc.
    
    # Stock
    quantite_stock: Decimal = Field(default=0, max_digits=10, decimal_places=2)
    quantite_min: Decimal = Field(default=0, max_digits=10, decimal_places=2)  # Seuil d'alerte
    quantite_max: Decimal = Field(default=0, max_digits=10, decimal_places=2)  # Stock maximum
    
    # Prix
    prix_unitaire: Optional[Decimal] = Field(default=None, max_digits=15, decimal_places=2)
    
    # Localisation
    emplacement: Optional[str] = Field(default=None, max_length=100)  # Magasin A - Rayon 3
    
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
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Article concerné
    article_id: int = Field(foreign_key="article.id")
    
    # Type de mouvement
    type_mouvement: str = Field(max_length=20)  # ENTREE, SORTIE, AJUSTEMENT, INVENTAIRE
    
    # Quantités
    quantite: Decimal = Field(max_digits=10, decimal_places=2)
    quantite_avant: Decimal = Field(max_digits=10, decimal_places=2)  # Stock avant mouvement
    quantite_apres: Decimal = Field(max_digits=10, decimal_places=2)   # Stock après mouvement
    
    # Détails
    motif: Optional[str] = Field(default=None, max_length=100)  # Achat, Distribution, Perte, etc.
    reference_document: Optional[str] = Field(default=None, max_length=100)  # N° bon de commande, etc.
    
    # Fournisseur (pour les entrées)
    fournisseur_id: Optional[int] = Field(default=None, foreign_key="fournisseur.id")
    
    # Bénéficiaire (pour les sorties)
    beneficiaire: Optional[str] = Field(default=None, max_length=200)  # Service/Agent bénéficiaire
    
    # Prix réel du mouvement (peut différer du prix de l'article en cas de réduction)
    prix_unitaire_reel: Optional[Decimal] = Field(default=None, max_digits=15, decimal_places=2)
    montant_total: Optional[Decimal] = Field(default=None, max_digits=15, decimal_places=2)  # quantite * prix_unitaire_reel
    
    # Document justificatif (bon de commande, bon de livraison, etc.)
    document_path: Optional[str] = Field(default=None, max_length=500)
    document_filename: Optional[str] = Field(default=None, max_length=200)
    
    # Observations
    observations: Optional[str] = None
    
    # Traçabilité
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    date_mouvement: date = Field(default_factory=date.today)
    created_at: datetime = Field(default_factory=datetime.now)


# ============================================
# DEMANDES DE STOCK
# ============================================

class DemandeStock(SQLModel, table=True):
    """Demandes de sortie/approvisionnement de stock"""
    __tablename__ = "demande_stock"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Numéro de demande
    numero: str = Field(index=True, max_length=50)  # DEM-2025-001
    
    # Type
    type_demande: str = Field(max_length=20)  # SORTIE, APPROVISIONNEMENT
    
    # Demandeur
    demandeur_id: int = Field(foreign_key="user.id")
    service_demandeur: Optional[str] = Field(default=None, max_length=100)
    
    # Article demandé
    article_id: int = Field(foreign_key="article.id")
    quantite_demandee: Decimal = Field(max_digits=10, decimal_places=2)
    
    # Justification
    motif: str = Field(max_length=200)
    description: Optional[str] = None
    
    # Document justificatif
    document_path: Optional[str] = Field(default=None, max_length=500)
    document_filename: Optional[str] = Field(default=None, max_length=200)
    
    # État
    statut: str = Field(default="EN_ATTENTE", max_length=20)  # EN_ATTENTE, VALIDEE, REJETEE, SERVIE
    
    # Validation
    valideur_id: Optional[int] = Field(default=None, foreign_key="user.id")
    date_validation: Optional[date] = None
    commentaire_validation: Optional[str] = None
    
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
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Référence
    numero: str = Field(index=True, max_length=50)  # INV-2025-001
    libelle: str = Field(max_length=200)
    
    # Période
    date_debut: date
    date_fin: Optional[date] = None
    
    # État
    statut: str = Field(default="EN_COURS", max_length=20)  # EN_COURS, CLOTURE
    
    # Observations
    observations: Optional[str] = None
    
    # Traçabilité
    responsable_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class LigneInventaire(SQLModel, table=True):
    """Lignes d'inventaire (comptage par article)"""
    __tablename__ = "ligne_inventaire"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Inventaire parent
    inventaire_id: int = Field(foreign_key="inventaire.id")
    
    # Article
    article_id: int = Field(foreign_key="article.id")
    
    # Quantités
    quantite_theorique: Decimal = Field(max_digits=10, decimal_places=2)  # Stock système
    quantite_physique: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)  # Comptage réel
    ecart: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)  # Différence
    
    # Observations
    observations: Optional[str] = None
    
    # Traçabilité
    compteur_id: Optional[int] = Field(default=None, foreign_key="user.id")
    date_comptage: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

