# 🚀 Quick Start - Système de Logging

## ⚡ Démarrage Rapide

### 1. Utiliser les Logs dans Votre Code

```python
from app.core.logging_config import get_logger

# Créer un logger pour votre module
logger = get_logger(__name__)

# Logger des informations
logger.info("✅ Opération réussie")
logger.warning("⚠️  Attention !")
logger.error("❌ Erreur rencontrée")
logger.critical("🔥 Erreur critique !")
```

---

## 📁 Fichiers de Logs

Tous les logs sont dans le dossier `logs/` :

```
logs/
├── app.log         → Tous les logs
├── error.log       → Seulement les erreurs
└── access.log      → Requêtes HTTP
```

---

## 👀 Voir les Logs en Temps Réel

### Windows (PowerShell)
```powershell
# Tous les logs
Get-Content logs\app.log -Wait -Tail 20

# Erreurs seulement
Get-Content logs\error.log -Wait -Tail 20

# Accès HTTP
Get-Content logs\access.log -Wait -Tail 20
```

### Linux/Mac
```bash
tail -f logs/app.log        # Tous les logs
tail -f logs/error.log      # Erreurs
tail -f logs/access.log     # HTTP
```

---

## 🎨 Console avec Couleurs

Les logs console utilisent des couleurs :

- 🟢 **INFO** : Vert (opérations normales)
- 🟡 **WARNING** : Jaune (situations anormales)
- 🔴 **ERROR** : Rouge (erreurs)
- 🟣 **CRITICAL** : Magenta (erreurs critiques)

---

## 📊 Séparation stdout/stderr

- **stdout** (sortie standard) : INFO, WARNING
- **stderr** (sortie erreur) : ERROR, CRITICAL

Utile pour rediriger séparément :
```bash
# Capturer seulement les erreurs
uvicorn app.main:app 2> errors.txt

# Capturer tout sauf les erreurs
uvicorn app.main:app 1> output.txt
```

---

## 🔧 Exemples d'Utilisation

### Dans un Service

```python
# app/services/user_service.py
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class UserService:
    @staticmethod
    def create_user(session, email, password):
        logger.info(f"Création utilisateur : {email}")
        
        try:
            user = User(email=email, ...)
            session.add(user)
            session.commit()
            
            logger.info(f"✅ Utilisateur créé : {user.id}")
            return user
            
        except Exception as e:
            logger.error(f"❌ Erreur : {e}", exc_info=True)
            raise
```

### Dans un Endpoint

```python
# app/api/v1/endpoints/users.py
from app.core.logging_config import get_logger

logger = get_logger(__name__)

@router.post("/users")
async def create_user(user: UserCreate):
    logger.info(f"Requête création : {user.email}")
    
    try:
        new_user = UserService.create_user(session, ...)
        return new_user
    except Exception as e:
        logger.error(f"Erreur API : {e}", exc_info=True)
        raise HTTPException(status_code=500)
```

---

## 📝 Bonnes Pratiques

### ✅ À Faire

```python
# Logger avec contexte
logger.info(f"Utilisateur {user_id} connecté")

# Logger les erreurs avec stack trace
logger.error(f"Erreur : {e}", exc_info=True)

# Utiliser des emojis pour la visibilité
logger.info("✅ Succès")
logger.error("❌ Échec")
```

### ❌ À Éviter

```python
# Ne pas logger de données sensibles
logger.info(f"Password: {password}")  # ❌

# Ne pas utiliser print()
print("Debug info")  # ❌ Utiliser logger.debug()

# Ne pas logger sans contexte
logger.error("Erreur")  # ❌ Trop vague
```

---

## 🔍 Rechercher dans les Logs

### Windows
```powershell
# Rechercher "ERROR"
Select-String -Path logs\app.log -Pattern "ERROR"

# Rechercher une requête
Select-String -Path logs\access.log -Pattern "POST /api/v1/login"

# Rechercher par Request-ID
Select-String -Path logs\app.log -Pattern "abc-123"
```

### Linux/Mac
```bash
# Rechercher "ERROR"
grep "ERROR" logs/app.log

# Rechercher une requête
grep "POST /api/v1/login" logs/access.log

# Rechercher par Request-ID
grep "abc-123" logs/app.log
```

---

## 🎯 Résumé

| Feature              | Description                      |
|----------------------|----------------------------------|
| 📄 **app.log**       | Tous les logs de l'application  |
| ❌ **error.log**     | Seulement les erreurs           |
| 🌐 **access.log**    | Requêtes HTTP (Apache-like)     |
| 🎨 **Console**       | Logs colorés (stdout/stderr)    |
| 🔄 **Rotation**      | Automatique à 10 MB             |
| 📊 **Format**        | Timestamp + Niveau + Contexte   |

---

## 📚 Documentation Complète

Pour plus de détails, consultez : `app/core/LOGGING.md`

---

**🎉 Votre système de logging est prêt ! 🎉**

