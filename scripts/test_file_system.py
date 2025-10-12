"""
Script de test pour vérifier le système de gestion de fichiers
"""
import sys
from pathlib import Path

# Ajouter le dossier parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.path_config import path_config
from app.core.enums import FileType, FileStatus, ProgramType
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def test_directories():
    """Vérifie que tous les dossiers existent"""
    logger.info("\n" + "="*60)
    logger.info("🧪 Test des dossiers de fichiers")
    logger.info("="*60)
    
    directories = {
        "Base uploads": path_config.UPLOADS_DIR,
        "Profiles": path_config.UPLOADS_PROFILES_DIR,
        "Files": path_config.UPLOADS_FILES_DIR,
        "Files RAW": path_config.UPLOADS_FILES_RAW_DIR,
        "Files PROCESSED": path_config.UPLOADS_FILES_PROCESSED_DIR,
        "Files ARCHIVE": path_config.UPLOADS_FILES_ARCHIVE_DIR,
    }
    
    all_ok = True
    for name, directory in directories.items():
        if directory.exists():
            logger.info(f"✅ {name:20} : {directory}")
        else:
            logger.error(f"❌ {name:20} : {directory} (MANQUANT)")
            all_ok = False
    
    if all_ok:
        logger.info("\n✅ Tous les dossiers existent!")
    else:
        logger.error("\n❌ Certains dossiers manquent!")
    
    return all_ok


def test_enums():
    """Vérifie que les énumérations sont bien définies"""
    logger.info("\n" + "="*60)
    logger.info("🧪 Test des énumérations")
    logger.info("="*60)
    
    logger.info("\n📋 Types de fichiers:")
    for file_type in FileType:
        logger.info(f"   • {file_type.value}")
    
    logger.info("\n📊 Statuts de fichiers:")
    for status in FileStatus:
        logger.info(f"   • {status.value}")
    
    logger.info("\n🎯 Types de programmes:")
    for program in ProgramType:
        logger.info(f"   • {program.value}")
    
    logger.info("\n✅ Toutes les énumérations sont définies!")
    return True


def test_models():
    """Vérifie que les modèles sont importables"""
    logger.info("\n" + "="*60)
    logger.info("🧪 Test des modèles")
    logger.info("="*60)
    
    try:
        from app.models.file import File
        logger.info("✅ Modèle File importé")
        
        # Vérifier les attributs
        attributes = [
            'id', 'original_filename', 'stored_filename', 'file_path',
            'file_type', 'program', 'period', 'title', 'status',
            'rows_processed', 'rows_failed', 'uploaded_by'
        ]
        
        logger.info("\n📝 Attributs du modèle File:")
        for attr in attributes:
            if hasattr(File, attr):
                logger.info(f"   ✅ {attr}")
            else:
                logger.error(f"   ❌ {attr} (MANQUANT)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'import du modèle: {e}")
        return False


def test_services():
    """Vérifie que les services sont importables"""
    logger.info("\n" + "="*60)
    logger.info("🧪 Test des services")
    logger.info("="*60)
    
    try:
        from app.services.file_service import FileService
        logger.info("✅ FileService importé")
        
        # Vérifier les méthodes
        methods = [
            'save_file', 'get_file_by_id', 'get_all_files',
            'update_file_status', 'delete_file', 'archive_file'
        ]
        
        logger.info("\n📝 Méthodes de FileService:")
        for method in methods:
            if hasattr(FileService, method):
                logger.info(f"   ✅ {method}")
            else:
                logger.error(f"   ❌ {method} (MANQUANT)")
        
        from app.services.excel_processor import ExcelProcessorService
        logger.info("\n✅ ExcelProcessorService importé")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'import des services: {e}")
        return False


def test_api_endpoints():
    """Vérifie que les endpoints sont importables"""
    logger.info("\n" + "="*60)
    logger.info("🧪 Test des endpoints API")
    logger.info("="*60)
    
    try:
        from app.api.v1.endpoints import files
        logger.info("✅ Module files importé")
        
        # Vérifier le router
        if hasattr(files, 'router'):
            logger.info("✅ Router défini")
            logger.info(f"   Prefix: {files.router.prefix}")
            logger.info(f"   Tags: {files.router.tags}")
        else:
            logger.error("❌ Router non trouvé")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'import des endpoints: {e}")
        return False


def test_templates():
    """Vérifie que le template existe"""
    logger.info("\n" + "="*60)
    logger.info("🧪 Test du template")
    logger.info("="*60)
    
    template_path = Path(__file__).parent.parent / "app" / "templates" / "pages" / "fichiers.html"
    
    if template_path.exists():
        logger.info(f"✅ Template fichiers.html existe")
        logger.info(f"   Chemin: {template_path}")
        
        # Vérifier la taille
        size = template_path.stat().st_size
        logger.info(f"   Taille: {size} bytes ({size / 1024:.2f} KB)")
        return True
    else:
        logger.error(f"❌ Template fichiers.html manquant")
        logger.error(f"   Attendu: {template_path}")
        return False


def run_all_tests():
    """Exécute tous les tests"""
    logger.info("\n" + "="*60)
    logger.info("🚀 Système de Gestion de Fichiers - Tests")
    logger.info("="*60)
    
    results = {
        "Dossiers": test_directories(),
        "Énumérations": test_enums(),
        "Modèles": test_models(),
        "Services": test_services(),
        "API Endpoints": test_api_endpoints(),
        "Templates": test_templates(),
    }
    
    logger.info("\n" + "="*60)
    logger.info("📊 RÉSULTATS")
    logger.info("="*60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name:20} : {status}")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    
    logger.info("="*60)
    logger.info(f"Total: {passed}/{total} tests réussis")
    
    if passed == total:
        logger.info("✅ TOUS LES TESTS SONT PASSÉS!")
        logger.info("🎉 Le système de gestion de fichiers est prêt!")
    else:
        logger.error("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        logger.error("⚠️  Corrigez les erreurs avant de continuer")
    
    logger.info("="*60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

