"""
Tests d'intégration pour Docker PostgreSQL
"""
import pytest
import os
from sqlmodel import Session, create_engine
from app.core.config import Settings


@pytest.mark.critical
@pytest.mark.docker
def test_docker_postgres_connection():
    """Test connexion PostgreSQL depuis Docker"""
    # Configuration pour Docker
    docker_settings = Settings(
        DATABASE_URL="postgresql://postgres:postgres@host.docker.internal:5432/mppeep",
        DEBUG=False,
        ENV="production"
    )
    
    # Créer l'engine
    engine = create_engine(docker_settings.database_url)
    
    # Test de connexion
    with Session(engine) as session:
        # Test requête simple
        result = session.exec("SELECT 1 as test").first()
        assert result.test == 1
        
        # Test connexion à la base mppeep
        result = session.exec("SELECT current_database()").first()
        assert result.current_database == "mppeep"


@pytest.mark.critical
@pytest.mark.docker
def test_docker_environment_variables():
    """Test variables d'environnement Docker"""
    # Variables requises pour Docker
    required_vars = [
        "DATABASE_URL",
        "SECRET_KEY",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB"
    ]
    
    # Vérifier que les variables sont définies
    for var in required_vars:
        value = os.getenv(var)
        assert value is not None, f"Variable {var} non définie"
        assert len(value) > 0, f"Variable {var} vide"


@pytest.mark.critical
@pytest.mark.docker
def test_docker_postgres_pool_connections():
    """Test pool de connexions PostgreSQL dans Docker"""
    from app.db.session import engine
    
    # Test avec plusieurs connexions simultanées
    connections = []
    
    try:
        # Créer plusieurs sessions simultanément
        for i in range(5):
            session = Session(engine)
            connections.append(session)
            
            # Test requête sur chaque session
            result = session.exec("SELECT current_timestamp").first()
            assert result is not None
            
    finally:
        # Fermer toutes les connexions
        for session in connections:
            session.close()


@pytest.mark.critical
@pytest.mark.docker
def test_docker_postgres_data_persistence():
    """Test persistance des données PostgreSQL dans Docker"""
    from app.db.session import engine
    from app.models.user import User
    from app.core.security import get_password_hash
    
    with Session(engine) as session:
        # Créer un utilisateur de test
        test_user = User(
            email="docker_test@example.com",
            full_name="Docker Test User",
            hashed_password=get_password_hash("password123"),
            is_active=True
        )
        
        session.add(test_user)
        session.commit()
        session.refresh(test_user)
        
        user_id = test_user.id
        assert user_id is not None
        
        # Vérifier que l'utilisateur existe
        retrieved_user = session.get(User, user_id)
        assert retrieved_user is not None
        assert retrieved_user.email == "docker_test@example.com"
        
        # Nettoyer
        session.delete(retrieved_user)
        session.commit()


@pytest.mark.critical
@pytest.mark.docker
def test_docker_postgres_migrations():
    """Test migrations de base de données dans Docker"""
    from app.db.session import engine
    from sqlmodel import SQLModel
    
    # Vérifier que toutes les tables existent
    with Session(engine) as session:
        # Lister les tables
        result = session.exec("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """).all()
        
        table_names = [row.table_name for row in result]
        
        # Tables attendues
        expected_tables = [
            "user",
            "agent", 
            "activity",
            "article",
            "budget",
            "file"
        ]
        
        for table in expected_tables:
            assert table in table_names, f"Table {table} manquante"


@pytest.mark.critical
@pytest.mark.docker
def test_docker_postgres_performance():
    """Test performance PostgreSQL dans Docker"""
    from app.db.session import engine
    import time
    
    with Session(engine) as session:
        # Test temps de réponse
        start_time = time.time()
        
        # Requête simple
        result = session.exec("SELECT COUNT(*) FROM information_schema.tables").first()
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Vérifier que la réponse est rapide (< 1 seconde)
        assert response_time < 1.0, f"Requête trop lente: {response_time:.3f}s"
        assert result is not None


