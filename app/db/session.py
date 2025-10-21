from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import QueuePool

# from app.core.logique_metier.rh_workflow import ensure_workflow_steps  # ← Ancien système désactivé
from app.core.config import settings

# Configuration optimisée pour les connexions simultanées
engine = create_engine(
    settings.database_url, 
    echo=settings.DEBUG,
    # Pool de connexions optimisé pour la production
    poolclass=QueuePool,
    pool_size=10,           # Connexions permanentes (au lieu de 5)
    max_overflow=20,        # Connexions supplémentaires (au lieu de 10)
    pool_timeout=30,        # Timeout d'attente d'une connexion (secondes)
    pool_recycle=3600,      # Recyclage des connexions (1 heure)
    pool_pre_ping=True      # Test de connexion avant utilisation
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        # ensure_workflow_steps(session)  # ← Ancien système désactivé - Utiliser les workflows personnalisés
        yield session
