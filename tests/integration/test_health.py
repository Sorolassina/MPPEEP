"""
Tests d'intégration pour les endpoints de santé
"""
from fastapi.testclient import TestClient


def test_ping(client: TestClient):
    """Test l'endpoint ping"""
    response = client.get("/api/v1/ping")
    
    assert response.status_code == 200
    assert response.json() == {"ping": "pong"}


def test_root_redirect(client: TestClient):
    """Test que la racine redirige vers login"""
    response = client.get("/", follow_redirects=False)
    
    assert response.status_code == 303
    assert "/login" in response.headers["location"]


def test_accueil_page(client: TestClient):
    """Test l'accès à la page d'accueil"""
    response = client.get("/accueil")
    
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

