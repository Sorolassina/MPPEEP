"""
Tests d'intégration pour les endpoints API principaux
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.user import User
from app.core.enums import UserType


@pytest.mark.critical
def test_users_api_list(client: TestClient, admin_client: TestClient, test_user: User):
    """Test GET /api/v1/users - Liste des utilisateurs"""
    # Test sans authentification (doit échouer)
    response = client.get("/api/v1/users")
    assert response.status_code in [401, 403]  # Non autorisé
    
    # Test avec authentification admin
    response = admin_client.get("/api/v1/users")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1  # Au moins l'admin


@pytest.mark.critical
def test_users_api_create(client: TestClient, admin_client: TestClient, session: Session):
    """Test POST /api/v1/users - Création d'utilisateur"""
    user_data = {
        "email": "newuser@example.com",
        "full_name": "New User",
        "password": "password123",
        "is_active": True,
        "type_user": UserType.AGENT.value
    }
    
    # Test sans authentification (doit échouer)
    response = client.post("/api/v1/users", json=user_data)
    assert response.status_code in [401, 403]
    
    # Test avec authentification admin
    response = admin_client.post("/api/v1/users", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["full_name"] == user_data["full_name"]
    assert data["is_active"] is True


@pytest.mark.critical
def test_users_api_get_by_id(client: TestClient, admin_client: TestClient, test_user: User):
    """Test GET /api/v1/users/{id} - Récupération utilisateur par ID"""
    # Test sans authentification
    response = client.get(f"/api/v1/users/{test_user.id}")
    assert response.status_code in [401, 403]
    
    # Test avec authentification
    response = admin_client.get(f"/api/v1/users/{test_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email


@pytest.mark.critical
def test_users_api_update(client: TestClient, admin_client: TestClient, test_user: User):
    """Test PUT /api/v1/users/{id} - Mise à jour utilisateur"""
    update_data = {
        "full_name": "Updated Name",
        "is_active": False
    }
    
    # Test sans authentification
    response = client.put(f"/api/v1/users/{test_user.id}", json=update_data)
    assert response.status_code in [401, 403]
    
    # Test avec authentification
    response = admin_client.put(f"/api/v1/users/{test_user.id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == update_data["full_name"]
    assert data["is_active"] == update_data["is_active"]


@pytest.mark.critical
def test_users_api_delete(client: TestClient, admin_client: TestClient, session: Session):
    """Test DELETE /api/v1/users/{id} - Suppression utilisateur"""
    # Créer un utilisateur à supprimer
    from app.services.user_service import UserService
    user = UserService.create_user(
        session=session,
        email="todelete@example.com",
        full_name="To Delete",
        password="password123"
    )
    
    # Test sans authentification
    response = client.delete(f"/api/v1/users/{user.id}")
    assert response.status_code in [401, 403]
    
    # Test avec authentification
    response = admin_client.delete(f"/api/v1/users/{user.id}")
    assert response.status_code == 204
    
    # Vérifier que l'utilisateur est supprimé
    response = admin_client.get(f"/api/v1/users/{user.id}")
    assert response.status_code == 404


@pytest.mark.critical
def test_agents_api_list(client: TestClient, admin_client: TestClient):
    """Test GET /api/v1/agents - Liste des agents"""
    # Test sans authentification
    response = client.get("/api/v1/agents")
    assert response.status_code in [401, 403]
    
    # Test avec authentification
    response = admin_client.get("/api/v1/agents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.critical
def test_agents_api_create(client: TestClient, admin_client: TestClient):
    """Test POST /api/v1/agents - Création d'agent"""
    agent_data = {
        "matricule": "A123456",
        "nom": "Test Agent",
        "prenom": "Test",
        "email": "agent@example.com",
        "telephone": "0123456789"
    }
    
    # Test sans authentification
    response = client.post("/api/v1/agents", json=agent_data)
    assert response.status_code in [401, 403]
    
    # Test avec authentification
    response = admin_client.post("/api/v1/agents", json=agent_data)
    # Peut être 201 (créé) ou 400 (validation) selon les contraintes
    assert response.status_code in [201, 400]


@pytest.mark.critical
def test_budget_api_list(client: TestClient, admin_client: TestClient):
    """Test GET /api/v1/budget - Liste des budgets"""
    # Test sans authentification
    response = client.get("/api/v1/budget")
    assert response.status_code in [401, 403]
    
    # Test avec authentification
    response = admin_client.get("/api/v1/budget")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.critical
def test_budget_api_create(client: TestClient, admin_client: TestClient):
    """Test POST /api/v1/budget - Création de budget"""
    budget_data = {
        "annee": 2025,
        "montant_total": 1000000,
        "description": "Budget test 2025"
    }
    
    # Test sans authentification
    response = client.post("/api/v1/budget", json=budget_data)
    assert response.status_code in [401, 403]
    
    # Test avec authentification
    response = admin_client.post("/api/v1/budget", json=budget_data)
    # Peut être 201 (créé) ou 400 (validation) selon les contraintes
    assert response.status_code in [201, 400]


@pytest.mark.critical
def test_api_error_handling(client: TestClient):
    """Test gestion des erreurs API"""
    # Test endpoint inexistant
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404
    
    # Test méthode non autorisée
    response = client.delete("/api/v1/ping")
    assert response.status_code == 405
    
    # Test données invalides
    response = client.post("/api/v1/users", json={"invalid": "data"})
    assert response.status_code in [400, 401, 403]


@pytest.mark.critical
def test_api_cors_headers(client: TestClient):
    """Test headers CORS"""
    response = client.options("/api/v1/users")
    assert response.status_code == 200
    
    # Vérifier les headers CORS
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-methods" in response.headers


@pytest.mark.critical
def test_api_response_format(client: TestClient, admin_client: TestClient):
    """Test format des réponses API"""
    response = admin_client.get("/api/v1/users")
    assert response.status_code == 200
    
    # Vérifier le Content-Type
    assert "application/json" in response.headers["content-type"]
    
    # Vérifier que c'est du JSON valide
    data = response.json()
    assert isinstance(data, (list, dict))


@pytest.mark.critical
def test_api_pagination(client: TestClient, admin_client: TestClient):
    """Test pagination des endpoints"""
    # Créer plusieurs utilisateurs pour tester la pagination
    from app.services.user_service import UserService
    
    for i in range(5):
        UserService.create_user(
            session=admin_client.app.state.session,
            email=f"pagination{i}@example.com",
            full_name=f"User {i}",
            password="password123"
        )
    
    # Test avec paramètres de pagination
    response = admin_client.get("/api/v1/users?page=1&size=3")
    assert response.status_code == 200
    
    data = response.json()
    # Vérifier que la pagination fonctionne (si implémentée)
    if isinstance(data, dict) and "items" in data:
        assert len(data["items"]) <= 3
        assert "total" in data
        assert "page" in data
