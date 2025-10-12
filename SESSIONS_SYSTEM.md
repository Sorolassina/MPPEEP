# 🔐 Système de Sessions Multi-Device

## 🎯 Vue d'ensemble

Le système de sessions permet aux utilisateurs de se connecter depuis **plusieurs appareils simultanément** (ordinateur de bureau, mobile, tablette, etc.) tout en gardant une trace de chaque connexion pour des raisons de sécurité.

---

## 🏗️ Architecture

### Composants

```
┌─────────────────┐
│   UserSession   │  ← Modèle (Table DB)
│   (Model)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ SessionService  │  ← Logique métier
│  (Service)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Endpoints     │  ← Routes API
│   (API)         │
└─────────────────┘
```

---

## 📊 Modèle UserSession

### Structure de la Table

```sql
CREATE TABLE user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    device_info VARCHAR(255),
    created_at DATETIME NOT NULL,
    last_activity DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES user(id)
);
```

### Champs Expliqués

| Champ | Description | Exemple |
|-------|-------------|---------|
| `session_token` | Token unique stocké dans le cookie | `"xK7pL9qR3..."` (32 bytes urlsafe) |
| `user_id` | ID de l'utilisateur connecté | `1` |
| `ip_address` | Adresse IP du client | `"192.168.1.100"` |
| `user_agent` | User-Agent HTTP complet | `"Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."` |
| `device_info` | Description simple du device | `"Chrome on Windows"` |
| `created_at` | Date de création de la session | `2025-01-15 10:30:00` |
| `last_activity` | Dernière activité de l'utilisateur | `2025-01-15 14:25:30` |
| `expires_at` | Date d'expiration | `2025-01-22 10:30:00` (7 jours) |
| `is_active` | Session active ou déconnectée | `true` / `false` |

---

## 🔧 SessionService

### Méthodes Principales

#### 1. Créer une Session

```python
from app.services.session_service import SessionService

user_session = SessionService.create_session(
    db_session=session,
    user=user,
    request=request,
    remember_me=False  # False = 7 jours, True = 30 jours
)

# Résultat :
# - Token généré : secrets.token_urlsafe(32)
# - IP récupérée : request.client.host
# - User-Agent extrait : request.headers["user-agent"]
# - Device info calculé : "Chrome on Windows"
# - Expiration : now + 7 jours (ou 30 si remember_me=True)
```

---

#### 2. Récupérer l'Utilisateur depuis une Session

```python
session_token = request.cookies.get("mppeep_session")

user = SessionService.get_user_from_session(
    db_session=session,
    session_token=session_token
)

if user:
    # ✅ Session valide, utilisateur authentifié
    print(f"Utilisateur : {user.email}")
else:
    # ❌ Session invalide, expirée ou inexistante
    return redirect("/login")
```

**Vérifications automatiques :**
- ✅ Token existe ?
- ✅ Session active ?
- ✅ Session non expirée ?
- ✅ Utilisateur actif ?

---

#### 3. Lister les Sessions Actives

```python
sessions = SessionService.get_active_sessions(
    db_session=session,
    user_id=user.id
)

for s in sessions:
    print(f"""
    Device: {s.device_info}
    IP: {s.ip_address}
    Créée: {s.created_at}
    Dernière activité: {s.last_activity}
    Expire: {s.expires_at}
    """)
```

**Exemple de sortie :**
```
Device: Chrome on Windows
IP: 192.168.1.100
Créée: 2025-01-15 10:30:00
Dernière activité: 2025-01-15 14:25:30
Expire: 2025-01-22 10:30:00

Device: Safari on iOS
IP: 192.168.1.105
Créée: 2025-01-14 08:15:00
Dernière activité: 2025-01-15 12:00:00
Expire: 2025-01-21 08:15:00
```

---

#### 4. Déconnecter une Session

```python
# Déconnecter une session spécifique
success = SessionService.delete_session(
    db_session=session,
    session_token=session_token
)

if success:
    print("✅ Session déconnectée")
```

---

#### 5. Déconnecter Toutes les Sessions

```python
# Déconnecter toutes les sessions d'un utilisateur
count = SessionService.delete_all_user_sessions(
    db_session=session,
    user_id=user.id
)

print(f"✅ {count} session(s) déconnectée(s)")
```

**Cas d'usage :** 
- Changement de mot de passe → Déconnecter tous les appareils
- Sécurité compromise → Forcer une nouvelle authentification partout

---

#### 6. Nettoyer les Sessions Expirées

```python
# À exécuter périodiquement (cron job, scheduler)
count = SessionService.cleanup_expired_sessions(db_session=session)

print(f"🧹 {count} session(s) expirée(s) nettoyée(s)")
```

