# 📘 Modules du Projet MPPEEP - Documentation Détaillée

## 🎯 Vue d'ensemble

Ce document détaille **tous les modules** du projet MPPEEP, leur architecture, leurs fonctionnalités et leurs interactions.

---

## 📂 STRUCTURE GLOBALE DU PROJET

```
mppeep/
├── app/
│   ├── api/              # Routes et endpoints API
│   ├── core/             # Configuration et utilitaires
│   ├── db/               # Base de données
│   ├── models/           # Modèles SQLModel (ORM)
│   ├── services/         # Logique métier
│   ├── static/           # Fichiers statiques (CSS, JS, images)
│   └── templates/        # Templates Jinja2 (HTML)
├── documentation/        # Documentation complète
├── scripts/              # Scripts utilitaires
├── tests/                # Tests unitaires et d'intégration
├── main.py               # Point d'entrée de l'application
├── requirements.txt      # Dépendances Python
└── README.md             # Documentation principale
```

---

# 🏗️ MODULE 1 : CORE (Configuration et Utilitaires)

## Fichiers

### `app/core/config.py`

**Rôle** : Configuration globale de l'application

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Configuration de l'application"""
    
    # Base de données
    DATABASE_URL: str = "sqlite:///./mppeep.db"
    
    # Sécurité
    SECRET_KEY: str = "votre-clé-secrète-super-longue-et-aléatoire"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 heures
    
    # Application
    APP_NAME: str = "MPPEEP Dashboard"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:9000"]
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**Utilisation** :
```python
from app.core.config import settings

print(settings.DATABASE_URL)  # "sqlite:///./mppeep.db"
print(settings.SECRET_KEY)     # "votre-clé-secrète..."
```

### `app/core/security.py`

**Rôle** : Gestion de la sécurité (hachage, JWT)

```python
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

# Configuration bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hache un mot de passe avec bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Crée un token JWT"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt
```

**Exemple** :
```python
# Hacher un mot de passe
hashed = hash_password("MonMotDePasse123")
# "$2b$12$KIXxLV7vZq..."

# Vérifier un mot de passe
is_valid = verify_password("MonMotDePasse123", hashed)
# True

# Créer un token JWT
token = create_access_token(
    data={"sub": "1"},  # User ID
    expires_delta=timedelta(hours=24)
)
# "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### `app/core/enums.py`

**Rôle** : Énumérations pour les constantes

```python
from enum import Enum

class UserRole(str, Enum):
    """Rôles utilisateur"""
    ADMIN = "ADMIN"
    USER = "USER"
    VIEWER = "VIEWER"

class WorkflowState(str, Enum):
    """États du workflow RH"""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    VALIDATION_N1 = "VALIDATION_N1"
    VALIDATION_N2 = "VALIDATION_N2"
    VALIDATION_N3 = "VALIDATION_N3"
    VALIDATION_N4 = "VALIDATION_N4"
    VALIDATION_N5 = "VALIDATION_N5"
    VALIDATION_N6 = "VALIDATION_N6"
    ARCHIVED = "ARCHIVED"
    REJECTED = "REJECTED"

class SexeType(str, Enum):
    """Sexe"""
    MASCULIN = "MASCULIN"
    FEMININ = "FEMININ"

class SituationFamiliale(str, Enum):
    """Situation familiale"""
    CELIBATAIRE = "CELIBATAIRE"
    MARIE = "MARIE"
    DIVORCE = "DIVORCE"
    VEUF = "VEUF"
    UNION_LIBRE = "UNION_LIBRE"
```

**Utilisation** :
```python
from app.core.enums import UserRole, WorkflowState

user_role = UserRole.ADMIN
if user_role == UserRole.ADMIN:
    print("L'utilisateur est admin")

state = WorkflowState.VALIDATION_N1
print(state.value)  # "VALIDATION_N1"
```

### `app/core/logging_config.py`

**Rôle** : Configuration des logs

```python
import logging
import sys
from datetime import datetime

def setup_logging():
    """Configure le système de logging"""
    
    # Format des logs
    log_format = "[%(asctime)s] %(levelname)s | %(name)s | %(message)s"
    date_format = "%H:%M:%S"
    
    # Configuration
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),  # Console
            logging.FileHandler(f"logs/mppeep_{datetime.now().strftime('%Y%m%d')}.log")  # Fichier
        ]
    )

def get_logger(name: str) -> logging.Logger:
    """Récupère un logger"""
    return logging.getLogger(name)
```

**Utilisation** :
```python
from app.core.logging_config import get_logger

