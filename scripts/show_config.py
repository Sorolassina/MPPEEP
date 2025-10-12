"""
Script utilitaire pour afficher la configuration actuelle de l'application
(Ce n'est PAS un test pytest, c'est un outil de diagnostic)
"""
from app.core.config import settings

def show_config():
    print("=" * 60)
    print("📋 CONFIGURATION ACTUELLE")
    print("=" * 60)
    print(f"🏷️  App Name      : {settings.APP_NAME}")
    print(f"🌍 Environment   : {settings.ENV}")
    print(f"🐛 Debug Mode    : {settings.DEBUG}")
    print(f"🔑 Secret Key    : {settings.SECRET_KEY[:10]}... (caché)")
    print()
    print("=" * 60)
    print("🗄️  BASE DE DONNÉES")
    print("=" * 60)
    
    db_url = settings.database_url
    
    if db_url.startswith("sqlite"):
        print("✅ Type          : SQLite (Développement)")
        print(f"📁 Fichier       : {settings.SQLITE_DB_PATH}")
        print("⚡ Performances  : Rapide pour le développement")
        print("👥 Concurrence   : Limitée (1 écriture à la fois)")
        print("💡 Conseil       : Parfait pour développer !")
    elif db_url.startswith("postgresql"):
        print("✅ Type          : PostgreSQL (Production)")
        print(f"🖥️  Host          : {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
        print(f"🗃️  Database      : {settings.POSTGRES_DB}")
        print(f"👤 User          : {settings.POSTGRES_USER}")
        print("⚡ Performances  : Excellent pour la production")
        print("👥 Concurrence   : Élevée (écritures multiples)")
        print("💡 Conseil       : Prêt pour la production !")
    else:
        print(f"✅ Type          : Personnalisé")
    
    print()
    print(f"🔗 Connection URL: {db_url}")
    print()
    print("=" * 60)
    print("📝 COMMENT CHANGER ?")
    print("=" * 60)
    print("1. Créer un fichier .env à partir de env.example")
    print("2. Modifier DEBUG=true (SQLite) ou DEBUG=false (PostgreSQL)")
    print("3. Ou définir directement DATABASE_URL dans .env")
    print()
    print("Exemples:")
    print("  # Copier un template")
    print("  cp env.example .env")
    print()
    print("  # Ou définir directement")
    print("  echo 'DEBUG=true' > .env")
    print("=" * 60)

if __name__ == "__main__":
    show_config()