---

## 🍪 Gestion des Cookies

### Créer le Cookie

```python
from fastapi import Response
from app.services.session_service import SessionService

response = Response()

SessionService.set_session_cookie(
    response=response,
    session_token=user_session.session_token,
    max_age=7 * 24 * 60 * 60  # 7 jours en secondes
)

# Cookie créé avec :
# - Name: mppeep_session
# - Value: session_token
# - Max-Age: 7 jours
# - HttpOnly: True (protection XSS)
# - Secure: False (TODO: True en production avec HTTPS)
# - SameSite: Lax (protection CSRF)
```

---

### Supprimer le Cookie

```python
from fastapi import Response
from app.services.session_service import SessionService

response = Response()
SessionService.delete_session_cookie(response)
```

---

## 🔄 Workflow Complet : Login

### Code Exemple

```python
from fastapi import APIRouter, Depends, Response
from sqlmodel import Session
from app.db import get_session
from app.services.user_service import UserService
from app.services.session_service import SessionService

router = APIRouter()

@router.post("/login")
async def login(
    email: str,
    password: str,
    remember_me: bool = False,
    request: Request,
    response: Response,
    db_session: Session = Depends(get_session)
):
    # 1. Authentifier l'utilisateur
    user = UserService.authenticate(db_session, email, password)
    
    if not user:
        raise HTTPException(401, detail="Email ou mot de passe incorrect")
    
    # 2. Créer une session
    user_session = SessionService.create_session(
        db_session=db_session,
        user=user,
        request=request,
        remember_me=remember_me
    )
    
    # 3. Définir le cookie
    max_age = 30 * 24 * 60 * 60 if remember_me else 7 * 24 * 60 * 60
    SessionService.set_session_cookie(
        response=response,
        session_token=user_session.session_token,
        max_age=max_age
    )
    
    # 4. Retourner la réponse
    return {
        "message": "Connexion réussie",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name
        }
    }
```

---

## 🔒 Sécurité

### Mesures Implémentées

#### 1. Tokens Sécurisés

```python
import secrets

# Génération cryptographiquement sécurisée
session_token = secrets.token_urlsafe(32)
# → 43 caractères alphanumériques + sûr
# → Exemples: "xK7pL9qR3mN5vB2wT8..."
```

---

#### 2. Cookies HttpOnly

```python
response.set_cookie(
    key="mppeep_session",
    value=session_token,
    httponly=True  # ← Inaccessible depuis JavaScript (protection XSS)
)
```

**Avantage :** Un script malveillant ne peut pas voler le cookie

---

#### 3. Cookies SameSite

```python
response.set_cookie(
    key="mppeep_session",
    value=session_token,
    samesite="lax"  # ← Protection CSRF
)
```

**Options :**
- `"strict"` : Cookie envoyé seulement sur le même site
- `"lax"` : Cookie envoyé sur le même site + navigation GET
- `"none"` : Cookie envoyé partout (nécessite Secure=True)

---

#### 4. Expiration Automatique

```python
# Sessions expirées automatiquement détectées
if session.is_expired():
    session.deactivate()
    db_session.commit()
    return None
```

---

#### 5. Tracking IP et Device

```python
# Détection de changements suspects
if session.ip_address != current_ip:
    logger.warning(f"⚠️  Changement d'IP détecté pour session {session.id}")
```

---

## 📱 Cas d'Usage

### 1. Utilisateur Normal

```
Lundi 10h00 : Login depuis ordinateur bureau (Windows)
  → Session 1 créée : "Chrome on Windows"

Lundi 14h00 : Login depuis téléphone (iOS)
  → Session 2 créée : "Safari on iOS"

Les deux sessions sont ACTIVES en même temps ✅
L'utilisateur peut utiliser les deux appareils simultanément
```

---

### 2. Changement de Mot de Passe

```python
# Après changement de mot de passe
@router.post("/change-password")
async def change_password(
    user_id: int,
    new_password: str,
    db_session: Session = Depends(get_session)
):
    # 1. Changer le mot de passe
    user = UserService.get_by_id(db_session, user_id)
    UserService.update_password(db_session, user, new_password)
    
    # 2. Déconnecter TOUTES les sessions
    count = SessionService.delete_all_user_sessions(db_session, user_id)
    
    return {
        "message": "Mot de passe changé",
        "sessions_disconnected": count
    }
```

---

### 3. Page "Mes Appareils Connectés"

