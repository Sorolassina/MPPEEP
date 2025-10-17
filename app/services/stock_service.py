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
    MouvementStock, DemandeStock, Inventaire, LigneInventaire,
    LotPerissable, Amortissement
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
    
    # ============================================
    # NOUVEAUTÉ : GESTION DES LOTS PÉRISSABLES
    # ============================================
    
    @staticmethod
    def creer_lot_perissable(
        session: Session,
        article_id: int,
        numero_lot: str,
        date_peremption: date,
        quantite: Decimal,
        fournisseur_id: Optional[int] = None,
        date_fabrication: Optional[date] = None,
        observations: Optional[str] = None
    ) -> LotPerissable:
        """Crée un nouveau lot d'article périssable"""
        
        # Vérifier que l'article existe et est périssable
        article = session.get(Article, article_id)
        if not article:
            raise ValueError(f"Article {article_id} introuvable")
        
        if not article.est_perissable:
            raise ValueError(f"L'article '{article.designation}' n'est pas défini comme périssable")
        
        # Vérifier si le lot existe déjà
        existing = session.exec(
            select(LotPerissable).where(
                LotPerissable.article_id == article_id,
                LotPerissable.numero_lot == numero_lot
            )
        ).first()
        
        if existing:
            raise ValueError(f"Le lot '{numero_lot}' existe déjà pour cet article")
        
        # Calculer le statut initial
        jours_avant_peremption = (date_peremption - date.today()).days
        
        if jours_avant_peremption < 0:
            statut = "PERIME"
        elif jours_avant_peremption <= article.seuil_alerte_peremption_jours:
            statut = "ALERTE"
        else:
            statut = "ACTIF"
        
        lot = LotPerissable(
            article_id=article_id,
            numero_lot=numero_lot,
            date_fabrication=date_fabrication,
            date_peremption=date_peremption,
            quantite_initiale=quantite,
            quantite_restante=quantite,
            statut=statut,
            fournisseur_id=fournisseur_id,
            observations=observations
        )
        
        session.add(lot)
        session.commit()
        session.refresh(lot)
        
        logger.info(f"Lot périssable créé : {numero_lot} - Article: {article.designation} - Péremption: {date_peremption}")
        return lot
    
    @staticmethod
    def get_lots_perissables_article(session: Session, article_id: int) -> List[LotPerissable]:
        """Récupère tous les lots d'un article périssable (triés par date de péremption)"""
        
        lots = session.exec(
            select(LotPerissable)
            .where(LotPerissable.article_id == article_id)
            .order_by(LotPerissable.date_peremption)
        ).all()
        
        return list(lots)
    
    @staticmethod
    def get_lots_a_perimer(session: Session, jours: int = 30) -> List[Dict[str, Any]]:
        """
        Récupère les lots qui vont périmer dans X jours
        
        Args:
            jours: Nombre de jours avant péremption pour l'alerte
        """
        from datetime import timedelta
        
        date_limite = date.today() + timedelta(days=jours)
        
        lots = session.exec(
            select(LotPerissable)
            .where(
                LotPerissable.date_peremption <= date_limite,
                LotPerissable.date_peremption >= date.today(),
                LotPerissable.quantite_restante > 0,
                LotPerissable.statut.in_(["ACTIF", "ALERTE"])
            )
            .order_by(LotPerissable.date_peremption)
        ).all()
        
        resultat = []
        for lot in lots:
            article = session.get(Article, lot.article_id)
            jours_restants = (lot.date_peremption - date.today()).days
            
            resultat.append({
                "lot": lot,
                "article": article,
                "jours_restants": jours_restants,
                "urgence": "CRITIQUE" if jours_restants <= 7 else "ELEVEE" if jours_restants <= 15 else "MOYENNE"
            })
        
        return resultat
    
    @staticmethod
    def get_lots_perimes(session: Session) -> List[Dict[str, Any]]:
        """Récupère tous les lots périmés avec quantité restante > 0"""
        
        lots = session.exec(
            select(LotPerissable)
            .where(
                LotPerissable.date_peremption < date.today(),
                LotPerissable.quantite_restante > 0
            )
            .order_by(LotPerissable.date_peremption)
        ).all()
        
        resultat = []
        for lot in lots:
            article = session.get(Article, lot.article_id)
            jours_perime = (date.today() - lot.date_peremption).days
            
            resultat.append({
                "lot": lot,
                "article": article,
                "jours_perime": jours_perime
            })
        
        return resultat
    
    @staticmethod
    def mettre_a_jour_statuts_lots(session: Session) -> Dict[str, int]:
        """
        Met à jour les statuts de tous les lots périssables
        À exécuter quotidiennement (tâche planifiée)
        
        Returns:
            dict: Nombre de lots par nouveau statut
        """
        
        lots = session.exec(select(LotPerissable)).all()
        
        stats = {
            "actifs": 0,
            "alertes": 0,
            "perimes": 0,
            "epuises": 0
        }
        
        for lot in lots:
            article = session.get(Article, lot.article_id)
            
            # Lot épuisé
            if lot.quantite_restante <= 0:
                lot.statut = "EPUISE"
                stats["epuises"] += 1
            # Lot périmé
            elif lot.date_peremption < date.today():
                if lot.statut != "PERIME":
                    lot.statut = "PERIME"
                    logger.warning(f"Lot périmé détecté : {lot.numero_lot} - Article: {article.designation}")
                stats["perimes"] += 1
            # Lot en alerte
            elif (lot.date_peremption - date.today()).days <= article.seuil_alerte_peremption_jours:
                lot.statut = "ALERTE"
                stats["alertes"] += 1
            # Lot actif
            else:
                lot.statut = "ACTIF"
                stats["actifs"] += 1
            
            lot.updated_at = datetime.now()
            session.add(lot)
        
        session.commit()
        
        logger.info(f"Statuts lots mis à jour - Actifs: {stats['actifs']}, Alertes: {stats['alertes']}, Périmés: {stats['perimes']}, Épuisés: {stats['epuises']}")
        return stats
    
    @staticmethod
    def consommer_lot_fifo(
        session: Session,
        article_id: int,
        quantite: Decimal
    ) -> List[Dict[str, Any]]:
        """
        Consomme une quantité d'un article périssable en suivant la règle FIFO
        (First In, First Out - premiers lots à périmer sont utilisés en premier)
        
        Returns:
            List[dict]: Liste des lots consommés avec quantités
        """
        
        # Récupérer les lots actifs triés par date de péremption (FIFO)
        lots = session.exec(
            select(LotPerissable)
            .where(
                LotPerissable.article_id == article_id,
                LotPerissable.quantite_restante > 0,
                LotPerissable.statut.in_(["ACTIF", "ALERTE"])
            )
            .order_by(LotPerissable.date_peremption)
        ).all()
        
        if not lots:
            raise ValueError("Aucun lot disponible pour cet article")
        
        quantite_restante = quantite
        lots_consommes = []
        
        for lot in lots:
            if quantite_restante <= 0:
                break
            
            if lot.quantite_restante >= quantite_restante:
                # Ce lot suffit
                quantite_prise = quantite_restante
                lot.quantite_restante -= quantite_restante
                quantite_restante = Decimal(0)
            else:
                # On prend tout le lot et on continue
                quantite_prise = lot.quantite_restante
                quantite_restante -= lot.quantite_restante
                lot.quantite_restante = Decimal(0)
            
            lot.updated_at = datetime.now()
            session.add(lot)
            
            lots_consommes.append({
                "lot_id": lot.id,
                "numero_lot": lot.numero_lot,
                "quantite_consommee": float(quantite_prise),
                "date_peremption": lot.date_peremption
            })
        
        if quantite_restante > 0:
            raise ValueError(f"Stock insuffisant : {quantite_restante} {session.get(Article, article_id).unite} manquant(s)")
        
        session.commit()
        
        return lots_consommes
    
    # ============================================
    # NOUVEAUTÉ : GESTION AMORTISSEMENT MATÉRIEL
    # ============================================
    
    @staticmethod
    def calculer_amortissement_lineaire(
        valeur_acquisition: Decimal,
        duree_annees: int,
        valeur_residuelle: Decimal = Decimal(0)
    ) -> Decimal:
        """
        Calcule l'amortissement annuel en méthode linéaire
        
        Formule: (Valeur d'acquisition - Valeur résiduelle) / Durée
        """
        return (valeur_acquisition - valeur_residuelle) / Decimal(duree_annees)
    
    @staticmethod
    def calculer_amortissement_degressif(
        valeur_nette_debut: Decimal,
        taux_degressif: Decimal
    ) -> Decimal:
        """
        Calcule l'amortissement annuel en méthode dégressive
        
        Formule: Valeur nette comptable début * Taux dégressif
        """
        return valeur_nette_debut * (taux_degressif / Decimal(100))
    
    @staticmethod
    def calculer_amortissement_annee(
        session: Session,
        article_id: int,
        annee: int,
        user_id: int
    ) -> Amortissement:
        """
        Calcule l'amortissement d'un matériel pour une année donnée
        """
        
        article = session.get(Article, article_id)
        if not article:
            raise ValueError(f"Article {article_id} introuvable")
        
        if not article.est_amortissable:
            raise ValueError(f"L'article '{article.designation}' n'est pas amortissable")
        
        if not article.date_acquisition or not article.valeur_acquisition or not article.duree_amortissement_annees:
            raise ValueError("Données d'amortissement incomplètes (date acquisition, valeur, durée)")
        
        # Vérifier si l'amortissement existe déjà pour cette année
        existing = session.exec(
            select(Amortissement).where(
                Amortissement.article_id == article_id,
                Amortissement.annee == annee
            )
        ).first()
        
        if existing:
            raise ValueError(f"L'amortissement pour l'année {annee} existe déjà")
        
        # Vérifier que l'année est >= année d'acquisition
        annee_acquisition = article.date_acquisition.year
        if annee < annee_acquisition:
            raise ValueError(f"L'année {annee} est antérieure à l'année d'acquisition ({annee_acquisition})")
        
        # Récupérer l'amortissement de l'année précédente
        amort_precedent = session.exec(
            select(Amortissement)
            .where(
                Amortissement.article_id == article_id,
                Amortissement.annee == annee - 1
            )
        ).first()
        
        if amort_precedent:
            amortissement_cumule_debut = amort_precedent.amortissement_cumule_fin
            
            # Vérifier si déjà totalement amorti
            if amort_precedent.totalement_amorti:
                raise ValueError("Le matériel est déjà totalement amorti")
        else:
            # Première année ou années manquantes
            if annee > annee_acquisition:
                logger.warning(f"Amortissement(s) manquant(s) pour les années précédentes")
            amortissement_cumule_debut = Decimal(0)
        
        # Calculer l'amortissement de l'année
        valeur_residuelle = article.valeur_residuelle or Decimal(0)
        
        if article.methode_amortissement == "LINEAIRE":
            amortissement_annuel = StockService.calculer_amortissement_lineaire(
                article.valeur_acquisition,
                article.duree_amortissement_annees,
                valeur_residuelle
            )
            taux_applique = Decimal(100) / Decimal(article.duree_amortissement_annees)
            base_calcul = article.valeur_acquisition - valeur_residuelle
            
        elif article.methode_amortissement == "DEGRESSIF":
            # Taux dégressif = Taux linéaire * Coefficient (1.25, 1.75 ou 2.25 selon durée)
            if not article.taux_amortissement:
                raise ValueError("Le taux d'amortissement dégressif n'est pas défini")
            
            valeur_nette_debut = article.valeur_acquisition - amortissement_cumule_debut
            amortissement_annuel = StockService.calculer_amortissement_degressif(
                valeur_nette_debut,
                article.taux_amortissement
            )
            taux_applique = article.taux_amortissement
            base_calcul = valeur_nette_debut
            
        else:
            raise ValueError(f"Méthode d'amortissement '{article.methode_amortissement}' non supportée")
        
        # Calculs finaux
        amortissement_cumule_fin = amortissement_cumule_debut + amortissement_annuel
        valeur_nette_comptable = article.valeur_acquisition - amortissement_cumule_fin
        
        # Vérifier si on atteint la valeur résiduelle
        if valeur_nette_comptable <= valeur_residuelle:
            # Ajuster pour ne pas dépasser la valeur résiduelle
            amortissement_annuel = article.valeur_acquisition - amortissement_cumule_debut - valeur_residuelle
            amortissement_cumule_fin = article.valeur_acquisition - valeur_residuelle
            valeur_nette_comptable = valeur_residuelle
            totalement_amorti = True
        else:
            totalement_amorti = False
        
        # Créer l'enregistrement d'amortissement
        amortissement = Amortissement(
            article_id=article_id,
            annee=annee,
            periode=str(annee),
            valeur_brute=article.valeur_acquisition,
            amortissement_cumule_debut=amortissement_cumule_debut,
            amortissement_periode=amortissement_annuel,
            amortissement_cumule_fin=amortissement_cumule_fin,
            valeur_nette_comptable=valeur_nette_comptable,
            taux_applique=taux_applique,
            methode=article.methode_amortissement,
            base_calcul=base_calcul,
            totalement_amorti=totalement_amorti,
            calcule_par_user_id=user_id
        )
        
        session.add(amortissement)
        session.commit()
        session.refresh(amortissement)
        
        logger.info(f"Amortissement calculé pour {article.designation} - Année {annee} - Montant: {amortissement_annuel}")
        return amortissement
    
    @staticmethod
    def get_plan_amortissement(session: Session, article_id: int) -> List[Dict[str, Any]]:
        """
        Génère le plan d'amortissement complet d'un matériel
        (pour toutes les années, calculées ou projetées)
        """
        
        article = session.get(Article, article_id)
        if not article or not article.est_amortissable:
            raise ValueError("Article introuvable ou non amortissable")
        
        if not article.date_acquisition or not article.valeur_acquisition or not article.duree_amortissement_annees:
            raise ValueError("Données d'amortissement incomplètes")
        
        # Récupérer les amortissements déjà calculés
        amortissements_calcules = session.exec(
            select(Amortissement)
            .where(Amortissement.article_id == article_id)
            .order_by(Amortissement.annee)
        ).all()
        
        plan = []
        annee_debut = article.date_acquisition.year
        valeur_residuelle = article.valeur_residuelle or Decimal(0)
        
        # Ajouter les amortissements déjà calculés
        amort_cumule = Decimal(0)
        derniere_annee_calculee = annee_debut - 1
        
        for amort in amortissements_calcules:
            plan.append({
                "annee": amort.annee,
                "valeur_brute": float(amort.valeur_brute),
                "amortissement_periode": float(amort.amortissement_periode),
                "amortissement_cumule": float(amort.amortissement_cumule_fin),
                "valeur_nette_comptable": float(amort.valeur_nette_comptable),
                "statut": amort.statut,
                "calcule": True
            })
            amort_cumule = amort.amortissement_cumule_fin
            derniere_annee_calculee = amort.annee
            
            if amort.totalement_amorti:
                return plan  # Amortissement terminé
        
        # Projeter les années restantes
        for i in range(int(derniere_annee_calculee - annee_debut + 1), article.duree_amortissement_annees):
            annee = annee_debut + i
            
            if article.methode_amortissement == "LINEAIRE":
                amort_annuel = StockService.calculer_amortissement_lineaire(
                    article.valeur_acquisition,
                    article.duree_amortissement_annees,
                    valeur_residuelle
                )
            else:
                valeur_nette = article.valeur_acquisition - amort_cumule
                amort_annuel = StockService.calculer_amortissement_degressif(
                    valeur_nette,
                    article.taux_amortissement or Decimal(0)
                )
            
            amort_cumule += amort_annuel
            vnc = article.valeur_acquisition - amort_cumule
            
            # Ajuster si on atteint la valeur résiduelle
            if vnc < valeur_residuelle:
                amort_annuel = article.valeur_acquisition - (amort_cumule - amort_annuel) - valeur_residuelle
                amort_cumule = article.valeur_acquisition - valeur_residuelle
                vnc = valeur_residuelle
            
            plan.append({
                "annee": annee,
                "valeur_brute": float(article.valeur_acquisition),
                "amortissement_periode": float(amort_annuel),
                "amortissement_cumule": float(amort_cumule),
                "valeur_nette_comptable": float(vnc),
                "statut": "PROJETE",
                "calcule": False
            })
            
            if vnc <= valeur_residuelle:
                break  # Amortissement terminé
        
        return plan
    
    @staticmethod
    def get_materiels_a_amortir(session: Session, annee: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Récupère les matériels amortissables pour lesquels l'amortissement
        n'a pas encore été calculé pour l'année donnée
        """
        
        if annee is None:
            annee = date.today().year
        
        # Récupérer tous les matériels amortissables
        materiels = session.exec(
            select(Article).where(
                Article.est_amortissable == True,
                Article.actif == True,
                Article.date_acquisition.is_not(None)
            )
        ).all()
        
        resultat = []
        
        for materiel in materiels:
            # Vérifier si déjà calculé pour cette année
            amort_existe = session.exec(
                select(Amortissement).where(
                    Amortissement.article_id == materiel.id,
                    Amortissement.annee == annee
                )
            ).first()
            
            if not amort_existe and materiel.date_acquisition.year <= annee:
                # Vérifier si déjà totalement amorti
                dernier_amort = session.exec(
                    select(Amortissement)
                    .where(Amortissement.article_id == materiel.id)
                    .order_by(Amortissement.annee.desc())
                ).first()
                
                if dernier_amort and dernier_amort.totalement_amorti:
                    continue  # Déjà totalement amorti
                
                resultat.append({
                    "article": materiel,
                    "annee": annee,
                    "annees_depuis_acquisition": annee - materiel.date_acquisition.year
                })
        
        return resultat

