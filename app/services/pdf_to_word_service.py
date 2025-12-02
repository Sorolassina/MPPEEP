"""
Service de conversion PDF vers Word utilisant Adobe PDF Services SDK.

Ce service permet de convertir un fichier PDF en document Word (.docx)
pour permettre aux utilisateurs de modifier le rapport généré.

Utilise le SDK Adobe PDF Services pour la conversion.
"""

import logging
import os
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

logger = logging.getLogger(__name__)


class PDFToWordService:
    """
    Service pour convertir un PDF en document Word (.docx).
    
    Utilise Adobe PDF Services SDK pour effectuer la conversion.
    Les identifiants sont récupérés depuis les variables d'environnement
    ou depuis le fichier de credentials.
    """
    
    @staticmethod
    def _load_credentials() -> tuple[str | None, str | None]:
        """
        Charge les credentials Adobe PDF Services.
        
        Cherche d'abord dans les variables d'environnement, puis dans le fichier
        de credentials fourni avec le SDK.
        
        Returns:
            Tuple (client_id, client_secret) ou (None, None) si non trouvé
        """
        # D'abord, essayer les variables d'environnement
        client_id = os.getenv('PDF_SERVICES_CLIENT_ID')
        client_secret = os.getenv('PDF_SERVICES_CLIENT_SECRET')
        
        if client_id and client_secret:
            logger.info("✅ Credentials Adobe PDF Services trouvés dans les variables d'environnement")
            return client_id, client_secret
        
        # Sinon, essayer de charger depuis le fichier de credentials
        try:
            import json
            credentials_path = Path(__file__).parent.parent / "PDFServicesSDK-PythonSamples" / "pdfservices-api-credentials.json"
            
            if credentials_path.exists():
                with open(credentials_path, 'r') as f:
                    credentials = json.load(f)
                    client_creds = credentials.get("client_credentials", {})
                    client_id = client_creds.get("client_id")
                    client_secret = client_creds.get("client_secret")
                    
                    if client_id and client_secret:
                        logger.info("✅ Credentials Adobe PDF Services chargés depuis le fichier")
                        return client_id, client_secret
        except Exception as e:
            logger.warning(f"⚠️ Impossible de charger les credentials depuis le fichier: {e}")
        
        logger.error("❌ Aucun credential Adobe PDF Services trouvé")
        return None, None
    
    @staticmethod
    def convert_pdf_to_word(pdf_buffer: BytesIO, use_ocr: bool = False) -> BytesIO:
        """
        Convertit un PDF en document Word (.docx).
        
        Args:
            pdf_buffer: Buffer BytesIO contenant le PDF à convertir
            use_ocr: Si True, applique OCR sur les images pour extraire le texte
        
        Returns:
            BytesIO contenant le document Word (.docx)
        
        Raises:
            ValueError: Si les credentials ne sont pas disponibles
            Exception: Si la conversion échoue
        """
        # Importer les modules Adobe en premier (peut échouer si le SDK n'est pas installé)
        try:
            from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials
            from adobe.pdfservices.operation.exception.exceptions import ServiceApiException, ServiceUsageException, SdkException
            from adobe.pdfservices.operation.io.cloud_asset import CloudAsset
            from adobe.pdfservices.operation.io.stream_asset import StreamAsset
            from adobe.pdfservices.operation.pdf_services import PDFServices
            from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
            from adobe.pdfservices.operation.pdfjobs.jobs.export_pdf_job import ExportPDFJob
            from adobe.pdfservices.operation.pdfjobs.params.export_pdf.export_pdf_params import ExportPDFParams
            from adobe.pdfservices.operation.pdfjobs.params.export_pdf.export_pdf_target_format import ExportPDFTargetFormat
            from adobe.pdfservices.operation.pdfjobs.params.export_pdf.export_ocr_locale import ExportOCRLocale
            from adobe.pdfservices.operation.pdfjobs.result.export_pdf_result import ExportPDFResult
        except ImportError as e:
            raise ImportError(
                f"Le SDK Adobe PDF Services n'est pas installé. "
                f"Installez-le avec: pip install pdfservices-sdk. "
                f"Erreur: {e}"
            )
        
        try:
            # Charger les credentials
            client_id, client_secret = PDFToWordService._load_credentials()
            
            if not client_id or not client_secret:
                raise ValueError(
                    "Les credentials Adobe PDF Services ne sont pas configurés. "
                    "Veuillez définir PDF_SERVICES_CLIENT_ID et PDF_SERVICES_CLIENT_SECRET "
                    "dans les variables d'environnement ou configurer le fichier de credentials."
                )
            
            logger.info("🔄 Début de la conversion PDF → Word")
            
            # Lire le contenu du PDF
            pdf_buffer.seek(0)
            pdf_content = pdf_buffer.read()
            
            # Créer les credentials
            credentials = ServicePrincipalCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
            
            # Créer une instance de PDF Services
            pdf_services = PDFServices(credentials=credentials)
            
            # Télécharger le PDF sur Adobe Cloud
            logger.info("📤 Upload du PDF sur Adobe Cloud...")
            input_asset = pdf_services.upload(
                input_stream=pdf_content,
                mime_type=PDFServicesMediaType.PDF
            )
            logger.info("✅ PDF téléchargé sur Adobe Cloud")
            
            # Créer les paramètres d'exportation
            if use_ocr:
                # Utiliser OCR pour extraire le texte des images
                export_pdf_params = ExportPDFParams(
                    target_format=ExportPDFTargetFormat.DOCX,
                    ocr_lang=ExportOCRLocale.FR_FR  # Français par défaut
                )
                logger.info("📝 OCR activé pour l'extraction de texte (FR_FR)")
            else:
                export_pdf_params = ExportPDFParams(
                    target_format=ExportPDFTargetFormat.DOCX
                )
            
            # Créer le job d'exportation
            export_pdf_job = ExportPDFJob(
                input_asset=input_asset,
                export_pdf_params=export_pdf_params
            )
            
            # Soumettre le job et attendre le résultat
            logger.info("⏳ Envoi du job de conversion...")
            location = pdf_services.submit(export_pdf_job)
            logger.info("⏳ Attente du résultat de conversion (cela peut prendre quelques secondes)...")
            pdf_services_response = pdf_services.get_job_result(location, ExportPDFResult)
            
            # Récupérer le document Word
            result_asset: CloudAsset = pdf_services_response.get_result().get_asset()
            stream_asset: StreamAsset = pdf_services.get_content(result_asset)
            
            # Créer un buffer pour le document Word
            logger.info("📥 Téléchargement du document Word...")
            word_buffer = BytesIO()
            # get_input_stream() retourne directement du contenu qui peut être écrit (comme dans l'exemple Adobe)
            input_stream = stream_asset.get_input_stream()
            if isinstance(input_stream, bytes):
                word_buffer.write(input_stream)
            elif hasattr(input_stream, 'read'):
                word_buffer.write(input_stream.read())
            else:
                # Fallback: convertir en bytes si possible
                word_buffer.write(bytes(input_stream))
            word_buffer.seek(0)
            
            logger.info("✅ Conversion PDF → Word terminée avec succès")
            
            return word_buffer
            
        except (ServiceApiException, ServiceUsageException, SdkException) as e:
            error_msg = f"Erreur Adobe PDF Services lors de la conversion: {e}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = f"Erreur lors de la conversion PDF → Word: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            raise Exception(error_msg) from e
    
    @staticmethod
    def convert_pdf_file_to_word(pdf_path: str | Path, output_path: str | Path | None = None, use_ocr: bool = False) -> BytesIO:
        """
        Convertit un fichier PDF en document Word.
        
        Args:
            pdf_path: Chemin vers le fichier PDF à convertir
            output_path: Chemin de sortie pour le fichier Word (optionnel)
            use_ocr: Si True, applique OCR sur les images
        
        Returns:
            BytesIO contenant le document Word
        
        Raises:
            FileNotFoundError: Si le fichier PDF n'existe pas
            Exception: Si la conversion échoue
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"Le fichier PDF n'existe pas: {pdf_path}")
        
        # Lire le PDF
        with open(pdf_path, 'rb') as f:
            pdf_buffer = BytesIO(f.read())
        
        # Convertir en Word
        word_buffer = PDFToWordService.convert_pdf_to_word(pdf_buffer, use_ocr=use_ocr)
        
        # Sauvegarder si un chemin de sortie est fourni
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                word_buffer.seek(0)
                f.write(word_buffer.read())
            logger.info(f"✅ Document Word sauvegardé: {output_path}")
        
        word_buffer.seek(0)
        return word_buffer

