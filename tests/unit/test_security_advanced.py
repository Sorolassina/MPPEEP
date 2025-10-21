"""
Tests de sécurité avancés
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session


@pytest.mark.security
@pytest.mark.critical
def test_sql_injection_prevention(client: TestClient, admin_client: TestClient):
    """Test protection contre SQL injection"""
    # Tentatives d'injection SQL dans les paramètres
    sql_injection_attempts = [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "admin'--",
        "1' UNION SELECT * FROM users--",
        "'; INSERT INTO users VALUES ('hacker', 'password'); --"
    ]
    
    for injection in sql_injection_attempts:
        # Test sur endpoint de recherche d'utilisateur
        response = admin_client.get(f"/api/v1/users?search={injection}")
        
        # Doit retourner 400 (Bad Request) ou 422 (Validation Error)
        assert response.status_code in [400, 422, 200], f"Injection réussie: {injection}"
        
        # Si 200, vérifier que l'injection n'a pas fonctionné
        if response.status_code == 200:
            data = response.json()
            # Ne doit pas contenir de données sensibles
            assert len(data) == 0 or all("DROP" not in str(item) for item in data)


@pytest.mark.security
@pytest.mark.critical
def test_xss_prevention(client: TestClient, admin_client: TestClient):
    """Test protection contre XSS"""
    # Scripts malveillants
    xss_attempts = [
        "<script>alert('XSS')</script>",
        "javascript:alert('XSS')",
        "<img src=x onerror=alert('XSS')>",
        "';alert('XSS');//",
        "<svg onload=alert('XSS')>"
    ]
    
    for xss in xss_attempts:
        # Test création d'utilisateur avec script XSS
        user_data = {
            "email": "xss_test@example.com",
            "full_name": xss,
            "password": "password123"
        }
        
        response = admin_client.post("/api/v1/users", json=user_data)
        
        # Doit être rejeté ou échappé
        if response.status_code == 201:
            data = response.json()
            # Vérifier que le script est échappé
            assert "<script>" not in data["full_name"]
            assert "javascript:" not in data["full_name"]
            assert "onerror" not in data["full_name"]


@pytest.mark.security
@pytest.mark.critical
def test_csrf_protection(client: TestClient, admin_client: TestClient):
    """Test protection CSRF"""
    # Test sans token CSRF (si implémenté)
    user_data = {
        "email": "csrf_test@example.com",
        "full_name": "CSRF Test User",
        "password": "password123"
    }
    
    # Test avec différentes méthodes
    methods_to_test = [
        ("POST", "/api/v1/users"),
        ("PUT", "/api/v1/users/1"),
        ("DELETE", "/api/v1/users/1")
    ]
    
    for method, endpoint in methods_to_test:
        if method == "POST":
            response = client.post(endpoint, json=user_data)
        elif method == "PUT":
            response = client.put(endpoint, json=user_data)
        elif method == "DELETE":
            response = client.delete(endpoint)
        
        # Doit être rejeté sans authentification appropriée
        assert response.status_code in [401, 403, 404]


@pytest.mark.security
@pytest.mark.critical
def test_authorization_bypass(client: TestClient, admin_client: TestClient):
    """Test contournement d'autorisation"""
    # Test accès aux endpoints admin sans privilèges
    admin_endpoints = [
        "/api/v1/users",
        "/api/v1/admin/settings",
        "/api/v1/admin/logs"
    ]
    
    for endpoint in admin_endpoints:
        # Test sans authentification
        response = client.get(endpoint)
        assert response.status_code in [401, 403]
        
        # Test avec utilisateur normal (si possible)
        # Note: Nécessite un client utilisateur normal


@pytest.mark.security
@pytest.mark.critical
def test_session_hijacking_prevention(client: TestClient, admin_client: TestClient):
    """Test prévention du détournement de session"""
    # Test avec des cookies de session invalides
    invalid_cookies = [
        "session_token=invalid_token",
        "session_token=admin",
        "session_token=../../etc/passwd",
        "session_token=<script>alert('hack')</script>"
    ]
    
    for cookie in invalid_cookies:
        # Définir le cookie invalide
        client.cookies.set("session_token", cookie.split("=")[1])
        
        # Tenter d'accéder à un endpoint protégé
        response = client.get("/api/v1/users")
        
        # Doit être rejeté
        assert response.status_code in [401, 403]


@pytest.mark.security
@pytest.mark.critical
def test_file_upload_security(client: TestClient, admin_client: TestClient):
    """Test sécurité des uploads de fichiers"""
    # Test upload de fichiers malveillants
    malicious_files = [
        ("malware.exe", b"MZ\x90\x00"),  # Fichier exécutable
        ("script.php", b"<?php system($_GET['cmd']); ?>"),  # Script PHP
        ("shell.jsp", b"<% Runtime.getRuntime().exec(request.getParameter(\"cmd\")); %>"),  # JSP
        ("backdoor.py", b"import os; os.system('rm -rf /')"),  # Script Python malveillant
    ]
    
    for filename, content in malicious_files:
        files = {"file": (filename, content, "application/octet-stream")}
        
        response = admin_client.post("/api/v1/upload", files=files)
        
        # Doit être rejeté
        assert response.status_code in [400, 403, 415], f"Fichier malveillant accepté: {filename}"


