"""
Service de traitement des fichiers Excel
Chaque type de fichier a son propre traitement
"""

from datetime import datetime
from typing import Any

import pandas as pd

from app.core.enums import FileType
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ExcelProcessorService:
    """
    Service pour traiter les fichiers Excel
    Chaque type de fichier a sa propre méthode de traitement
    """

    @classmethod
    def process_file(
        cls, file_path: str, file_type: str, metadata: dict
    ) -> tuple[bool, int, int, str | None, list[dict]]:
        """
        Point d'entrée principal pour traiter un fichier

        Args:
            file_path: Chemin du fichier à traiter
            file_type: Type du fichier (budget, depenses, etc.)
            metadata: Métadonnées du fichier

        Returns:
            Tuple: (success, rows_processed, rows_failed, error_message, processed_data)
        """
        try:
            logger.info(f"📊 Début du traitement du fichier: {file_path} (type: {file_type})")

            # Lire le fichier Excel
            df = pd.read_excel(file_path, engine="openpyxl")
            logger.info(f"📄 Fichier lu: {len(df)} lignes, {len(df.columns)} colonnes")

            # Dispatcher selon le type de fichier
            if file_type == FileType.BUDGET:
                result = cls._process_budget(df, metadata)
            elif file_type == FileType.DEPENSES:
                result = cls._process_depenses(df, metadata)
            elif file_type == FileType.REVENUS:
                result = cls._process_revenus(df, metadata)
            elif file_type == FileType.PERSONNEL:
                result = cls._process_personnel(df, metadata)
            elif file_type == FileType.RAPPORT_ACTIVITE:
                result = cls._process_rapport_activite(df, metadata)
            elif file_type == FileType.BENEFICIAIRES:
                result = cls._process_beneficiaires(df, metadata)
            elif file_type == FileType.INDICATEURS:
                result = cls._process_indicateurs(df, metadata)
            else:
                result = cls._process_generic(df, metadata)

            success, rows_processed, rows_failed, error_msg, processed_data = result

            if success:
                logger.info(f"✅ Traitement réussi: {rows_processed} lignes traitées, {rows_failed} échecs")
            else:
                logger.error(f"❌ Traitement échoué: {error_msg}")

            return result

        except Exception as e:
            error_msg = f"Erreur lors du traitement: {e!s}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return False, 0, 0, error_msg, []

    @classmethod
    def _process_budget(cls, df: pd.DataFrame, metadata: dict) -> tuple[bool, int, int, str | None, list[dict]]:
        """
        Traitement spécifique pour les fichiers de type BUDGET

        Structure attendue (à adapter selon vos besoins):
        - Colonne A: Ligne budgétaire / Poste
        - Colonne B: Montant prévu
        - Colonne C: Montant réalisé
        - Colonne D: Écart
        - Colonne E: Commentaire
        """
        logger.info("💰 Traitement d'un fichier BUDGET")

        try:
            processed_data = []
            rows_failed = 0

            # Nettoyer les noms de colonnes
            df.columns = df.columns.str.strip()

            # Vérifier les colonnes minimales requises
            # Note: Adapter selon votre structure réelle
            required_columns = ["Ligne budgétaire", "Montant prévu"]
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                # Si les colonnes ne correspondent pas, utiliser les indices
                logger.warning(f"⚠️ Colonnes manquantes: {missing_columns}. Utilisation des indices.")
                df.columns = [f"Col_{i}" for i in range(len(df.columns))]

            # Traiter chaque ligne
            for idx, row in df.iterrows():
                try:
                    # Extraire les données (à adapter selon votre structure)
                    record = {
                        "row_index": idx,
                        "ligne_budgetaire": str(row.iloc[0]) if len(row) > 0 else "",
                        "montant_prevu": float(row.iloc[1]) if len(row) > 1 and pd.notna(row.iloc[1]) else 0.0,
                        "montant_realise": float(row.iloc[2]) if len(row) > 2 and pd.notna(row.iloc[2]) else 0.0,
                        "ecart": float(row.iloc[3]) if len(row) > 3 and pd.notna(row.iloc[3]) else 0.0,
                        "commentaire": str(row.iloc[4]) if len(row) > 4 and pd.notna(row.iloc[4]) else "",
                        "period": metadata.get("period"),
                        "program": metadata.get("program"),
                        "processed_at": datetime.now().isoformat(),
                    }

                    # Validation basique
                    if record["ligne_budgetaire"] and record["ligne_budgetaire"] != "nan":
                        processed_data.append(record)
                    else:
                        rows_failed += 1

                except Exception as e:
                    logger.warning(f"⚠️ Erreur ligne {idx}: {e}")
                    rows_failed += 1

            rows_processed = len(processed_data)
            logger.info(f"✅ Budget traité: {rows_processed} lignes OK, {rows_failed} échecs")

            # TODO: Insérer dans la base de données
            # Vous créerez une table spécifique pour les données budgétaires

            return True, rows_processed, rows_failed, None, processed_data

        except Exception as e:
            error_msg = f"Erreur traitement budget: {e!s}"
            logger.error(f"❌ {error_msg}")
            return False, 0, 0, error_msg, []

    @classmethod
    def _process_depenses(cls, df: pd.DataFrame, metadata: dict) -> tuple[bool, int, int, str | None, list[dict]]:
        """
        Traitement spécifique pour les fichiers de type DÉPENSES

        Structure attendue:
        - Date
        - Bénéficiaire
        - Description
        - Catégorie
        - Montant
        - Mode de paiement
        """
        logger.info("💸 Traitement d'un fichier DÉPENSES")

        try:
            processed_data = []
            rows_failed = 0

            df.columns = df.columns.str.strip()

            for idx, row in df.iterrows():
                try:
                    record = {
                        "row_index": idx,
                        "date": str(row.iloc[0]) if len(row) > 0 else "",
                        "beneficiaire": str(row.iloc[1]) if len(row) > 1 else "",
                        "description": str(row.iloc[2]) if len(row) > 2 else "",
                        "categorie": str(row.iloc[3]) if len(row) > 3 else "",
                        "montant": float(row.iloc[4]) if len(row) > 4 and pd.notna(row.iloc[4]) else 0.0,
                        "mode_paiement": str(row.iloc[5]) if len(row) > 5 else "",
                        "period": metadata.get("period"),
                        "program": metadata.get("program"),
                        "processed_at": datetime.now().isoformat(),
                    }

                    if record["beneficiaire"] and record["beneficiaire"] != "nan":
                        processed_data.append(record)
                    else:
                        rows_failed += 1

                except Exception as e:
                    logger.warning(f"⚠️ Erreur ligne {idx}: {e}")
                    rows_failed += 1

            rows_processed = len(processed_data)
            logger.info(f"✅ Dépenses traitées: {rows_processed} lignes OK, {rows_failed} échecs")

            return True, rows_processed, rows_failed, None, processed_data

        except Exception as e:
            error_msg = f"Erreur traitement dépenses: {e!s}"
            logger.error(f"❌ {error_msg}")
            return False, 0, 0, error_msg, []

    @classmethod
    def _process_revenus(cls, df: pd.DataFrame, metadata: dict) -> tuple[bool, int, int, str | None, list[dict]]:
        """Traitement spécifique pour les REVENUS"""
        logger.info("💵 Traitement d'un fichier REVENUS")
        # TODO: Implémenter selon votre structure
        return cls._process_generic(df, metadata)

    @classmethod
    def _process_personnel(cls, df: pd.DataFrame, metadata: dict) -> tuple[bool, int, int, str | None, list[dict]]:
        """Traitement spécifique pour les données PERSONNEL"""
        logger.info("👥 Traitement d'un fichier PERSONNEL")
        # TODO: Implémenter selon votre structure
        return cls._process_generic(df, metadata)

    @classmethod
    def _process_rapport_activite(
        cls, df: pd.DataFrame, metadata: dict
    ) -> tuple[bool, int, int, str | None, list[dict]]:
        """Traitement spécifique pour les RAPPORTS D'ACTIVITÉ"""
        logger.info("📋 Traitement d'un fichier RAPPORT D'ACTIVITÉ")
        # TODO: Implémenter selon votre structure
        return cls._process_generic(df, metadata)

    @classmethod
    def _process_beneficiaires(cls, df: pd.DataFrame, metadata: dict) -> tuple[bool, int, int, str | None, list[dict]]:
        """Traitement spécifique pour les BÉNÉFICIAIRES"""
        logger.info("👤 Traitement d'un fichier BÉNÉFICIAIRES")
        # TODO: Implémenter selon votre structure
        return cls._process_generic(df, metadata)

    @classmethod
    def _process_indicateurs(cls, df: pd.DataFrame, metadata: dict) -> tuple[bool, int, int, str | None, list[dict]]:
        """Traitement spécifique pour les INDICATEURS"""
        logger.info("📊 Traitement d'un fichier INDICATEURS")
        # TODO: Implémenter selon votre structure
        return cls._process_generic(df, metadata)

    @classmethod
    def _process_generic(cls, df: pd.DataFrame, metadata: dict) -> tuple[bool, int, int, str | None, list[dict]]:
        """
        Traitement générique pour les fichiers non spécifiques
        Lit simplement toutes les données
        """
        logger.info("📄 Traitement générique du fichier")

        try:
            processed_data = []
            rows_failed = 0

            df.columns = df.columns.str.strip()

            for idx, row in df.iterrows():
                try:
                    record = {
                        "row_index": idx,
                        "data": row.to_dict(),
                        "period": metadata.get("period"),
                        "program": metadata.get("program"),
                        "processed_at": datetime.now().isoformat(),
                    }
                    processed_data.append(record)

                except Exception as e:
                    logger.warning(f"⚠️ Erreur ligne {idx}: {e}")
                    rows_failed += 1

            rows_processed = len(processed_data)
            logger.info(f"✅ Traitement générique: {rows_processed} lignes OK, {rows_failed} échecs")

            return True, rows_processed, rows_failed, None, processed_data

        except Exception as e:
            error_msg = f"Erreur traitement générique: {e!s}"
            logger.error(f"❌ {error_msg}")
            return False, 0, 0, error_msg, []

    @classmethod
    def validate_file_structure(cls, file_path: str, file_type: str) -> tuple[bool, str | None]:
        """
        Valide la structure d'un fichier avant traitement

        Returns:
            Tuple: (is_valid, error_message)
        """
        try:
            df = pd.read_excel(file_path, engine="openpyxl")

            # Vérifications basiques
            if df.empty:
                return False, "Le fichier est vide"

            if len(df.columns) == 0:
                return False, "Aucune colonne trouvée"

            # Validations spécifiques par type
            # TODO: Ajouter des validations spécifiques selon le type

            return True, None

        except Exception as e:
            return False, f"Erreur de validation: {e!s}"

    @classmethod
    def get_file_preview(cls, file_path: str, nrows: int = 10) -> dict[str, Any]:
        """
        Récupère un aperçu du fichier Excel

        Returns:
            Dict avec colonnes, premières lignes, et statistiques
        """
        try:
            df = pd.read_excel(file_path, nrows=nrows, engine="openpyxl")

            preview = {
                "columns": df.columns.tolist(),
                "rows": df.to_dict("records"),
                "total_columns": len(df.columns),
                "preview_rows": len(df),
            }

            return preview

        except Exception as e:
            logger.error(f"❌ Erreur lors de la prévisualisation: {e}")
            return {"error": str(e)}