logger = get_logger(__name__)

logger.info("Application démarrée")
logger.warning("Attention : stock faible")
logger.error("Erreur lors de la connexion DB")
```

---

# 🗄️ MODULE 2 : DATABASE (Base de données)

## Fichiers

### `app/db/session.py`

**Rôle** : Gestion de la connexion à la base de données

```python
from sqlmodel import create_engine, Session, SQLModel
from app.core.config import settings

# Moteur SQLite
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,  # True pour voir les requêtes SQL
    connect_args={"check_same_thread": False}  # SQLite only
)

def create_db_and_tables():
    """Crée toutes les tables de la base de données"""
    # Import de tous les modèles
    from app.models import *
    
    # Création des tables
    SQLModel.metadata.create_all(engine)

def get_session():
    """Dependency pour obtenir une session DB"""
    with Session(engine) as session:
        yield session
```

**Utilisation** :
```python
from app.db.session import get_session
from fastapi import Depends

@router.get("/users")
def list_users(session: Session = Depends(get_session)):
    users = session.exec(select(User)).all()
    return users
```

---

# 🏛️ MODULE 3 : MODELS (Modèles de données)

## Architecture SQLModel

SQLModel = SQLAlchemy + Pydantic

**Avantages** :
- ✅ Validation automatique des données
- ✅ Serialization JSON
- ✅ Type hints Python
- ✅ Documentation auto-générée

## Fichiers de modèles

### `app/models/user.py`

**Modèle : Utilisateur**

```python
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from app.core.enums import UserRole

class User(SQLModel, table=True):
    """Utilisateur du système"""
    __tablename__ = "user"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    hashed_password: str
    full_name: str = Field(max_length=255)
    role: UserRole = Field(default=UserRole.USER)
    is_active: bool = Field(default=True)
    agent_id: Optional[int] = Field(default=None, foreign_key="agent_complet.id")
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

**Champs** :
- `id` : Clé primaire auto-incrémentée
- `email` : Email unique (login)
- `hashed_password` : Mot de passe hashé avec bcrypt
- `full_name` : Nom complet
- `role` : Rôle (ADMIN, USER, VIEWER)
- `is_active` : Compte actif ou désactivé
- `agent_id` : Lien vers la fiche agent (peut être NULL)

**Requêtes SQL** :
```python
# Créer un utilisateur
user = User(
    email="john.doe@example.com",
    hashed_password=hash_password("password123"),
    full_name="John Doe",
    role=UserRole.USER
)
session.add(user)
session.commit()

# Récupérer par email
user = session.exec(
    select(User).where(User.email == "john.doe@example.com")
).first()

# Modifier
user.is_active = False
session.add(user)
session.commit()

# Supprimer
session.delete(user)
session.commit()
```

### `app/models/personnel.py`

**Modèle : Agent (Personnel)**

```python
class AgentComplet(SQLModel, table=True):
    """Agent (membre du personnel)"""
    __tablename__ = "agent_complet"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Identification
    matricule: str = Field(unique=True, index=True, max_length=50)
    nom: str = Field(max_length=100)
    prenom: str = Field(max_length=100)
    sexe: Optional[SexeType] = None
    date_naissance: Optional[date] = None
    lieu_naissance: Optional[str] = Field(default=None, max_length=200)
    situation_familiale: Optional[SituationFamiliale] = None
    nombre_enfants: Optional[int] = Field(default=0)
    
    # Contact
    telephone: Optional[str] = Field(default=None, max_length=20)
    email_professionnel: Optional[str] = Field(default=None, max_length=255)
    email_personnel: Optional[str] = Field(default=None, max_length=255)
    adresse: Optional[str] = None
    
    # Carrière
    grade_id: Optional[int] = Field(default=None, foreign_key="grade_complet.id")
    programme_id: Optional[int] = Field(default=None, foreign_key="programme_budgetaire.id")
    direction_id: Optional[int] = Field(default=None, foreign_key="direction.id")
    service_id: Optional[int] = Field(default=None, foreign_key="service.id")
    fonction: Optional[str] = Field(default=None, max_length=200)
    
    date_recrutement: Optional[date] = None
    date_prise_service: Optional[date] = None
    position_administrative: Optional[str] = Field(default=None, max_length=100)
    
    # État
    actif: bool = Field(default=True)
    
    # Audit
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

**Exemple d'utilisation** :
```python
# Créer un agent
agent = AgentComplet(
    matricule="2025-001",
    nom="DUPONT",
    prenom="Jean",
    sexe=SexeType.MASCULIN,
    date_naissance=date(1985, 5, 15),
    grade_id=5,
    service_id=3,
    fonction="Chef de Service",
    date_recrutement=date(2010, 1, 15)
)
session.add(agent)
session.commit()

