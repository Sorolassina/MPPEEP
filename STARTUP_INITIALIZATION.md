# 🚀 Initialisation Automatique au Démarrage

## 🎯 Vue d'Ensemble

L'application **initialise automatiquement** la base de données et crée un utilisateur admin par défaut à chaque démarrage si nécessaire.

---

## ⚙️ Comment ça Fonctionne ?

### Séquence de Démarrage

```
┌─────────────────────────────────────────┐
│  uvicorn app.main:app --reload          │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│  1. FastAPI démarre                     │
│     app = FastAPI(title=...)            │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│  2. Événement "startup" déclenché       │
│     @app.on_event("startup")            │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│  3. Appel de initialize_database()      │
│     scripts/init_db.py                  │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│  4. Création des tables                 │
│     SQLModel.metadata.create_all()      │
│     ✅ Vérifie si les tables existent   │
│     ✅ Crée seulement celles manquantes │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│  5. Vérification des utilisateurs       │
│     SELECT * FROM user                  │
└────────────────┬────────────────────────┘
                 │
         ┌───────┴───────┐
         │               │
         ↓               ↓
┌────────────┐   ┌────────────────┐
│ Utilisateurs│   │ Base vide      │
│ existent    │   │                │
│             │   │ 6. Création    │
│ → Skip ✅   │   │    admin par   │
│             │   │    défaut      │
└─────────────┘   └────────┬───────┘
                           │
                           ↓
                  ┌─────────────────┐
                  │ admin@mppeep.com│
                  │ / admin123      │
                  │ Superuser: Yes  │
                  └────────┬────────┘
                           │
                           ↓
                  ┌─────────────────┐
                  │ ✅ Affichage    │
                  │    identifiants │
                  └────────┬────────┘
                           │
         ┌─────────────────┴──────────────────┐
         │                                    │
         ↓                                    ↓
┌─────────────────────────────────────────────┐
│  7. Application prête                       │
│     🌐 http://localhost:8000                │
│     📚 http://localhost:8000/docs           │
└─────────────────────────────────────────────┘
```

---

## 📝 Code Impliqué

### 1. `app/main.py` - Événement de Startup

```python
@app.on_event("startup")
async def startup_event():
    """
    Initialisation au démarrage de l'application
    - Crée les tables de la base de données
    - Crée l'utilisateur admin par défaut si aucun utilisateur n'existe
    """
    try:
        from scripts.init_db import initialize_database
        initialize_database()
    except Exception as e:
        print(f"⚠️  Erreur lors de l'initialisation: {e}")
        print("   L'application démarre quand même...")
```

---

### 2. `scripts/init_db.py` - Logique d'Initialisation

```python
def initialize_database():
    """
    Initialise la base de données complète :
    1. Crée les tables si elles n'existent pas
    2. Crée l'utilisateur admin si aucun utilisateur n'existe
    """
    # Étape 1: Créer les tables
    create_tables()
    
    # Étape 2: Créer l'admin si besoin
    create_admin_user()
```

---

## ✅ Ce qui est Créé Automatiquement

### Tables de Base de Données

Toutes les tables définies dans `app/models/` :

```
✅ user (id, email, full_name, hashed_password, is_active, is_superuser)
✅ ... (autres tables futures)
```

### Utilisateur Admin Par Défaut

Si **aucun utilisateur** n'existe dans la base :

```
📧 Email     : admin@mppeep.com
🔑 Password  : admin123
👑 Superuser : Oui
✓  Actif     : Oui
```

---

## 🔄 Comportement Selon l'État

### Scénario 1 : Premier Démarrage (DB vide)

```bash
uvicorn app.main:app --reload
```

**Output :**
```
🚀 Initialisation de la base de données...
📂 Base de données: sqlite:///./app.db
--------------------------------------------------
✅ Tables de la base de données créées/vérifiées

==================================================
✅ UTILISATEUR ADMIN CRÉÉ
==================================================
📧 Email    : admin@mppeep.com
🔑 Password : admin123
🆔 ID       : 1
==================================================
⚠️  IMPORTANT: Changez ce mot de passe en production!
==================================================

✅ Initialisation terminée avec succès!
```

