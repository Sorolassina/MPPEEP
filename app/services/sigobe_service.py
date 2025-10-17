# app/services/sigobe_service.py
"""
Service de traitement des données SIGOBE (Système d'Information de Gestion et d'Observation Budgétaire)
Gère l'import, la validation et le parsing de fichiers Excel SIGOBE
Version simplifiée pour template structuré
"""
from typing import Optional, Dict, Tuple
from decimal import Decimal
from datetime import datetime
from io import BytesIO
import pandas as pd
import re
import unicodedata

from sqlmodel import Session, select, func
from fastapi import HTTPException

from app.models.budget import SigobeChargement, SigobeExecution, SigobeKpi
from app.models.user import User
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class SigobeService:
    """Service pour gérer les données SIGOBE"""
    
    @staticmethod
    def parse_fichier_excel(
        excel_file: BytesIO, 
        annee: int, 
        trimestre: Optional[int]
    ) -> Tuple[pd.DataFrame, dict, list]:
        """
        Parse un fichier SIGOBE depuis notre template structuré
        
        Args:
            excel_file: Fichier Excel en mémoire
            annee: Année budgétaire
            trimestre: Trimestre (optionnel)
        
        Returns:
            Tuple (DataFrame nettoyé, Métadonnées, Liste des colonnes hiérarchiques)
        
        Raises:
            HTTPException si le fichier n'est pas conforme
        """
        try:
            # --- A. Charger le fichier Excel ---
            # header=0 signifie que la première ligne contient les en-têtes
            df = pd.read_excel(excel_file, sheet_name=0, header=0)
            
            logger.info(f"📊 [A] Fichier chargé : {len(df)} lignes × {len(df.columns)} colonnes")
            logger.info(f"📋 [A] Colonnes détectées : {list(df.columns)}")
            
            # --- B. Métadonnées ---
            Metadatafile = {
                'annee': str(annee),
                'trimestre': str(trimestre) if trimestre else None
            }
            
            logger.info(f"📋 [B] Métadonnées : {Metadatafile}")
            
            # --- C. Suppression lignes vides ---
            df_clean = df.dropna(how='all').reset_index(drop=True)
            
            logger.info(f"🧹 [C] Après suppression lignes vides : {len(df_clean)} lignes")
            
            # --- D. Standardisation des noms de colonnes ---
            # Mapper les noms du template vers nos noms standardisés
            rename_map = {
                'PROGRAMMES': 'Programmes',
                'ACTIONS': 'Actions',
                'RPROG': 'Rprog',
                'TYPE DEPENSE': 'Type_depense',
                'ACTIVITES': 'Activites',
                'TACHES': 'Taches',
                'BUDGET VOTE': 'Budget_Vote',
                'BUDGET ACTUEL': 'Budget_Actuel',
                'ENGAGEMENTS EMIS': 'Engagements_Emis',
                'DISPONIBLE ENG': 'Disponible_Eng',
                'MANDATS EMIS': 'Mandats_Emis',
                'MANDATS VISE CF': 'Mandats_Vise_CF',
                'MANDATS PEC': 'Mandats_Pec'
            }
            
            df_renamed = df_clean.rename(columns=rename_map)
            logger.info(f"🔤 [D] Colonnes renommées : {list(df_renamed.columns)}")
            
            # Colonnes hiérarchiques
            ColsToKeep = ['Programmes', 'Actions', 'Rprog', 'Type_depense', 'Activites', 'Taches']
            
            # --- E. Nettoyage codes dans colonnes hiérarchiques ---
            # Séparer les codes des libellés (ex: "Programme 001 - Pilotage" → "Pilotage")
            for col in ColsToKeep:
                if col in df_renamed.columns:
                    df_renamed[col] = df_renamed[col].apply(
                        lambda x: SigobeService._split_code_libelle(x)[1] if pd.notna(x) else ''
                    )
            
            logger.info(f"✂️ [E] Codes supprimés des colonnes hiérarchiques")
            
            # --- F. Conversion des colonnes financières en numérique ---
            financial_cols = ['Budget_Vote', 'Budget_Actuel', 'Engagements_Emis', 
                            'Disponible_Eng', 'Mandats_Emis', 'Mandats_Vise_CF', 'Mandats_Pec']
            
            for col in financial_cols:
                if col in df_renamed.columns:
                    df_renamed[col] = pd.to_numeric(df_renamed[col], errors='coerce').fillna(0)
            
            logger.info(f"💰 [F] Colonnes financières converties en numérique")
            
            # --- G. Filtrage : garder uniquement les lignes les plus détaillées (Taches) ---
            # On ne garde que les lignes qui ont une valeur dans la colonne TACHES
            # Cela élimine automatiquement les lignes de totaux et les niveaux supérieurs
            if 'Taches' in df_renamed.columns:
                # Garder uniquement les lignes avec Taches non vide
                mask_taches = df_renamed['Taches'].notna() & (df_renamed['Taches'].astype(str).str.strip() != '')
                df_final = df_renamed[mask_taches].reset_index(drop=True)
                logger.info(f"🎯 [G] Filtrage sur Taches : {len(df_final)} lignes conservées (sur {len(df_renamed)} total)")
            else:
                # Si pas de colonne Taches, garder toutes les lignes avec au moins une info
                mask = df_renamed[ColsToKeep].notna().any(axis=1)
                df_final = df_renamed[mask].reset_index(drop=True)
                logger.info(f"🎯 [G] Filtrage général : {len(df_final)} lignes conservées")
            
            # --- H. Validation finale ---
            if len(df_final) == 0:
                raise HTTPException(400, "❌ Aucune donnée valide trouvée dans le fichier")
            
            # Vérifier qu'on a au moins quelques colonnes essentielles
            required_cols = ['Programmes', 'Budget_Vote']
            missing_cols = [col for col in required_cols if col not in df_final.columns]
            if missing_cols:
                raise HTTPException(
                    400, 
                    f"❌ Colonnes manquantes : {', '.join(missing_cols)}\n\n"
                    f"📥 Colonnes trouvées : {', '.join(df_final.columns)}\n\n"
                    f"💡 Utilisez le modèle Excel fourni pour garantir le bon format"
                )
            
            logger.info(f"✅ [H] Validation réussie - {len(df_final)} lignes conformes")
            
            return df_final, Metadatafile, ColsToKeep
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erreur parsing SIGOBE : {e}")
            raise HTTPException(500, f"Erreur lors de l'analyse du fichier : {str(e)}")
    
    
    @staticmethod
    def _split_code_libelle(text: str) -> tuple:
        """
        Sépare code et libellé dans une chaîne
        
        Formats supportés:
        - "Programme 001 - Pilotage" → ("001", "Pilotage")
        - "Action 1.1 - Coordination" → ("1.1", "Coordination")
        - "2208401 Pilotage" → ("2208401", "Pilotage")
        - "Pilotage" → ("", "Pilotage")
        
        Returns:
            Tuple (code, libellé)
        """
        if not text or pd.isna(text):
            return ('', '')
        
        text = str(text).strip()
        
        # Pattern 1: "Type XXX - Libellé" (ex: "Programme 001 - Pilotage")
        match = re.match(r'^[A-Za-zé\s]+\s+([0-9\.]+)\s*-\s*(.+)$', text)
        if match:
            return (match.group(1), match.group(2).strip())
        
        # Pattern 2: "Code numérique Libellé" (ex: "2208401 Pilotage")
        match = re.match(r'^([0-9]+)\s+(.+)$', text)
        if match:
            return (match.group(1), match.group(2).strip())
        
        # Sinon retourner tout comme libellé
        return ('', text)
    
    
    @staticmethod
    def creer_chargement(
        nom_fichier: str,
        annee: int,
        trimestre: Optional[int],
        df: pd.DataFrame,
        metadata: dict,
        session: Session,
        current_user: User
    ) -> SigobeChargement:
        """
        Créer un enregistrement de chargement SIGOBE
        
        Args:
            nom_fichier: Nom du fichier source
            annee: Année budgétaire
            trimestre: Trimestre (optionnel)
            df: DataFrame avec les données parsées
            metadata: Métadonnées extraites
            session: Session DB
            current_user: Utilisateur effectuant l'import
        
        Returns:
            SigobeChargement créé
        """
        # Compter les programmes uniques
        nb_programmes = 0
        if 'Programmes' in df.columns:
            programmes_uniques = df['Programmes'].dropna()
            programmes_uniques = programmes_uniques[programmes_uniques.astype(str).str.strip() != '']
            nb_programmes = int(programmes_uniques.nunique())
        
        # Générer période
        if trimestre:
            periode_libelle = f"T{trimestre} {annee}"
        else:
            periode_libelle = f"Annuel {annee}"
        
        chargement = SigobeChargement(
            nom_fichier=nom_fichier,
            annee=annee,
            trimestre=trimestre,
            periode_libelle=periode_libelle,
            date_chargement=datetime.now(),
            nb_lignes_importees=len(df),
            nb_programmes=nb_programmes,
            statut="Terminé",
            charge_par_user_id=current_user.id
        )
        
        session.add(chargement)
        session.commit()
        session.refresh(chargement)
        
        logger.info(f"✅ Chargement SIGOBE créé : ID={chargement.id}, {len(df)} lignes, {nb_programmes} programmes")
        
        return chargement
    
    
    @staticmethod
    def creer_executions(
        df: pd.DataFrame,
        cols_to_keep: list,
        chargement_id: int,
        session: Session
    ) -> int:
        """
        Créer les enregistrements d'exécution SIGOBE depuis le DataFrame
        
        Returns:
            Nombre d'enregistrements créés
        """
        count = 0
        
        for idx, row in df.iterrows():
            try:
                # Extraire valeurs hiérarchiques
                def get_str(col_name):
                    if col_name in df.columns:
                        val = row[col_name]
                        if pd.notna(val) and str(val).strip() != '':
                            return str(val).strip()
                    return None
                
                # Extraire montants financiers
                def get_decimal(col_name):
                    if col_name in df.columns:
                        val = row[col_name]
                        if pd.notna(val):
                            try:
                                return Decimal(str(val))
                            except:
                                return Decimal("0")
                    return Decimal("0")
                
                execution = SigobeExecution(
                    chargement_id=chargement_id,
                    programmes=get_str('Programmes'),
                    actions=get_str('Actions'),
                    rprog=get_str('Rprog'),
                    type_depense=get_str('Type_depense'),
                    activites=get_str('Activites'),
                    taches=get_str('Taches'),
                    budget_vote=get_decimal('Budget_Vote'),
                    budget_actuel=get_decimal('Budget_Actuel'),
                    engagements_emis=get_decimal('Engagements_Emis'),
                    disponible_eng=get_decimal('Disponible_Eng'),
                    mandats_emis=get_decimal('Mandats_Emis'),
                    mandats_vise_cf=get_decimal('Mandats_Vise_CF'),
                    mandats_pec=get_decimal('Mandats_Pec')
                )
                
                session.add(execution)
                count += 1
                
            except Exception as e:
                logger.error(f"❌ Erreur ligne {idx+1}: {e}")
        
        session.commit()
        
        logger.info(f"✅ {count} enregistrements d'exécution créés")
        
        return count
    
    
    @staticmethod
    def calculer_kpis(chargement_id: int, session: Session):
        """
        Calculer les KPIs globaux et par dimension pour un chargement SIGOBE
        
        Args:
            chargement_id: ID du chargement
            session: Session DB
        """
        # Récupérer toutes les exécutions
        executions = session.exec(
            select(SigobeExecution)
            .where(SigobeExecution.chargement_id == chargement_id)
        ).all()
        
        if not executions:
            logger.warning(f"⚠️ Aucune exécution pour chargement {chargement_id}")
            return
        
        # Récupérer le chargement pour obtenir l'année
        chargement = session.get(SigobeChargement, chargement_id)
        if not chargement:
            logger.error(f"❌ Chargement {chargement_id} non trouvé")
            return
        
        # KPI Global
        budget_vote_total = sum(e.budget_vote or Decimal("0") for e in executions)
        budget_actuel_total = sum(e.budget_actuel or Decimal("0") for e in executions)
        engagements_total = sum(e.engagements_emis or Decimal("0") for e in executions)
        mandats_total = sum(e.mandats_emis or Decimal("0") for e in executions)
        
        taux_engagement = (float(engagements_total) / float(budget_actuel_total) * 100) if budget_actuel_total > 0 else 0
        taux_mandatement = (float(mandats_total) / float(budget_actuel_total) * 100) if budget_actuel_total > 0 else 0
        
        kpi_global = SigobeKpi(
            chargement_id=chargement_id,
            annee=chargement.annee,
            trimestre=chargement.trimestre,
            dimension="global",
            dimension_valeur="GLOBAL",
            budget_vote_total=budget_vote_total,
            budget_actuel_total=budget_actuel_total,
            engagements_total=engagements_total,
            mandats_total=mandats_total,
            taux_engagement=Decimal(str(taux_engagement)),
            taux_mandatement=Decimal(str(taux_mandatement))
        )
        
        session.add(kpi_global)
        session.commit()
        
        logger.info(f"✅ KPI global créé : Engagement={taux_engagement:.2f}%, Mandatement={taux_mandatement:.2f}%")