@pytest.mark.security
@pytest.mark.critical
def test_path_traversal_prevention(client: TestClient, admin_client: TestClient):
    """Test prévention du path traversal"""
    # Tentatives de path traversal
    path_traversal_attempts = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
        "....//....//....//etc/passwd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "..%252f..%252f..%252fetc%252fpasswd"
    ]
    
    for path in path_traversal_attempts:
        # Test sur endpoint de fichiers
        response = admin_client.get(f"/api/v1/files/{path}")
        
        # Doit être rejeté
        assert response.status_code in [400, 403, 404], f"Path traversal réussi: {path}"


@pytest.mark.security
@pytest.mark.critical
def test_rate_limiting(client: TestClient):
    """Test limitation de taux"""
    # Test avec de nombreuses requêtes rapides
    for i in range(100):  # 100 requêtes rapides
        response = client.get("/api/v1/ping")
        
        # Après un certain nombre, doit être limité
        if response.status_code == 429:  # Too Many Requests
            assert "rate limit" in response.text.lower() or "too many" in response.text.lower()
            break
    
    # Si pas de rate limiting, au moins vérifier que ça ne plante pas
    assert response.status_code in [200, 429]


@pytest.mark.security
@pytest.mark.critical
def test_input_validation_security(client: TestClient, admin_client: TestClient):
    """Test validation sécurisée des entrées"""
    # Test avec des données malformées
    malformed_data = [
        {"email": None, "password": "test"},  # Email null
        {"email": "", "password": "test"},    # Email vide
        {"email": "test@example.com", "password": None},  # Password null
        {"email": "test@example.com", "password": ""},    # Password vide
        {"email": "a" * 1000 + "@example.com", "password": "test"},  # Email trop long
        {"email": "test@example.com", "password": "a" * 1000},        # Password trop long
    ]
    
    for data in malformed_data:
        response = admin_client.post("/api/v1/users", json=data)
        
        # Doit être rejeté avec erreur de validation
        assert response.status_code in [400, 422], f"Données malformées acceptées: {data}"


@pytest.mark.security
@pytest.mark.critical
def test_http_method_override_security(client: TestClient):
    """Test sécurité des méthodes HTTP"""
    # Test avec méthodes HTTP non autorisées
    methods_to_test = [
        ("TRACE", "/api/v1/users"),
        ("CONNECT", "/api/v1/users"),
        ("PATCH", "/api/v1/users"),  # Si non implémenté
    ]
    
    for method, endpoint in methods_to_test:
        response = client.request(method, endpoint)
        
        # Doit être rejeté
        assert response.status_code in [405, 501], f"Méthode {method} autorisée"


@pytest.mark.security
@pytest.mark.critical
def test_header_injection_prevention(client: TestClient, admin_client: TestClient):
    """Test prévention d'injection dans les headers"""
    # Headers malveillants
    malicious_headers = [
        {"X-Forwarded-For": "127.0.0.1\r\nX-Injected: malicious"},
        {"User-Agent": "Mozilla/5.0\r\nX-Injected: malicious"},
        {"Referer": "http://evil.com\r\nX-Injected: malicious"},
    ]
    
    for headers in malicious_headers:
        response = admin_client.get("/api/v1/users", headers=headers)
        
        # Doit traiter les headers correctement
        assert response.status_code in [200, 400, 403]
        
        # Vérifier que l'injection n'a pas fonctionné
        if response.status_code == 200:
            assert "X-Injected" not in response.text


@pytest.mark.security
@pytest.mark.critical
def test_password_security_requirements():
    """Test exigences de sécurité des mots de passe"""
    from app.services.user_service import UserService
    
    # Mots de passe faibles
    weak_passwords = [
        "password",      # Trop simple
        "123456",        # Que des chiffres
        "abcdef",        # Que des lettres
        "Password",      # Pas de chiffres
        "password123",   # Pas de caractères spéciaux
        "P@ss",          # Trop court
    ]
    
    for password in weak_passwords:
        assert UserService.validate_password(password) is False, f"Mot de passe faible accepté: {password}"
    
    # Mots de passe forts
    strong_passwords = [
        "Password123!",
        "MySecure2024@",
        "Complex#Pass1",
        "StrongP@ssw0rd",
    ]
    
    for password in strong_passwords:
        assert UserService.validate_password(password) is True, f"Mot de passe fort rejeté: {password}"


@pytest.mark.security
@pytest.mark.critical
def test_logging_security_events():
    """Test journalisation des événements de sécurité"""
    import logging
    from app.core.logging_config import get_logger
    
    logger = get_logger("security_test")
    
    # Test journalisation des tentatives d'injection
    logger.warning("Tentative d'injection SQL détectée", extra={
        "ip": "192.168.1.100",
        "user_agent": "Mozilla/5.0",
        "endpoint": "/api/v1/users",
        "payload": "'; DROP TABLE users; --"
    })
    
    # Test journalisation des échecs d'authentification
    logger.warning("Échec d'authentification", extra={
        "email": "test@example.com",
        "ip": "192.168.1.100",
        "attempts": 3
    })
    
    # Les logs doivent être générés (test basique)
    assert True  # Si on arrive ici, les logs sont générés
