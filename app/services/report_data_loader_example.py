"""
Exemple d'utilisation de ReportDataLoader dans les générateurs de rapports.

Ce fichier montre comment utiliser ReportDataLoader pour charger les données
dans les générateurs de rapports (RPROG, RAP, etc.).
"""

from sqlmodel import Session
from app.services.report_data_loader import ReportDataLoader
from app.db.session import engine
from datetime import date


def example_usage_rprog():
    """
    Exemple d'utilisation pour le rapport RPROG (rapport d'activité par programme).
    """
    with Session(engine) as session:
        # Paramètres du rapport
        programme_nom = "ADMINISTRATION GENERALE"
        annee = 2026
        
        # Charger les données de performance pour ce programme
        data_performance = ReportDataLoader.load_data_performance(
            session=session,
            annee=annee,
            programme_nom=programme_nom
        )
        
        # Utiliser les données
        objectifs_avec_indicateurs = data_performance["objectifs_avec_indicateurs"]
        
        print(f"✅ {len(objectifs_avec_indicateurs)} objectifs avec indicateurs trouvés")
        for obj_data in objectifs_avec_indicateurs:
            objectif = obj_data["objectif"]
            indicateurs = obj_data["indicateurs"]
            print(f"   - {objectif.titre}: {len(indicateurs)} indicateur(s)")


def example_usage_rap():
    """
    Exemple d'utilisation pour le rapport annuel de performance (RAP).
    """
    with Session(engine) as session:
        # Paramètres du rapport
        annee = 2026
        
        # Charger toutes les données en une fois
        all_data = ReportDataLoader.load_all_data(
            session=session,
            annee=annee
        )
        
        # Utiliser les données
        data_performance = all_data["data_performance"]
        data_ministere = all_data["data_ministere"]
        data_sigobe = all_data["data_sigobe"]
        data_agents = all_data["data_agents"]
        data_programmes = all_data["data_programmes"]
        
        # Exemple : Utiliser les données de performance
        realisations = data_performance["realisations"]
        print(f"✅ {len(realisations)} réalisations trouvées")
        
        # Exemple : Utiliser les données ministérielles
        orientations = data_ministere["orientations"]
        print(f"✅ {len(orientations)} orientations stratégiques trouvées")
        
        # Exemple : Utiliser les données SIGOBE
        investissements = data_sigobe["investissements"]
        print(f"✅ {len(investissements)} investissements trouvés")
        
        # Exemple : Utiliser les données agents
        total_agents = data_agents["total_agents"]
        print(f"✅ {total_agents} agents trouvés")


def example_usage_selective():
    """
    Exemple d'utilisation sélective (charger seulement ce dont on a besoin).
    """
    with Session(engine) as session:
        annee = 2026
        programme_id = 2
        
        # Charger seulement les données de performance
        data_performance = ReportDataLoader.load_data_performance(
            session=session,
            annee=annee,
            programme_id=programme_id
        )
        
        # Charger seulement les données SIGOBE
        data_sigobe = ReportDataLoader.load_data_sigobe(
            session=session,
            annee=annee,
            programme_nom="ADMINISTRATION GENERALE"
        )
        
        # Utiliser les données
        architecture = data_performance["architecture"]
        print(f"Architecture: {architecture}")
        
        investissements = data_sigobe["investissements"]
        print(f"Investissements: {len(investissements)}")


if __name__ == "__main__":
    print("=" * 80)
    print("EXEMPLE 1: Utilisation pour RPROG")
    print("=" * 80)
    example_usage_rprog()
    
    print("\n" + "=" * 80)
    print("EXEMPLE 2: Utilisation pour RAP (toutes les données)")
    print("=" * 80)
    example_usage_rap()
    
    print("\n" + "=" * 80)
    print("EXEMPLE 3: Utilisation sélective")
    print("=" * 80)
    example_usage_selective()