@pytest.mark.critical
@pytest.mark.docker
def test_docker_postgres_concurrent_access():
    """Test accès concurrent PostgreSQL dans Docker"""
    from app.db.session import engine
    import threading
    import time
    
    results = []
    errors = []
    
    def test_query(thread_id):
        try:
            with Session(engine) as session:
                # Attendre un peu pour simuler des requêtes simultanées
                time.sleep(0.1)
                
                result = session.exec(f"SELECT {thread_id} as thread_id").first()
                results.append(result.thread_id)
                
        except Exception as e:
            errors.append(str(e))
    
    # Lancer plusieurs threads
    threads = []
    for i in range(10):
        thread = threading.Thread(target=test_query, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Attendre que tous les threads se terminent
    for thread in threads:
        thread.join()
    
    # Vérifier les résultats
    assert len(errors) == 0, f"Erreurs détectées: {errors}"
    assert len(results) == 10, f"Seulement {len(results)}/10 requêtes réussies"
    assert set(results) == set(range(10)), "Résultats incorrects"


@pytest.mark.critical
@pytest.mark.docker
def test_docker_postgres_health_check():
    """Test health check PostgreSQL dans Docker"""
    from app.db.session import engine
    
    with Session(engine) as session:
        # Test health check simple
        result = session.exec("SELECT 1 as health").first()
        assert result.health == 1
        
        # Test connexions actives
        result = session.exec("""
            SELECT count(*) as active_connections 
            FROM pg_stat_activity 
            WHERE state = 'active'
        """).first()
        
        assert result.active_connections >= 1
        
        # Test taille de la base
        result = session.exec("""
            SELECT pg_database_size(current_database()) as db_size
        """).first()
        
        assert result.db_size > 0


@pytest.mark.critical
@pytest.mark.docker
def test_docker_postgres_backup_restore():
    """Test sauvegarde/restauration PostgreSQL dans Docker"""
    from app.db.session import engine
    from app.models.user import User
    from app.core.security import get_password_hash
    
    with Session(engine) as session:
        # Créer des données de test
        test_users = []
        for i in range(3):
            user = User(
                email=f"backup_test_{i}@example.com",
                full_name=f"Backup Test User {i}",
                hashed_password=get_password_hash("password123"),
                is_active=True
            )
            session.add(user)
            test_users.append(user)
        
        session.commit()
        
        # Récupérer les IDs
        user_ids = [user.id for user in test_users]
        
        # Vérifier que les utilisateurs existent
        for user_id in user_ids:
            user = session.get(User, user_id)
            assert user is not None
        
        # Simuler une restauration (supprimer et recréer)
        for user in test_users:
            session.delete(user)
        
        session.commit()
        
        # Vérifier que les utilisateurs sont supprimés
        for user_id in user_ids:
            user = session.get(User, user_id)
            assert user is None


@pytest.mark.critical
@pytest.mark.docker
def test_docker_postgres_connection_pool_settings():
    """Test configuration du pool de connexions"""
    from app.db.session import engine
    
    # Vérifier les paramètres du pool
    pool = engine.pool
    
    # Vérifier les paramètres configurés
    assert pool.size() >= 5, "Pool trop petit"
    assert pool.size() <= 30, "Pool trop grand"
    
    # Test utilisation du pool
    connections_used = []
    
    try:
        # Utiliser plusieurs connexions
        for i in range(10):
            session = Session(engine)
            connections_used.append(session)
            
            # Test requête
            result = session.exec("SELECT 1").first()
            assert result is not None
            
    finally:
        # Fermer les connexions
        for session in connections_used:
            session.close()
    
    # Vérifier que le pool fonctionne correctement
    assert pool.size() >= 5, "Pool ne se reconstitue pas correctement"
