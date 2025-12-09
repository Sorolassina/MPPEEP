"""
Script pour corriger les noms de programmes dans SIGOBE.

Ce script met à jour les noms de programmes dans la table sigobe_execution
pour qu'ils correspondent aux noms corrects dans la table programme.
"""

import logging
from sqlmodel import Session, select
from app.db.session import engine
from app.models.personnel import Programme
from app.models.budget import SigobeExecution, SigobeChargement

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_sigobe_programme_names(session: Session, dry_run: bool = True):
    """
    Corrige les noms de programmes dans SIGOBE.
    
    Args:
        session: Session de base de données
        dry_run: Si True, n'applique pas les modifications, juste affiche ce qui serait fait
    """
    logger.info("🔧 Début de la correction des noms de programmes dans SIGOBE")
    if dry_run:
        logger.info("⚠️ MODE DRY-RUN : Aucune modification ne sera appliquée")
    
    # 1. Récupérer tous les programmes actifs
    programmes_query = select(Programme).where(Programme.actif == True).order_by(Programme.code)
    programmes = list(session.exec(programmes_query).all())
    
    logger.info(f"📋 {len(programmes)} programmes actifs trouvés dans la base de données:")
    for prog in programmes:
        logger.info(f"   - {prog.code or 'N/A'}: {prog.libelle}")
    
    # 2. Récupérer tous les chargements SIGOBE
    chargements = list(session.exec(select(SigobeChargement).order_by(SigobeChargement.annee.desc(), SigobeChargement.date_chargement.desc())).all())
    
    if not chargements:
        logger.warning("⚠️ Aucun chargement SIGOBE trouvé")
        return
    
    logger.info(f"📊 {len(chargements)} chargement(s) SIGOBE trouvé(s)")
    
    # 3. Créer un mapping des noms SIGOBE vers les noms corrects
    # On va chercher toutes les valeurs distinctes de programmes dans SIGOBE
    all_sigobe_programmes = set()
    for chargement in chargements:
        executions = session.exec(
            select(SigobeExecution)
            .where(SigobeExecution.chargement_id == chargement.id)
            .where(SigobeExecution.programmes.isnot(None))
            .where(SigobeExecution.programmes != "")
        ).all()
        
        for exec_sigobe in executions:
            if exec_sigobe.programmes:
                all_sigobe_programmes.add(exec_sigobe.programmes.strip())
    
    logger.info(f"📊 {len(all_sigobe_programmes)} nom(s) de programme(s) distinct(s) trouvé(s) dans SIGOBE:")
    for sigobe_nom in sorted(all_sigobe_programmes):
        logger.info(f"   - '{sigobe_nom}'")
    
    # 4. Créer un mapping automatique basé sur la correspondance
    mapping = {}
    
    for sigobe_nom in all_sigobe_programmes:
        sigobe_nom_upper = sigobe_nom.upper().strip()
        matched_programme = None
        
        # Chercher une correspondance exacte
        for prog in programmes:
            prog_nom = (prog.libelle or "").upper().strip()
            if prog_nom == sigobe_nom_upper:
                matched_programme = prog
                logger.info(f"✅ Correspondance exacte trouvée: '{sigobe_nom}' → '{prog.libelle}'")
                break
        
        # Si pas de correspondance exacte, chercher une correspondance partielle
        if not matched_programme:
            for prog in programmes:
                prog_nom = (prog.libelle or "").upper().strip()
                # Vérifier si un nom contient l'autre ou vice versa
                if (sigobe_nom_upper in prog_nom or prog_nom in sigobe_nom_upper) and len(prog_nom) > 3:
                    matched_programme = prog
                    logger.info(f"✅ Correspondance partielle trouvée: '{sigobe_nom}' → '{prog.libelle}'")
                    break
        
        if matched_programme:
            mapping[sigobe_nom] = matched_programme.libelle
        else:
            logger.warning(f"⚠️ Aucune correspondance trouvée pour: '{sigobe_nom}'")
    
    # Mapping manuel pour les cas spécifiques
    # Format: "nom_dans_sigobe": "nom_correct_dans_programme"
    manual_mapping = {
        "AFFAIRES ADMINISTRATIVES ET FINANCIERES": "ADMINISTRATION GENERALE",
        "DIRECTION DES AFFAIRES ADMINISTRATIVES ET FINANCIERES": "ADMINISTRATION GENERALE",
        "AFFAIRES ADMINISTRATIVES ET FINANCIERES": "ADMINISTRATION GENERALE",
        "AFFAIRES ADMINISTRATIVES ET FINANCIERE": "ADMINISTRATION GENERALE",
        "DIRECTION AFFAIRES ADMINISTRATIVES ET FINANCIERES": "ADMINISTRATION GENERALE",
        "DIRECTION AFFAIRES ADMINISTRATIVES ET FINANCIERE": "ADMINISTRATION GENERALE",
        # Ajouter d'autres mappings manuels si nécessaire
        # Exemples:
        # "NOM_DANS_SIGOBE": "NOM_CORRECT",
    }
    
    # Appliquer le mapping manuel (écrase les correspondances automatiques si nécessaire)
    for sigobe_nom, correct_nom in manual_mapping.items():
        if sigobe_nom in all_sigobe_programmes:
            mapping[sigobe_nom] = correct_nom
            logger.info(f"📝 Mapping manuel: '{sigobe_nom}' → '{correct_nom}'")
    
    logger.info(f"\n📋 Mapping final ({len(mapping)} correspondance(s)):")
    for sigobe_nom, correct_nom in sorted(mapping.items()):
        logger.info(f"   '{sigobe_nom}' → '{correct_nom}'")
    
    # 5. Appliquer les corrections
    total_updated = 0
    
    for chargement in chargements:
        executions = session.exec(
            select(SigobeExecution)
            .where(SigobeExecution.chargement_id == chargement.id)
            .where(SigobeExecution.programmes.isnot(None))
            .where(SigobeExecution.programmes != "")
        ).all()
        
        for exec_sigobe in executions:
            if exec_sigobe.programmes:
                sigobe_nom_original = exec_sigobe.programmes.strip()
                if sigobe_nom_original in mapping:
                    correct_nom = mapping[sigobe_nom_original]
                    if exec_sigobe.programmes != correct_nom:
                        logger.info(f"🔄 Mise à jour: '{exec_sigobe.programmes}' → '{correct_nom}' (chargement {chargement.annee})")
                        if not dry_run:
                            exec_sigobe.programmes = correct_nom
                        total_updated += 1
    
    if dry_run:
        logger.info(f"\n✅ MODE DRY-RUN : {total_updated} entrée(s) seraient mise(s) à jour")
        logger.info("💡 Pour appliquer les modifications, relancez le script avec dry_run=False")
    else:
        session.commit()
        logger.info(f"\n✅ {total_updated} entrée(s) mise(s) à jour avec succès")
    
    return total_updated


if __name__ == "__main__":
    with Session(engine) as session:
        # D'abord, afficher ce qui serait fait (dry_run=True)
        logger.info("=" * 80)
        logger.info("ÉTAPE 1 : Analyse (mode dry-run)")
        logger.info("=" * 80)
        fix_sigobe_programme_names(session, dry_run=True)
        
        # Demander confirmation avant d'appliquer
        logger.info("\n" + "=" * 80)
        logger.info("Pour appliquer les modifications, décommentez la ligne suivante :")
        logger.info("# fix_sigobe_programme_names(session, dry_run=False)")
        logger.info("=" * 80)
        
        # Décommenter la ligne suivante pour appliquer les modifications
        # fix_sigobe_programme_names(session, dry_run=False)

