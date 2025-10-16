# app/services/stock_service.py
"""
Service de gestion des stocks
Contient toute la logique métier liée à la gestion des stocks
"""
from typing import Optional, Dict, Any, List
from datetime import date, datetime
from decimal import Decimal
from sqlmodel import Session, select, func
from app.core.logging_config import get_logger

from app.models.stock import (
    Article, CategorieArticle, Fournisseur,
    MouvementStock, DemandeStock, Inventaire, LigneInventaire
)

logger = get_logger(__name__)


class StockService:
    """Service de gestion des stocks"""
    
    # ============================================
    # KPIs & STATISTIQUES
    # ============================================
    
    @staticmethod
    def get_kpis(session: Session) -> Dict[str, Any]:
        """Récupère les indicateurs clés de performance"""
        
        # Total articles
        total_articles = session.exec(select(func.count(Article.id))).one()
        
        # Articles actifs
        articles_actifs = session.exec(
            select(func.count(Article.id)).where(Article.actif == True)
        ).one()
        
        # Articles en rupture (quantité <= quantité_min)
        articles_rupture = session.exec(
            select(func.count(Article.id)).where(
                Article.quantite_stock <= Article.quantite_min
            )
        ).one()
        
        # Valeur totale du stock
        valeur_stock = session.exec(
            select(func.sum(Article.quantite_stock * Article.prix_unitaire)).where(
                Article.actif == True
            )
        ).one() or 0
        
        # Demandes
        total_demandes = session.exec(select(func.count(DemandeStock.id))).one()
        
        demandes_en_attente = session.exec(
            select(func.count(DemandeStock.id)).where(
                DemandeStock.statut == "EN_ATTENTE"
            )
        ).one()
        
        demandes_validees = session.exec(
            select(func.count(DemandeStock.id)).where(
                DemandeStock.statut == "VALIDEE"
            )
        ).one()
        
        # Mouvements du mois en cours
        premier_jour_mois = date.today().replace(day=1)
        
        mouvements_entree = session.exec(
            select(func.count(MouvementStock.id)).where(
                MouvementStock.type_mouvement == "ENTREE",
                MouvementStock.date_mouvement >= premier_jour_mois
            )
        ).one()
        
        mouvements_sortie = session.exec(
            select(func.count(MouvementStock.id)).where(
                MouvementStock.type_mouvement == "SORTIE",
                MouvementStock.date_mouvement >= premier_jour_mois
            )
        ).one()
        
        return {
            "total_articles": total_articles,
            "articles_actifs": articles_actifs,
            "articles_rupture": articles_rupture,
            "valeur_stock": float(valeur_stock),
            "total_demandes": total_demandes,
            "demandes_en_attente": demandes_en_attente,
            "demandes_validees": demandes_validees,
            "mouvements_entree": mouvements_entree,
            "mouvements_sortie": mouvements_sortie
        }
    
    # ============================================
    # GESTION DES ARTICLES
    # ============================================
    
    @staticmethod
    def creer_article(
        session: Session,
        code: str,
        designation: str,
        categorie_id: Optional[int] = None,
        unite: str = "Unité",
        quantite_min: Decimal = Decimal(0),
        prix_unitaire: Optional[Decimal] = None,
        **kwargs
    ) -> Article:
        """Crée un nouvel article"""
        
        # Vérifier que le code est unique
        existing = session.exec(
            select(Article).where(Article.code == code)
        ).first()
        
        if existing:
            raise ValueError(f"Un article avec le code '{code}' existe déjà")
        
        article = Article(
            code=code,
            designation=designation,
            categorie_id=categorie_id,
            unite=unite,
            quantite_min=quantite_min,
            prix_unitaire=prix_unitaire,
            **kwargs
        )
        
        session.add(article)
        session.commit()
        session.refresh(article)
        
        logger.info(f"Article créé : {code} - {designation}")
        return article
    
    # ============================================
    # MOUVEMENTS DE STOCK
    # ============================================
    
    @staticmethod
    def enregistrer_mouvement(
        session: Session,
        article_id: int,
        type_mouvement: str,  # ENTREE, SORTIE, AJUSTEMENT
        quantite: Decimal,
        motif: str,
        user_id: int,
        fournisseur_id: Optional[int] = None,
        beneficiaire: Optional[str] = None,
        document_path: Optional[str] = None,
        document_filename: Optional[str] = None,
        **kwargs
    ) -> tuple[MouvementStock, Optional[str]]:
        """
        Enregistre un mouvement de stock et met à jour les quantités
        
        Returns:
            tuple: (mouvement, alerte)
            - mouvement: L'objet MouvementStock créé
            - alerte: Message d'alerte si stock sous le minimum, None sinon
        """
        
        # Récupérer l'article
        article = session.get(Article, article_id)
        if not article:
            raise ValueError(f"Article {article_id} introuvable")
        
        # Sauvegarder quantité avant
        quantite_avant = article.quantite_stock
        
        # Calculer nouvelle quantité
        if type_mouvement == "ENTREE":
            quantite_apres = quantite_avant + quantite
        elif type_mouvement == "SORTIE":
            quantite_apres = quantite_avant - quantite
            if quantite_apres < 0:
                raise ValueError(f"Stock insuffisant pour {article.designation}")
        elif type_mouvement == "AJUSTEMENT":
            quantite_apres = quantite  # Nouvelle quantité absolue
        else:
            raise ValueError(f"Type de mouvement invalide : {type_mouvement}")
        
        # Créer le mouvement
        mouvement = MouvementStock(
            article_id=article_id,
            type_mouvement=type_mouvement,
            quantite=quantite if type_mouvement != "AJUSTEMENT" else quantite - quantite_avant,
            quantite_avant=quantite_avant,
            quantite_apres=quantite_apres,
            motif=motif,
            fournisseur_id=fournisseur_id,
            beneficiaire=beneficiaire,
            document_path=document_path,
            document_filename=document_filename,
            user_id=user_id,
            **kwargs
        )
        
        # Mettre à jour le stock de l'article
        article.quantite_stock = quantite_apres
        article.updated_at = datetime.now()
        
        session.add(mouvement)
        session.add(article)
        session.commit()
        session.refresh(mouvement)
        
        # Vérifier le stock minimum
        alerte = None
        if quantite_apres <= article.quantite_min:
            if quantite_apres == 0:
                alerte = f"⚠️ RUPTURE DE STOCK : {article.designation} (Stock: 0)"
                logger.warning(f"RUPTURE DE STOCK : Article {article.code} - {article.designation}")
            else:
                alerte = f"⚠️ ALERTE STOCK FAIBLE : {article.designation} (Stock: {quantite_apres} {article.unite}, Min: {article.quantite_min} {article.unite})"
                logger.warning(f"Stock faible : Article {article.code} - Stock: {quantite_apres}, Min: {article.quantite_min}")
        
        logger.info(f"Mouvement {type_mouvement} : {article.designation} - {quantite} {article.unite}")
        return mouvement, alerte
    
    # ============================================
    # GESTION DES DEMANDES
    # ============================================
    
    @staticmethod
    def creer_demande(
        session: Session,
        type_demande: str,  # SORTIE, APPROVISIONNEMENT
        demandeur_id: int,
        article_id: int,
        quantite_demandee: Decimal,
        motif: str,
        document_path: Optional[str] = None,
        document_filename: Optional[str] = None,
        **kwargs
    ) -> DemandeStock:
        """Crée une demande de stock"""
        
        # Générer le numéro
        annee = date.today().year
        count = session.exec(
            select(func.count(DemandeStock.id)).where(
                DemandeStock.numero.like(f"DEM-{annee}-%")
            )
        ).one()
        numero = f"DEM-{annee}-{str(count + 1).zfill(4)}"
        
        demande = DemandeStock(
            numero=numero,
            type_demande=type_demande,
            demandeur_id=demandeur_id,
            article_id=article_id,
            quantite_demandee=quantite_demandee,
            motif=motif,
            document_path=document_path,
            document_filename=document_filename,
            **kwargs
        )
        
        session.add(demande)
        session.commit()
        session.refresh(demande)
        
        logger.info(f"Demande créée : {numero}")
        return demande
    
    @staticmethod
    def valider_demande(
        session: Session,
        demande_id: int,
        valideur_id: int,
        accepte: bool,
        commentaire: Optional[str] = None
    ) -> tuple[DemandeStock, Optional[str]]:
        """
        Valide ou rejette une demande
        
        Returns:
            tuple: (demande, alerte)
            - demande: L'objet DemandeStock mis à jour
            - alerte: Message d'alerte si applicable
        """
        
        demande = session.get(DemandeStock, demande_id)
        if not demande:
            raise ValueError(f"Demande {demande_id} introuvable")
        
        if demande.statut != "EN_ATTENTE":
            raise ValueError(f"La demande {demande.numero} n'est pas en attente")
        
        alerte = None
        
        # Si acceptée et c'est une SORTIE, vérifier le stock disponible
        if accepte and demande.type_demande == "SORTIE":
            disponible, msg = StockService.verifier_stock_disponible(
                session=session,
                article_id=demande.article_id,
                quantite_demandee=demande.quantite_demandee
            )
            if not disponible:
                raise ValueError(msg)
            if msg:  # Alerte de stock faible
                alerte = msg
        
        demande.valideur_id = valideur_id
        demande.date_validation = date.today()
        demande.commentaire_validation = commentaire
        demande.statut = "VALIDEE" if accepte else "REJETEE"
        demande.updated_at = datetime.now()
        
        session.add(demande)
        session.commit()
        session.refresh(demande)
        
        logger.info(f"Demande {demande.numero} : {'VALIDEE' if accepte else 'REJETEE'}")
        return demande, alerte
    
    # ============================================
    # INVENTAIRE
    # ============================================
    
    @staticmethod
    def creer_inventaire(
        session: Session,
        libelle: str,
        responsable_id: int,
        date_debut: date
    ) -> Inventaire:
        """Crée un nouvel inventaire"""
        
        # Générer le numéro
        annee = date_debut.year
        count = session.exec(
            select(func.count(Inventaire.id)).where(
                Inventaire.numero.like(f"INV-{annee}-%")
            )
        ).one()
        numero = f"INV-{annee}-{str(count + 1).zfill(3)}"
        
        inventaire = Inventaire(
            numero=numero,
            libelle=libelle,
            responsable_id=responsable_id,
            date_debut=date_debut
        )
        
        session.add(inventaire)
        session.commit()
        session.refresh(inventaire)
        
        # Créer les lignes d'inventaire pour tous les articles actifs
        articles = session.exec(
            select(Article).where(Article.actif == True)
        ).all()
        
        for article in articles:
            ligne = LigneInventaire(
                inventaire_id=inventaire.id,
                article_id=article.id,
                quantite_theorique=article.quantite_stock
            )
            session.add(ligne)
        
        session.commit()
        
        logger.info(f"Inventaire créé : {numero} avec {len(articles)} articles")
        return inventaire
    
    @staticmethod
    def enregistrer_comptage(
        session: Session,
        ligne_inventaire_id: int,
        quantite_physique: Decimal,
        compteur_id: int,
        observations: Optional[str] = None
    ) -> LigneInventaire:
        """Enregistre le comptage physique d'une ligne d'inventaire"""
        
        ligne = session.get(LigneInventaire, ligne_inventaire_id)
        if not ligne:
            raise ValueError(f"Ligne d'inventaire {ligne_inventaire_id} introuvable")
        
        ligne.quantite_physique = quantite_physique
        ligne.ecart = quantite_physique - ligne.quantite_theorique
        ligne.compteur_id = compteur_id
        ligne.date_comptage = date.today()
        ligne.observations = observations
        ligne.updated_at = datetime.now()
        
        session.add(ligne)
        session.commit()
        session.refresh(ligne)
        
        return ligne
    
    # ============================================
    # GESTION DES STOCKS MINIMUM
    # ============================================
    
    @staticmethod
    def get_articles_rupture(session: Session) -> List[Article]:
        """Récupère les articles en rupture (stock <= stock minimum)"""
        articles = session.exec(
            select(Article).where(
                Article.actif == True,
                Article.quantite_stock <= Article.quantite_min
            ).order_by(Article.quantite_stock)
        ).all()
        
        return list(articles)
    
    @staticmethod
    def get_articles_stock_faible(session: Session, seuil_pourcentage: float = 1.2) -> List[Article]:
        """
        Récupère les articles avec stock faible (entre min et min*seuil)
        
        Args:
            seuil_pourcentage: Multiplicateur du stock min (1.2 = 120% du stock min)
        """
        articles = session.exec(
            select(Article).where(
                Article.actif == True,
                Article.quantite_stock > Article.quantite_min,
                Article.quantite_stock <= Article.quantite_min * seuil_pourcentage
            ).order_by(Article.quantite_stock)
        ).all()
        
        return list(articles)
    
    @staticmethod
    def verifier_stock_disponible(
        session: Session,
        article_id: int,
        quantite_demandee: Decimal
    ) -> tuple[bool, Optional[str]]:
        """
        Vérifie si le stock est disponible pour une sortie
        
        Returns:
            tuple: (disponible, message)
            - disponible: True si le stock est suffisant
            - message: Message d'erreur ou d'alerte
        """
        article = session.get(Article, article_id)
        if not article:
            return False, f"Article {article_id} introuvable"
        
        stock_actuel = article.quantite_stock
        stock_apres = stock_actuel - quantite_demandee
        
        # Stock insuffisant
        if stock_apres < 0:
            return False, f"Stock insuffisant : Disponible {stock_actuel} {article.unite}, Demandé {quantite_demandee} {article.unite}"
        
        # Stock qui passera sous le minimum
        if stock_apres <= article.quantite_min:
            message = f"⚠️ Attention : Cette sortie fera passer le stock sous le minimum ({article.quantite_min} {article.unite}). Stock après sortie : {stock_apres} {article.unite}"
            return True, message
        
        # Stock OK
        return True, None
    
    @staticmethod
    def get_alertes_stock(session: Session) -> Dict[str, Any]:
        """Récupère toutes les alertes de stock"""
        
        # Articles en rupture
        ruptures = StockService.get_articles_rupture(session)
        
        # Articles à stock faible
        stock_faible = StockService.get_articles_stock_faible(session)
        
        # Articles proches du max (surstock)
        articles_surstock = session.exec(
            select(Article).where(
                Article.actif == True,
                Article.quantite_max > 0,
                Article.quantite_stock >= Article.quantite_max * Decimal("0.9")
            )
        ).all()
        
        return {
            "ruptures": [
                {
                    "id": a.id,
                    "code": a.code,
                    "designation": a.designation,
                    "stock": float(a.quantite_stock),
                    "stock_min": float(a.quantite_min),
                    "unite": a.unite
                }
                for a in ruptures
            ],
            "stock_faible": [
                {
                    "id": a.id,
                    "code": a.code,
                    "designation": a.designation,
                    "stock": float(a.quantite_stock),
                    "stock_min": float(a.quantite_min),
                    "unite": a.unite,
                    "pourcentage": float((a.quantite_stock / a.quantite_min * 100) if a.quantite_min > 0 else 0)
                }
                for a in stock_faible
            ],
            "surstock": [
                {
                    "id": a.id,
                    "code": a.code,
                    "designation": a.designation,
                    "stock": float(a.quantite_stock),
                    "stock_max": float(a.quantite_max),
                    "unite": a.unite
                }
                for a in articles_surstock
            ]
        }