# Recherche avec jointure
agents = session.exec(
    select(AgentComplet, GradeComplet, Service)
    .join(GradeComplet, AgentComplet.grade_id == GradeComplet.id)
    .join(Service, AgentComplet.service_id == Service.id)
    .where(AgentComplet.actif == True)
).all()
```

### `app/models/rh.py`

**Modèle : Demande RH**

```python
class HRRequest(SQLModel, table=True):
    """Demande RH (congé, mission, formation, etc.)"""
    __tablename__ = "hrrequest"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Agent demandeur
    agent_id: int = Field(foreign_key="agent_complet.id", index=True)
    
    # Type de demande (dynamique)
    type: str = Field(max_length=50, index=True)  # Code du RequestTypeCustom
    
    # Dates
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    
    # Contenu
    objet: Optional[str] = Field(default=None, max_length=500)
    motif: Optional[str] = None
    description: Optional[str] = None
    
    # Workflow
    current_state: WorkflowState = Field(default=WorkflowState.DRAFT, index=True)
    
    # Satisfaction (pour besoins d'actes)
    satisfaction_note: Optional[int] = Field(default=None, ge=1, le=5)
    satisfaction_commentaire: Optional[str] = None
    satisfaction_date: Optional[date] = None
    
    # Audit
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

**Workflow History** :

```python
class WorkflowHistory(SQLModel, table=True):
    """Historique des transitions de workflow"""
    __tablename__ = "workflowhistory"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    request_id: int = Field(foreign_key="hrrequest.id", index=True)
    from_state: str = Field(max_length=50)
    to_state: str = Field(max_length=50)
    
    validator_id: Optional[int] = Field(default=None, foreign_key="user.id")
    validator_name: Optional[str] = Field(default=None, max_length=255)
    
    decision: str = Field(max_length=20)  # APPROVED, REJECTED
    commentaire: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.now)
```

**Exemple** :
```python
# Créer une demande
request = HRRequest(
    agent_id=1,
    type="CONGE",
    date_debut=date(2025, 12, 1),
    date_fin=date(2025, 12, 31),
    objet="Congés annuels 2025",
    motif="Repos annuel",
    current_state=WorkflowState.DRAFT
)
session.add(request)
session.commit()

# Enregistrer une validation
history = WorkflowHistory(
    request_id=request.id,
    from_state=WorkflowState.SUBMITTED.value,
    to_state=WorkflowState.VALIDATION_N1.value,
    validator_id=2,
    validator_name="Chef de Service",
    decision="APPROVED",
    commentaire="Accord donné"
)
session.add(history)
session.commit()
```

### `app/models/workflow_config.py`

**Modèles : Workflow Personnalisé**

```python
class CustomRole(SQLModel, table=True):
    """Rôle personnalisé pour le workflow"""
    __tablename__ = "custom_role"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, max_length=50, index=True)
    libelle: str = Field(max_length=200)
    description: Optional[str] = None
    actif: bool = Field(default=True)
    ordre: int = Field(default=0)
    
    created_at: datetime = Field(default_factory=datetime.now)

class CustomRoleAssignment(SQLModel, table=True):
    """Attribution d'un rôle à un agent"""
    __tablename__ = "custom_role_assignment"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    custom_role_id: int = Field(foreign_key="custom_role.id", index=True)
    agent_id: int = Field(foreign_key="agent_complet.id", index=True)
    actif: bool = Field(default=True)
    
    created_at: datetime = Field(default_factory=datetime.now)

class WorkflowTemplate(SQLModel, table=True):
    """Template de workflow"""
    __tablename__ = "workflow_template"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, max_length=50)
    nom: str = Field(max_length=200)
    description: Optional[str] = None
    actif: bool = Field(default=True)
    
    created_at: datetime = Field(default_factory=datetime.now)

class WorkflowTemplateStep(SQLModel, table=True):
    """Étape d'un template de workflow"""
    __tablename__ = "workflow_template_step"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    template_id: int = Field(foreign_key="workflow_template.id", index=True)
    ordre: int  # 1, 2, 3...
    custom_role_id: int = Field(foreign_key="custom_role.id")
    
    created_at: datetime = Field(default_factory=datetime.now)

class RequestTypeCustom(SQLModel, table=True):
    """Type de demande personnalisé"""
    __tablename__ = "request_type_custom"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, max_length=50)
    libelle: str = Field(max_length=200)
    categorie: Optional[str] = Field(default=None, max_length=100)
    workflow_template_id: int = Field(foreign_key="workflow_template.id")
    actif: bool = Field(default=True)
    ordre: int = Field(default=0)
    
    created_at: datetime = Field(default_factory=datetime.now)
```