```python
@router.get("/my-sessions")
async def get_my_sessions(
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_session)
):
    sessions = SessionService.get_active_sessions(
        db_session=db_session,
        user_id=current_user.id
    )
    
    return {
        "sessions": [
            {
                "id": s.id,
                "device": s.device_info,
                "ip": s.ip_address,
                "created_at": s.created_at,
                "last_activity": s.last_activity,
                "current": s.session_token == request.cookies.get("mppeep_session")
            }
            for s in sessions
        ]
    }
```

**Exemple de réponse :**
```json
{
  "sessions": [
    {
      "id": 1,
      "device": "Chrome on Windows",
      "ip": "192.168.1.100",
      "created_at": "2025-01-15T10:30:00",
      "last_activity": "2025-01-15T14:25:30",
      "current": true
    },
    {
      "id": 2,
      "device": "Safari on iOS",
      "ip": "192.168.1.105",
      "created_at": "2025-01-14T08:15:00",
      "last_activity": "2025-01-15T12:00:00",
      "current": false
    }
  ]
}
```

---

### 4. Déconnecter un Appareil Spécifique

```python
@router.delete("/sessions/{session_id}")
async def disconnect_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_session)
):
    # Récupérer la session
    user_session = db_session.get(UserSession, session_id)
    
    if not user_session or user_session.user_id != current_user.id:
        raise HTTPException(404, detail="Session non trouvée")
    
    # Déconnecter
    user_session.deactivate()
    db_session.commit()
    
    return {"message": "Appareil déconnecté"}
```

---

## 🧹 Maintenance

### Nettoyage Automatique

#### Option 1 : Scheduler Python (APScheduler)

```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

def cleanup_sessions():
    with Session(engine) as session:
        count = SessionService.cleanup_expired_sessions(session)
        logger.info(f"🧹 {count} sessions expirées nettoyées")

# Exécuter toutes les heures
scheduler.add_job(cleanup_sessions, 'interval', hours=1)
scheduler.start()
```

---

#### Option 2 : Cron Job (Linux/Mac)

```bash
# Créer un script cleanup_sessions.py
# scripts/cleanup_sessions.py

from app.db import Session, engine
from app.services.session_service import SessionService

with Session(engine) as session:
    count = SessionService.cleanup_expired_sessions(session)
    print(f"✅ {count} sessions nettoyées")

# Ajouter au crontab (toutes les heures)
# crontab -e
0 * * * * cd /path/to/project && python scripts/cleanup_sessions.py
```

---

#### Option 3 : Task Scheduler (Windows)

```powershell
# Créer une tâche planifiée
$action = New-ScheduledTaskAction -Execute "python" -Argument "scripts/cleanup_sessions.py"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "Cleanup Sessions" -Action $action -Trigger $trigger
```

---

## 📊 Statistiques

### Requêtes SQL Optimisées

```sql
-- Index sur session_token (recherche rapide)
CREATE INDEX idx_session_token ON user_sessions(session_token);

-- Index sur user_id (lister les sessions d'un user)
CREATE INDEX idx_user_id ON user_sessions(user_id);

-- Index composé pour filtrage (actives + non expirées)
CREATE INDEX idx_active_sessions ON user_sessions(user_id, is_active, expires_at);
```

---

## ✅ Avantages du Système

| Avantage | Description |
|----------|-------------|
| 🔐 **Sécurité** | Tokens cryptographiquement sûrs, cookies HttpOnly |
| 📱 **Multi-device** | Plusieurs connexions simultanées |
| 👁️ **Transparence** | L'utilisateur voit où il est connecté |
| 🧹 **Auto-nettoyage** | Sessions expirées supprimées automatiquement |
| 📊 **Tracking** | IP, device, activité pour audit de sécurité |
| 🔄 **Flexibilité** | Expiration configurable (7 ou 30 jours) |

---

## 🚀 Évolutions Futures

### Fonctionnalités à Ajouter

- [ ] Notifications lors de nouvelles connexions
- [ ] Détection de localisation (via IP geolocation)
- [ ] Limite du nombre de sessions simultanées
- [ ] Historique des connexions (archivage)
- [ ] Two-Factor Authentication (2FA)
- [ ] Détection d'activité suspecte
- [ ] API pour gérer les sessions depuis une app mobile

---

## 📚 Ressources

### Documentation Liée

- `app/models/session.py` - Modèle UserSession
- `app/services/session_service.py` - Service de sessions
- `app/core/config.py` - Configuration (SESSION_TIMEOUT, etc.)
- `LOGGING_QUICKSTART.md` - Voir les logs de sessions

### Standards de Sécurité

- [OWASP Session Management](https://owasp.org/www-community/vulnerabilities/Session_Management)
- [MDN HTTP Cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

---

**🔐 Système de sessions sécurisé et moderne pour authentification multi-device !**

