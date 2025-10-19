"""
Migration: Ajouter le champ responsable_id à la table programme

Ce script ajoute la colonne responsable_id à la table programme
pour permettre d'affecter un responsable (agent_complet) à chaque programme.
"""
from sqlalchemy import text
from app.db.session import engine

def migrate():
    """Ajoute la colonne responsable_id à la table programme"""
    
    print("🔄 Vérification de la colonne responsable_id dans la table programme...")
    
    with engine.connect() as conn:
        # Vérifier si la colonne existe déjà
        result = conn.execute(text("""
            SELECT COUNT(*) as count
            FROM pragma_table_info('programme')
            WHERE name = 'responsable_id'
        """))
        
        exists = result.fetchone()[0] > 0
        
        if exists:
            print("✅ La colonne responsable_id existe déjà dans la table programme")
            return
        
        print("➕ Ajout de la colonne responsable_id à la table programme...")
        
        # Ajouter la colonne
        conn.execute(text("""
            ALTER TABLE programme
            ADD COLUMN responsable_id INTEGER
            REFERENCES agent_complet(id)
        """))
        
        conn.commit()
        
        print("✅ Colonne responsable_id ajoutée avec succès !")
        print("")
        print("📝 Structure mise à jour :")
        print("   - Programme.responsable_id → agent_complet.id")
        print("   - Direction.directeur_id → agent_complet.id")
        print("   - Service.chef_service_id → agent_complet.id")
        print("")
        print("🎯 Utilisation dans les workflows :")
        print("   Vous pouvez maintenant affecter des responsables à chaque niveau")
        print("   de la structure organisationnelle pour les utiliser dans les")
        print("   circuits de validation.")

if __name__ == "__main__":
    try:
        migrate()
        print("\n✅ Migration terminée avec succès !")
    except Exception as e:
        print(f"\n❌ Erreur lors de la migration : {e}")
        raise