**Exemple complet** :
```python
# 1. Créer un rôle personnalisé
role = CustomRole(
    code="VALIDATEUR_CONGE",
    libelle="Validateur des Congés",
    description="Valide toutes les demandes de congé"
)
session.add(role)
session.commit()

# 2. Attribuer le rôle à un agent
assignment = CustomRoleAssignment(
    custom_role_id=role.id,
    agent_id=5  # Chef RH
)
session.add(assignment)
session.commit()

# 3. Créer un template de workflow
template = WorkflowTemplate(
    code="WF_CONGE",
    nom="Workflow Congés",
    description="N+1 → RH → Archivage"
)
session.add(template)
session.commit()

# 4. Ajouter les étapes
step1 = WorkflowTemplateStep(
    template_id=template.id,
    ordre=1,
    custom_role_id=role_n1.id  # Chef hiérarchique
)
step2 = WorkflowTemplateStep(
    template_id=template.id,
    ordre=2,
    custom_role_id=role_rh.id  # RH
)
session.add_all([step1, step2])
session.commit()

# 5. Créer un type de demande
request_type = RequestTypeCustom(
    code="CONGE_ANNUEL",
    libelle="Congé Annuel",
    categorie="Congés",
    workflow_template_id=template.id
)
session.add(request_type)
session.commit()
```

### `app/models/stock.py`

**Modèles : Gestion de Stock**

```python
class Article(SQLModel, table=True):
    """Article de stock"""
    __tablename__ = "article"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Identification
    code: str = Field(unique=True, max_length=50, index=True)
    designation: str = Field(max_length=255)
    description: Optional[str] = None
    categorie_id: Optional[int] = Field(default=None, foreign_key="categorie_article.id")
    unite: str = Field(default="Unité", max_length=20)
    
    # Stock
    quantite_actuelle: Decimal = Field(default=0, max_digits=10, decimal_places=2)
    quantite_min: Decimal = Field(default=0, max_digits=10, decimal_places=2)
    quantite_max: Decimal = Field(default=0, max_digits=10, decimal_places=2)
    
    # Prix
    prix_unitaire: Optional[Decimal] = Field(default=None, max_digits=15, decimal_places=2)
    
    # Localisation
    emplacement: Optional[str] = Field(default=None, max_length=100)
    
    # NOUVEAUTÉ : Articles Périssables
    est_perissable: bool = Field(default=False)
    seuil_alerte_peremption_jours: int = Field(default=30)
    
    # NOUVEAUTÉ : Amortissement
    est_amortissable: bool = Field(default=False)
    date_acquisition: Optional[date] = None
    valeur_acquisition: Optional[Decimal] = Field(default=None, max_digits=15, decimal_places=2)
    duree_amortissement_annees: Optional[int] = None
    taux_amortissement: Optional[Decimal] = Field(default=None, max_digits=5, decimal_places=2)
    valeur_residuelle: Optional[Decimal] = Field(default=None, max_digits=15, decimal_places=2)
    methode_amortissement: Optional[str] = Field(default="LINEAIRE", max_length=20)
    
    # État
    actif: bool = Field(default=True)
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class LotPerissable(SQLModel, table=True):
    """Lot périssable avec date de péremption"""
    __tablename__ = "lot_perissable"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="article.id", index=True)
    
    numero_lot: str = Field(max_length=100, index=True)
    date_fabrication: Optional[date] = None
    date_reception: date = Field(default_factory=date.today)
    date_peremption: date  # OBLIGATOIRE
    
    quantite_initiale: Decimal = Field(max_digits=10, decimal_places=2)
    quantite_restante: Decimal = Field(max_digits=10, decimal_places=2)
    
    statut: str = Field(default="ACTIF", max_length=20)  # ACTIF, ALERTE, PERIME, EPUISE
    fournisseur_id: Optional[int] = Field(default=None, foreign_key="fournisseur.id")
    observations: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.now)

class Amortissement(SQLModel, table=True):
    """Historique des amortissements annuels"""
    __tablename__ = "amortissement"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="article.id", index=True)
    
    annee: int = Field(index=True)
    periode: str = Field(max_length=50)
    
    valeur_brute: Decimal = Field(max_digits=15, decimal_places=2)
    amortissement_cumule_debut: Decimal = Field(max_digits=15, decimal_places=2)
    amortissement_periode: Decimal = Field(max_digits=15, decimal_places=2)
    amortissement_cumule_fin: Decimal = Field(max_digits=15, decimal_places=2)
    valeur_nette_comptable: Decimal = Field(max_digits=15, decimal_places=2)
    
    taux_applique: Decimal = Field(max_digits=5, decimal_places=2)
    methode: str = Field(max_length=20)
    statut: str = Field(default="CALCULE", max_length=20)
    totalement_amorti: bool = Field(default=False)
    
    created_at: datetime = Field(default_factory=datetime.now)
```

