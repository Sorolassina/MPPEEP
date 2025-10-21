"""
Planificateur de tâches automatiques
Exécute des tâches périodiques en arrière-plan
"""
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session, select

from app.core.logging_config import get_logger
from app.db.session import engine
from app.models.session import UserSession
from app.models.file import File
from app.core.enums import FileStatus
from app.core.path_config import path_config
from pathlib import Path
from datetime import timedelta

logger = get_logger("scheduler")

# Instance globale du scheduler
scheduler = None


def cleanup_expired_sessions():
    """Nettoie les sessions expirées"""
    try:
        logger.info("🧹 [CRON] Nettoyage des sessions expirées...")
        
        with Session(engine) as session:
            statement = select(UserSession).where(UserSession.is_active == True)
            active_sessions = session.exec(statement).all()
            
            expired_count = 0
            for user_session in active_sessions:
                if user_session.is_expired():
                    user_session.deactivate()
                    expired_count += 1
            
            if expired_count > 0:
                session.commit()
                logger.info(f"✅ [CRON] {expired_count} session(s) expirée(s) nettoyée(s)")
            else:
                logger.debug("✅ [CRON] Aucune session expirée")
        
        return expired_count
    except Exception as e:
        logger.error(f"❌ [CRON] Erreur nettoyage sessions: {e}", exc_info=True)
        return 0


def cleanup_old_files():
    """Nettoie les fichiers temporaires > 24h"""
    try:
        logger.info("🧹 [CRON] Nettoyage des fichiers temporaires...")
        
        cutoff_time = datetime.now() - timedelta(hours=24)
        deleted_count = 0
        total_size = 0
        
        # Nettoyer les fichiers RAW
        raw_dir = path_config.UPLOADS_FILES_RAW_DIR
        if raw_dir.exists():
            for file_path in raw_dir.glob("*.xls*"):
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        try:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            deleted_count += 1
                            total_size += file_size
                            logger.debug(f"   Supprimé: {file_path.name}")
                        except Exception as e:
                            logger.error(f"   Erreur suppression {file_path.name}: {e}")
        
        # Nettoyer les fichiers SIGOBE
        sigobe_dir = path_config.UPLOADS_DIR / "sigobe"
        if sigobe_dir.exists():
            for year_dir in sigobe_dir.iterdir():
                if year_dir.is_dir():
                    for file_path in year_dir.glob("*.xls*"):
                        if file_path.is_file():
                            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                            if file_time < cutoff_time:
                                try:
                                    file_size = file_path.stat().st_size
                                    file_path.unlink()
                                    deleted_count += 1
                                    total_size += file_size
                                    logger.debug(f"   Supprimé: {file_path.name}")
                                except Exception as e:
                                    logger.error(f"   Erreur suppression {file_path.name}: {e}")
        
        if deleted_count > 0:
            logger.info(f"✅ [CRON] {deleted_count} fichier(s) supprimé(s) ({total_size / (1024*1024):.2f} MB)")
        else:
            logger.debug("✅ [CRON] Aucun fichier à nettoyer")
        
        return deleted_count
    except Exception as e:
        logger.error(f"❌ [CRON] Erreur nettoyage fichiers: {e}", exc_info=True)
        return 0


def cleanup_error_files():
    """Nettoie les fichiers en erreur > 7 jours"""
    try:
        logger.info("🧹 [CRON] Nettoyage des fichiers en erreur...")
        
        with Session(engine) as session:
            cutoff_date = datetime.now() - timedelta(days=7)
            
            statement = select(File).where(
                File.status == FileStatus.ERROR,
                File.created_at < cutoff_date
            )
            error_files = session.exec(statement).all()
            
            deleted_count = 0
            for file in error_files:
                # Supprimer le fichier physique
                file_path = Path(file.file_path)
                if file_path.exists():
                    try:
                        file_path.unlink()
                    except Exception as e:
                        logger.error(f"   Erreur suppression {file.original_filename}: {e}")
                
                # Supprimer l'enregistrement en base
                session.delete(file)
                deleted_count += 1
            
            if deleted_count > 0:
                session.commit()
                logger.info(f"✅ [CRON] {deleted_count} fichier(s) en erreur nettoyé(s)")
            else:
                logger.debug("✅ [CRON] Aucun fichier en erreur")
            
            return deleted_count
    except Exception as e:
        logger.error(f"❌ [CRON] Erreur nettoyage fichiers erreur: {e}", exc_info=True)
        return 0


def run_daily_cleanup():
    """Exécute toutes les tâches de nettoyage quotidien"""
    logger.info("=" * 70)
    logger.info("🔄 [CRON] NETTOYAGE AUTOMATIQUE QUOTIDIEN - DÉMARRAGE")
    logger.info(f"📅 [CRON] Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)
    
    # Exécuter tous les nettoyages
    sessions = cleanup_expired_sessions()
    files = cleanup_old_files()
    errors = cleanup_error_files()
    
    # Résumé
    total = sessions + files + errors
    logger.info("")
    logger.info("=" * 70)
    logger.info("📊 [CRON] RÉSUMÉ DU NETTOYAGE")
    logger.info("=" * 70)
    logger.info(f"   🔐 Sessions expirées     : {sessions}")
    logger.info(f"   📊 Fichiers temporaires  : {files}")
    logger.info(f"   ❌ Fichiers en erreur    : {errors}")
    logger.info("")
    logger.info(f"   🎯 TOTAL                 : {total} éléments nettoyés")
    logger.info("=" * 70)
    logger.info("✅ [CRON] NETTOYAGE TERMINÉ")
    logger.info("=" * 70)


def start_scheduler():
    """Démarre le planificateur de tâches"""
    global scheduler
    
    if scheduler is not None:
        logger.warning("⚠️  Scheduler déjà démarré")
        return
    
    logger.info("🚀 Démarrage du planificateur de tâches...")
    
    # Créer le scheduler
    scheduler = BackgroundScheduler(timezone="Europe/Paris")
    
    # Ajouter la tâche de nettoyage quotidien (tous les jours à 3h00)
    scheduler.add_job(
        run_daily_cleanup,
        trigger=CronTrigger(hour=3, minute=0),  # Tous les jours à 3h00
        id='daily_cleanup',
        name='Nettoyage quotidien',
        replace_existing=True
    )
    
    # Démarrer le scheduler
    scheduler.start()
    
    logger.info("✅ Planificateur démarré")
    logger.info("   📅 Nettoyage quotidien programmé : 3h00 du matin")
    
    # Afficher les jobs planifiés
    jobs = scheduler.get_jobs()
    for job in jobs:
        logger.info(f"   ⏰ Job: {job.name} - Prochaine exécution: {job.next_run_time}")


def stop_scheduler():
    """Arrête le planificateur de tâches"""
    global scheduler
    
    if scheduler is None:
        return
    
    logger.info("🛑 Arrêt du planificateur de tâches...")
    scheduler.shutdown()
    scheduler = None
    logger.info("✅ Planificateur arrêté")


def get_scheduler_status():
    """Retourne l'état du scheduler"""
    global scheduler
    
    if scheduler is None:
        return {"running": False, "jobs": []}
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None
        })
    
    return {
        "running": True,
        "jobs": jobs
    }