---

### Scénario 2 : Démarrage Normal (DB existe)

```bash
uvicorn app.main:app --reload
```

**Output :**
```
🚀 Initialisation de la base de données...
📂 Base de données: sqlite:///./app.db
--------------------------------------------------
✅ Tables de la base de données créées/vérifiées
ℹ️  5 utilisateur(s) trouvé(s) dans la base
✅ Initialisation terminée avec succès!
```

---

### Scénario 3 : Erreur d'Initialisation

```bash
uvicorn app.main:app --reload
```

**Output :**
```
🚀 Initialisation de la base de données...
⚠️  Erreur lors de l'initialisation: [erreur]
   L'application démarre quand même...
```

**Résultat :** L'application démarre malgré l'erreur, mais vous devrez initialiser la DB manuellement.

---

## 🔧 Initialisation Manuelle

Si l'initialisation automatique échoue, vous pouvez la lancer manuellement :

```bash
# Initialisation complète
python scripts/init_db.py

# OU seulement créer un utilisateur
python scripts/create_user.py
```

---

## 🎯 Avantages de Cette Approche

### ✅ Pour le Développement

```
1. Cloner le projet
2. uv sync
3. uvicorn app.main:app --reload
   → Tout est créé automatiquement ! ✅

Plus besoin de :
❌ python scripts/init_db.py
❌ python scripts/create_user.py
```

---

### ✅ Pour la Production

```
1. Déployer le code
2. Lancer l'application
   → Tables + Admin créés automatiquement ✅
3. Se connecter et changer le mot de passe admin
```

---

### ✅ Pour les Tests

```
Les tests utilisent une DB en mémoire séparée
→ L'initialisation auto n'interfère pas
```

---

## 🔒 Sécurité

### ⚠️ Mot de Passe par Défaut

L'utilisateur admin par défaut utilise `admin123` comme mot de passe.

**En production, vous DEVEZ :**
1. Se connecter avec `admin@mppeep.com / admin123`
2. Changer le mot de passe immédiatement
3. OU créer un nouvel admin et désactiver/supprimer celui par défaut

### ✅ Idempotence

Le script peut être exécuté plusieurs fois sans problème :
- Tables existantes → Ignorées
- Utilisateurs existants → Ignorés
- Aucun doublon créé

---

## 🐛 Troubleshooting

### L'admin n'est pas créé

**Vérifier :**
```bash
# Vérifier qu'aucun utilisateur n'existe
sqlite3 app.db "SELECT * FROM user;"

# Si des utilisateurs existent, l'admin ne sera pas créé
# Solution : Supprimer la DB et redémarrer
rm app.db
uvicorn app.main:app --reload
```

### Erreur de connexion à la DB

**Vérifier la configuration :**
```bash
python scripts/show_config.py
```

### Les tables ne sont pas créées

**Vérifier les modèles :**
```bash
# Les modèles doivent hériter de SQLModel avec table=True
# Vérifier app/models/*.py
```

---

## 📊 Logs de Démarrage

### Normal

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
🚀 Initialisation de la base de données...
✅ Tables de la base de données créées/vérifiées
ℹ️  1 utilisateur(s) trouvé(s) dans la base
✅ Initialisation terminée avec succès!
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Premier Démarrage

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
🚀 Initialisation de la base de données...
✅ Tables de la base de données créées/vérifiées

==================================================
✅ UTILISATEUR ADMIN CRÉÉ
==================================================
📧 Email    : admin@mppeep.com
🔑 Password : admin123
🆔 ID       : 1
==================================================

✅ Initialisation terminée avec succès!
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 🎉 Résumé

✅ **Initialisation automatique** au démarrage  
✅ **Aucune commande manuelle** nécessaire  
✅ **Idempotent** : sûr de relancer plusieurs fois  
✅ **Sécurisé** : vérifications avant création  
✅ **Multi-environnements** : fonctionne partout (dev/staging/prod)  

**Votre application est prête dès le premier `uvicorn` ! 🚀**