---

# 🔧 MODULE 4 : SERVICES (Logique métier)

Les services contiennent la **logique métier** pure, sans dépendance à FastAPI.

## Fichiers

### `app/services/rh.py`

**Service RH**

```python
class RHService:
    """Service pour la gestion RH"""
    
    @staticmethod
    def next_states_for(session: Session, request_id: int) -> List[Dict]:
        """Retourne les états suivants possibles"""
        request = session.get(HRRequest, request_id)
        if not request:
            return []
        
        # Récupérer le circuit de workflow
        circuit = HierarchyService.get_workflow_circuit(session, request_id)
        
        # Trouver l'index de l'état actuel
        try:
            current_index = circuit.index(request.current_state)
        except ValueError:
            return []
        
        # L'état suivant est le prochain dans le circuit
        if current_index + 1 < len(circuit):
            next_state = circuit[current_index + 1]
            return [{
                "state": next_state.value,
                "label": next_state.value.replace("_", " ").title()
            }]
        
        return []
    
    @staticmethod
    def transition(
        session: Session,
        request_id: int,
        to_state: WorkflowState,
        user_id: int,
        commentaire: Optional[str] = None
    ) -> HRRequest:
        """Effectue une transition de workflow"""
        
        request = session.get(HRRequest, request_id)
        if not request:
            raise ValueError("Demande introuvable")
        
        # Vérifier que l'utilisateur peut valider
        can_validate = HierarchyService.can_user_validate(
            session, user_id, request_id, to_state
        )
        
        if not can_validate:
            raise PermissionError("Vous n'êtes pas autorisé à valider cette étape")
        
        # Enregistrer l'historique
        validator = HierarchyService.get_expected_validator(session, request_id, to_state)
        
        history = WorkflowHistory(
            request_id=request_id,
            from_state=request.current_state.value,
            to_state=to_state.value,
            validator_id=user_id,
            validator_name=validator.nom if validator else "Inconnu",
            decision="APPROVED" if to_state != WorkflowState.REJECTED else "REJECTED",
            commentaire=commentaire
        )
        session.add(history)
        
        # Mettre à jour l'état
        request.current_state = to_state
        request.updated_at = datetime.now()
        session.add(request)
        session.commit()
        session.refresh(request)
        
        return request
    
    @staticmethod
    def kpis(session: Session) -> Dict:
        """Calcule les KPIs RH"""
        
        # Nombre total d'agents
        total_agents = session.exec(
            select(func.count(AgentComplet.id))
            .where(AgentComplet.actif == True)
        ).one()
        
        # Demandes par état
        demandes_par_etat = {}
        for state in WorkflowState:
            count = session.exec(
                select(func.count(HRRequest.id))
                .where(HRRequest.current_state == state)
            ).one()
            demandes_par_etat[state.value] = count
        
        # Demandes par type
        demandes_par_type = {}
        request_types = session.exec(select(RequestTypeCustom)).all()
        for rt in request_types:
            count = session.exec(
                select(func.count(HRRequest.id))
                .where(HRRequest.type == rt.code)
            ).one()
            demandes_par_type[rt.code] = count
        
        return {
            "total_agents": total_agents,
            "demandes_par_etat": demandes_par_etat,
            "demandes_par_type": demandes_par_type
        }
```

### `app/services/hierarchy_service.py`

**Service de gestion du workflow hiérarchique**

