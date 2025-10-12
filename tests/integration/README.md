# 🔗 Tests d'Intégration

## 🤔 Pourquoi "Intégration" ?

Le mot "**intégration**" signifie "**assembler plusieurs pièces ensemble**". On teste comment les différentes parties de l'application **collaborent**.

### 🏗️ Analogie Simple

Imaginez que vous construisez une maison :

- ⚪ **Test Unitaire** = Vérifier qu'une brique est solide
- ✅ **Test d'Intégration** = Vérifier que les briques assemblées forment un mur solide
- ⚠️ **Pas encore** = Vérifier que toute la maison tient debout (c'est le test fonctionnel)

**Exemples concrets dans notre application :**

| Ce qu'on teste | Ce qui est impliqué |
|----------------|---------------------|
| Login API | Endpoint HTTP + Base de données + Hashing |
| Créer un utilisateur | API + Validation + Stockage DB |
| Récupérer des users | API + DB + Transformation JSON |

---

## 🎯 Objectif des Tests d'Intégration

### Pour quoi faire ?

1. **Vérifier que l'API fonctionne correctement**
   - Est-ce que `/api/v1/login` retourne le bon code HTTP ?
   - Est-ce que les données sont bien sauvegardées en base ?
   
2. **Tester la communication entre composants**
   - L'API appelle bien la base de données ?
   - Les données sont bien transformées en JSON ?
   
3. **Simuler un utilisateur qui appelle l'API**
   - Comme si on utilisait Postman ou curl

### 📊 Avantages

✅ **Réaliste** - Teste comment les utilisateurs interagiront réellement  
✅ **Détecte les bugs d'intégration** - Quand 2 composants ne communiquent pas bien  
✅ **Rapide quand même** - Plus lent qu'unitaire, mais reste < 100ms  

---

## ⚙️ Comment ça Fonctionne ?

### Principe Simple

```
1. Créer un "faux" client HTTP
2. Envoyer une requête à l'API (GET, POST, etc.)
3. Vérifier la réponse (code HTTP, données)
```

### 🎬 Exemple Concret

**Test : Vérifier qu'on peut se connecter**

```python
def test_login_success(client: TestClient, test_user: User):
    # 1. PRÉPARATION
    # test_user existe déjà en base (créé par la fixture)
    
    # 2. ACTION - Envoyer une requête POST
    response = client.post("/api/v1/login", data={
        "username": "test@example.com",
        "password": "testpassword123"
    })
    
    # 3. VÉRIFICATION
    assert response.status_code == 303  # Redirection
    assert "/dashboard" in response.headers["location"]
```

**Ce qui se passe vraiment :**
1. Un utilisateur test est créé en base de données
2. On envoie une requête HTTP POST comme si on était un navigateur
3. L'API vérifie le mot de passe, crée une session, redirige
4. On vérifie que la réponse est correcte

---

## 🚀 Lancer les Tests d'Intégration

### 📝 Commandes Simples

```bash
# Tous les tests d'intégration
pytest tests/integration/

# Avec plus de détails
pytest tests/integration/ -v

# Un seul fichier
pytest tests/integration/test_auth_api.py

# Tests de login seulement
pytest tests/integration/ -k "login"
```

### 🎨 Comprendre les Résultats

**✅ Succès**
```
tests/integration/test_auth_api.py::test_login_success PASSED [100%]
✓ L'API de login fonctionne !
```

**❌ Échec**
```
tests/integration/test_auth_api.py::test_login_success FAILED
AssertionError: assert 200 == 303
✗ L'API retourne 200 au lieu de 303 (pas de redirection)
```

---

## 📂 Fichiers de Tests d'Intégration

### `test_auth_api.py` - API d'Authentification

**Ce qu'on teste :**
- 🔐 Connexion (login)
- 📧 Mot de passe oublié
- ✅ Vérification de code
- 🔒 Comptes désactivés

**Scénarios testés :**

| Test | Scénario | Résultat Attendu |
|------|----------|------------------|
| `test_login_success` | Connexion avec bon mdp | Redirection vers /dashboard |
| `test_login_wrong_password` | Mauvais mot de passe | Message d'erreur |
| `test_login_user_not_found` | Email inexistant | Message d'erreur |
| `test_login_inactive_user` | Compte désactivé | Message "compte désactivé" |
| `test_forgot_password_submit` | Demande récupération | Redirection vers vérification |

**Exemple :**
```python
def test_login_wrong_password(client, test_user):
    response = client.post("/api/v1/login", data={
        "username": "test@example.com",
        "password": "MAUVAIS_MOT_DE_PASSE"
    })
    
    assert response.status_code == 200
    assert b"incorrect" in response.content.lower()
```

---

### `test_users_api.py` - API Utilisateurs (CRUD)

**Ce qu'on teste :**
- 📋 Lister les utilisateurs (GET /users/)
- 👤 Récupérer un utilisateur (GET /users/{id})
- ➕ Créer un utilisateur (POST /users/)
- ❌ Cas d'erreur (email dupliqué, user introuvable)

**CRUD = Create, Read, Update, Delete** (Créer, Lire, Modifier, Supprimer)

**Scénarios testés :**

```python
# CREATE - Créer
def test_create_user(client):
    response = client.post("/api/v1/users/", json={
        "email": "nouveau@example.com",
        "full_name": "Nouveau User"
    })
    assert response.status_code == 200

# READ - Lire
def test_get_user_by_id(client, test_user):
    response = client.get(f"/api/v1/users/{test_user.id}")
    assert response.status_code == 200
    
# Cas d'erreur
def test_get_user_not_found(client):
    response = client.get("/api/v1/users/99999")
    assert response.status_code == 404  # Not Found
```

---

### `test_health.py` - Santé de l'Application

**Ce qu'on teste :**
- 🏥 Health check (ping/pong)
- 🏠 Redirection de la racine
- 📄 Pages accessibles

**Pourquoi c'est important :**  
Ces endpoints sont utilisés pour vérifier que l'application fonctionne (monitoring).

**Exemples :**
```python
def test_ping(client):
    response = client.get("/api/v1/ping")
    assert response.status_code == 200
    assert response.json() == {"ping": "pong"}

def test_root_redirect(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert "/login" in response.headers["location"]
```

---

## 💡 Conseils pour Comprendre

### 🔍 Différence avec les Tests Unitaires

| Aspect | Test Unitaire | Test d'Intégration |
|--------|---------------|-------------------|
| **Quoi** | Une fonction | Plusieurs composants |
| **Comment** | Appel direct | Requête HTTP |
| **Base de données** | En mémoire isolée | En mémoire partagée |
| **Vitesse** | ⚡⚡⚡ Très rapide | ⚡⚡ Rapide |
| **Exemple** | `verify_password()` | `POST /api/v1/login` |

### 🎯 Ce qu'on teste

✅ **Routes HTTP** - Est-ce que `/api/v1/users/` existe ?  
✅ **Codes de statut** - 200 OK, 404 Not Found, 303 Redirect  
✅ **Réponses JSON** - Les données retournées sont correctes ?  
✅ **Base de données** - Les données sont sauvegardées ?  

### 🔧 Outils Utilisés

**TestClient de FastAPI** - Simule un navigateur
```python
client = TestClient(app)
response = client.get("/api/v1/ping")
# Comme faire : curl http://localhost:8000/api/v1/ping
```

**Fixtures pytest** - Données de test pré-créées
```python
def test_avec_user(client, test_user):
    # test_user existe déjà !
    # Pas besoin de le créer à chaque fois
```

---

## 🆘 Problèmes Courants

### Test qui échoue : "404 Not Found"

```
AssertionError: assert 404 == 200
```

**Causes possibles :**
1. ❌ La route n'existe pas
2. ❌ L'URL est mal écrite (`/api/v1/user` au lieu de `/api/v1/users`)
3. ❌ Le router n'est pas inclus dans `main.py`

**Solution :**
```bash
# Lister toutes les routes disponibles
pytest tests/integration/test_health.py::test_ping -vvs
```

### Test qui échoue : "500 Internal Server Error"

```
AssertionError: assert 500 == 200
```

**Causes possibles :**
1. ❌ Erreur dans le code de l'endpoint
2. ❌ Problème avec la base de données
3. ❌ Données manquantes

**Solution :**
```bash
# Voir les logs détaillés
pytest tests/integration/test_auth_api.py::test_login_success -vvs
```

---

## 📊 Statistiques Actuelles

| Fichier | Tests | Temps Moyen | Ce qui est testé |
|---------|-------|-------------|------------------|
| `test_auth_api.py` | 8 tests | ~50ms | Login, récupération mdp |
| `test_users_api.py` | 5 tests | ~30ms | CRUD utilisateurs |
| `test_health.py` | 3 tests | ~10ms | Health checks |

**Total : 16 tests d'intégration** ⚡

---

## 🎓 Pour Aller Plus Loin

### Questions Fréquentes

**Q: Pourquoi utiliser une base de données en mémoire ?**  
R: Pour que les tests soient rapides et isolés. Chaque test repart de zéro.

**Q: Est-ce que ces tests appellent vraiment l'API ?**  
R: Oui ! Mais c'est une "fausse" API en mémoire, pas le vrai serveur.

**Q: Quelle est la différence avec Postman ?**  
R: Postman teste manuellement, pytest teste automatiquement à chaque modification.

### Codes HTTP Courants

| Code | Signification | Quand ça arrive |
|------|---------------|----------------|
| 200 | OK | Requête réussie |
| 303 | Redirect | Redirection (après login) |
| 400 | Bad Request | Données invalides |
| 404 | Not Found | Route inexistante |
| 422 | Unprocessable | Validation échouée |
| 500 | Server Error | Bug dans le code |

### Méthodes HTTP

| Méthode | Usage | Exemple |
|---------|-------|---------|
| **GET** | Récupérer | `GET /users/` - Liste users |
| **POST** | Créer | `POST /users/` - Créer user |
| **PUT** | Modifier | `PUT /users/1` - Modifier user 1 |
| **DELETE** | Supprimer | `DELETE /users/1` - Supprimer user 1 |

---

## ✨ En Résumé

| Aspect | Explication Simple |
|--------|-------------------|
| **Nom** | "Intégration" = assembler plusieurs pièces |
| **Objectif** | Vérifier que l'API fonctionne avec la DB |
| **Vitesse** | ⚡⚡ Rapide (~50ms) |
| **Quand** | Après chaque modification d'endpoint |
| **Commande** | `pytest tests/integration/` |

**💡 Pensez aux tests d'intégration comme des "tests d'API" - on vérifie que les endpoints HTTP répondent correctement !**

