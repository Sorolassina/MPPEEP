from sqlmodel import SQLModel, Session, create_engine
# from app.core.logique_metier.rh_workflow import ensure_workflow_steps  # ← Ancien système désactivé
from app.core.config import settings

# Utilise la propriété database_url qui bascule automatiquement selon l'environnement
engine = create_engine(settings.database_url, echo=settings.DEBUG)

def init_db() -> None:
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        # ensure_workflow_steps(session)  # ← Ancien système désactivé - Utiliser les workflows personnalisés
        yield session