```python
class HierarchyService:
    """Service pour gérer la hiérarchie et les workflows"""
    
    @staticmethod
    def get_workflow_circuit(session: Session, request_id: int) -> List[WorkflowState]:
        """Retourne le circuit de workflow complet pour une demande"""
        
        request = session.get(HRRequest, request_id)
        if not request:
            return []
        
        # Récupérer le type de demande
        request_type = session.exec(
            select(RequestTypeCustom).where(RequestTypeCustom.code == request.type)
        ).first()
        
        if not request_type:
            return [WorkflowState.DRAFT, WorkflowState.SUBMITTED, WorkflowState.ARCHIVED]
        
        # Récupérer les étapes du template
        steps = session.exec(
            select(WorkflowTemplateStep)
            .where(WorkflowTemplateStep.template_id == request_type.workflow_template_id)
            .order_by(WorkflowTemplateStep.ordre)
        ).all()
        
        # Construire le circuit
        circuit = [WorkflowState.DRAFT, WorkflowState.SUBMITTED]
        
        for i, step in enumerate(steps):
            # Mapper les étapes aux états VALIDATION_N1, N2, etc.
            if i < 6:
                circuit.append(getattr(WorkflowState, f"VALIDATION_N{i+1}"))
        
        circuit.append(WorkflowState.ARCHIVED)
        
        return circuit
    
    @staticmethod
    def get_expected_validator(
        session: Session,
        request_id: int,
        to_state: WorkflowState
    ) -> Optional[AgentComplet]:
        """Retourne l'agent censé valider une étape"""
        
        request = session.get(HRRequest, request_id)
        if not request:
            return None
        
        # Cas spécial : DRAFT → SUBMITTED (l'agent lui-même)
        if to_state == WorkflowState.SUBMITTED:
            return session.get(AgentComplet, request.agent_id)
        
        # Récupérer le type de demande
        request_type = session.exec(
            select(RequestTypeCustom).where(RequestTypeCustom.code == request.type)
        ).first()
        
        if not request_type:
            return None
        
        # Trouver l'étape correspondante
        step_index = HierarchyService._get_step_index_for_state(to_state)
        if step_index is None:
            return None
        
        # Récupérer l'étape du workflow
        step = session.exec(
            select(WorkflowTemplateStep)
            .where(
                WorkflowTemplateStep.template_id == request_type.workflow_template_id,
                WorkflowTemplateStep.ordre == step_index
            )
        ).first()
        
        if not step:
            return None
        
        # Trouver l'agent assigné à ce rôle
        assignment = session.exec(
            select(CustomRoleAssignment)
            .where(
                CustomRoleAssignment.custom_role_id == step.custom_role_id,
                CustomRoleAssignment.actif == True
            )
        ).first()
        
        if not assignment:
            return None
        
        return session.get(AgentComplet, assignment.agent_id)
    
    @staticmethod
    def can_user_validate(
        session: Session,
        user_id: int,
        request_id: int,
        to_state: WorkflowState
    ) -> bool:
        """Vérifie si un utilisateur peut valider une étape"""
        
        # Récupérer l'utilisateur et son agent
        user = session.get(User, user_id)
        if not user or not user.agent_id:
            return False
        
        user_agent = session.get(AgentComplet, user.agent_id)
        if not user_agent:
            return False
        
        # Récupérer la demande
        request = session.get(HRRequest, request_id)
        if not request:
            return False
        
        # Cas spécial : DRAFT → SUBMITTED (seul l'agent peut soumettre sa propre demande)
        if to_state == WorkflowState.SUBMITTED:
            return user_agent.id == request.agent_id
        
        # Trouver le validateur attendu
        expected_validator = HierarchyService.get_expected_validator(
            session, request_id, to_state
        )
        
        if not expected_validator:
            return False
        
        # Vérifier que l'utilisateur est bien le validateur attendu
        return user_agent.id == expected_validator.id
    
    @staticmethod
    def get_pending_requests_for_user(
        session: Session,
        user_id: int
    ) -> List[HRRequest]:
        """Retourne les demandes en attente de validation par un utilisateur"""
        
        user = session.get(User, user_id)
        if not user or not user.agent_id:
            return []
        
        # Récupérer toutes les demandes non archivées/rejetées
        requests = session.exec(
            select(HRRequest)
            .where(
                HRRequest.current_state.not_in([
                    WorkflowState.ARCHIVED,
                    WorkflowState.REJECTED,
                    WorkflowState.DRAFT
                ])
            )
        ).all()
        
        pending = []
        for req in requests:
            # Déterminer l'état suivant
            circuit = HierarchyService.get_workflow_circuit(session, req.id)
            try:
                current_index = circuit.index(req.current_state)
                if current_index + 1 < len(circuit):
                    next_state = circuit[current_index + 1]
                    
                    # Vérifier si l'utilisateur peut valider cet état
                    if HierarchyService.can_user_validate(session, user_id, req.id, next_state):
                        pending.append(req)
            except ValueError:
                continue
        
        return pending
```

### `app/services/stock_service.py`

**Service Stock**

```python
class StockService:
    """Service pour la gestion de stock"""
    
    @staticmethod
    def creer_article(
        session: Session,
        code: str,
        designation: str,
        **kwargs
    ) -> Article:
        """Crée un nouvel article"""
        
        # Vérifier que le code est unique
        existing = session.exec(
            select(Article).where(Article.code == code)
        ).first()
        
        if existing:
            raise ValueError(f"Un article avec le code '{code}' existe déjà")
        
        article = Article(
            code=code,
            designation=designation,
            **kwargs
        )
        
        session.add(article)
        session.commit()
        session.refresh(article)
        
        return article
    
    @staticmethod
    def creer_lot_perissable(
        session: Session,
        article_id: int,
        numero_lot: str,
        quantite: Decimal,
        date_peremption: date,
        **kwargs
    ) -> LotPerissable:
        """Crée un lot périssable"""
        
        article = session.get(Article, article_id)
        if not article:
            raise ValueError("Article introuvable")
        
        if not article.est_perissable:
            raise ValueError("L'article n'est pas configuré comme périssable")
        
        # Calculer le statut selon la date de péremption
        jours_avant_peremption = (date_peremption - date.today()).days
        
        if jours_avant_peremption < 0:
            statut = "PERIME"
        elif jours_avant_peremption <= article.seuil_alerte_peremption_jours:
            statut = "ALERTE"
        else:
            statut = "ACTIF"
        
        lot = LotPerissable(
            article_id=article_id,
            numero_lot=numero_lot,
            quantite_initiale=quantite,
            quantite_restante=quantite,
            date_peremption=date_peremption,
            statut=statut,
            **kwargs
        )
        
        session.add(lot)
        session.commit()
        session.refresh(lot)
        
        return lot
    
    @staticmethod
    def get_lots_proches_peremption(
        session: Session,
        jours: int = 30
    ) -> List[LotPerissable]:
        """Retourne les lots proches de la péremption"""
        
        date_limite = date.today() + timedelta(days=jours)
        
        lots = session.exec(
            select(LotPerissable)
            .where(
                LotPerissable.statut.in_(["ACTIF", "ALERTE"]),
                LotPerissable.date_peremption <= date_limite,
                LotPerissable.date_peremption >= date.today(),
                LotPerissable.quantite_restante > 0
            )
            .order_by(LotPerissable.date_peremption)
        ).all()
        
        return lots
    
    @staticmethod
    def calculer_amortissement_lineaire(
        valeur_acquisition: Decimal,
        duree_annees: int,
        valeur_residuelle: Decimal = Decimal(0)
    ) -> Decimal:
        """Calcule l'amortissement annuel en méthode linéaire"""
        return (valeur_acquisition - valeur_residuelle) / Decimal(duree_annees)
    
    @staticmethod
    def calculer_amortissement_annee(
        session: Session,
        article_id: int,
        annee: int
    ) -> Amortissement:
        """Calcule l'amortissement d'un matériel pour une année"""
        
        article = session.get(Article, article_id)
        if not article:
            raise ValueError("Article introuvable")
        
        if not article.est_amortissable:
            raise ValueError("L'article n'est pas amortissable")
        
        if not article.date_acquisition or not article.valeur_acquisition:
            raise ValueError("Données d'amortissement incomplètes")
        
        # Vérifier si déjà calculé
        existing = session.exec(
            select(Amortissement).where(
                Amortissement.article_id == article_id,
                Amortissement.annee == annee
            )
        ).first()
        
        if existing:
            raise ValueError(f"L'amortissement pour l'année {annee} existe déjà")
        
        # Récupérer l'amortissement cumulé de l'année précédente
        amort_precedent = session.exec(
            select(Amortissement)
            .where(
                Amortissement.article_id == article_id,
                Amortissement.annee == annee - 1
            )
        ).first()
        
        if amort_precedent:
            amortissement_cumule_debut = amort_precedent.amortissement_cumule_fin
        else:
            amortissement_cumule_debut = Decimal(0)
        
        # Calculer l'amortissement de l'année
        valeur_residuelle = article.valeur_residuelle or Decimal(0)
        
        if article.methode_amortissement == "LINEAIRE":
            amortissement_annuel = StockService.calculer_amortissement_lineaire(
                article.valeur_acquisition,
                article.duree_amortissement_annees,
                valeur_residuelle
            )
            taux_applique = Decimal(100) / Decimal(article.duree_amortissement_annees)
        
        elif article.methode_amortissement == "DEGRESSIF":
            valeur_nette_debut = article.valeur_acquisition - amortissement_cumule_debut
            amortissement_annuel = valeur_nette_debut * (article.taux_amortissement / Decimal(100))
            taux_applique = article.taux_amortissement
        
        else:
            raise ValueError(f"Méthode '{article.methode_amortissement}' non supportée")
        
        # Calcul final
        amortissement_cumule_fin = amortissement_cumule_debut + amortissement_annuel
        valeur_nette_comptable = article.valeur_acquisition - amortissement_cumule_fin
        
        # Vérifier si totalement amorti
        if valeur_nette_comptable <= valeur_residuelle:
            amortissement_annuel = article.valeur_acquisition - amortissement_cumule_debut - valeur_residuelle
            amortissement_cumule_fin = article.valeur_acquisition - valeur_residuelle
            valeur_nette_comptable = valeur_residuelle
            totalement_amorti = True
        else:
            totalement_amorti = False
        
        # Créer l'enregistrement
        amortissement = Amortissement(
            article_id=article_id,
            annee=annee,
            periode=str(annee),
            valeur_brute=article.valeur_acquisition,
            amortissement_cumule_debut=amortissement_cumule_debut,
            amortissement_periode=amortissement_annuel,
            amortissement_cumule_fin=amortissement_cumule_fin,
            valeur_nette_comptable=valeur_nette_comptable,
            taux_applique=taux_applique,
            methode=article.methode_amortissement,
            totalement_amorti=totalement_amorti
        )
        
        session.add(amortissement)
        session.commit()
        session.refresh(amortissement)
        
        return amortissement
    
    @staticmethod
    def get_plan_amortissement(
        session: Session,
        article_id: int
    ) -> List[Dict]:
        """Génère le plan d'amortissement complet"""
        
        article = session.get(Article, article_id)
        if not article:
            raise ValueError("Article introuvable")
        
        if not article.est_amortissable:
            raise ValueError("L'article n'est pas amortissable")
        
        # Récupérer les amortissements déjà calculés
        amortissements_calcules = session.exec(
            select(Amortissement)
            .where(Amortissement.article_id == article_id)
            .order_by(Amortissement.annee)
        ).all()
        
        plan = []
        
        # Ajouter les années calculées
        for amort in amortissements_calcules:
            plan.append({
                "annee": amort.annee,
                "valeur_brute": float(amort.valeur_brute),
                "amortissement_periode": float(amort.amortissement_periode),
                "amortissement_cumule": float(amort.amortissement_cumule_fin),
                "valeur_nette_comptable": float(amort.valeur_nette_comptable),
                "calcule": True,
                "methode": amort.methode
            })
        
        # Ajouter les années prévisionnelles
        annee_debut = article.date_acquisition.year
        derniere_annee_calculee = amortissements_calcules[-1].annee if amortissements_calcules else annee_debut - 1
        amort_cumule = amortissements_calcules[-1].amortissement_cumule_fin if amortissements_calcules else Decimal(0)
        
        for i in range(int(derniere_annee_calculee - annee_debut + 1), article.duree_amortissement_annees):
            annee = annee_debut + i
            
            if article.methode_amortissement == "LINEAIRE":
                amort_annuel = StockService.calculer_amortissement_lineaire(
                    article.valeur_acquisition,
                    article.duree_amortissement_annees,
                    article.valeur_residuelle or Decimal(0)
                )
            else:  # DEGRESSIF
                valeur_nette = article.valeur_acquisition - amort_cumule
                amort_annuel = valeur_nette * (article.taux_amortissement / Decimal(100))
            
            amort_cumule += amort_annuel
            vnc = article.valeur_acquisition - amort_cumule
            
            plan.append({
                "annee": annee,
                "valeur_brute": float(article.valeur_acquisition),
                "amortissement_periode": float(amort_annuel),
                "amortissement_cumule": float(amort_cumule),
                "valeur_nette_comptable": float(vnc),
                "calcule": False,
                "methode": article.methode_amortissement
            })
            
            if vnc <= (article.valeur_residuelle or Decimal(0)):
                break
        
        return plan
```

---

**Ce document est encore incomplet. Continuons avec la suite pour couvrir tous les modules...**

**Voulez-vous que je continue avec :**
- Module 5 : API/Endpoints (routes FastAPI)
- Module 6 : Templates (HTML/Jinja2)
- Module 7 : Static (CSS/JS)

Ou préférez-vous que je finalise ce document maintenant et créons un 4ème document pour les modules restants ?

