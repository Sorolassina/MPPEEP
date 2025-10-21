# 📦 Déploiement via Clé USB - Guide Complet

## 🎯 **Fichiers à copier sur la clé USB :**

### **Méthode 1 : Avec l'image Docker exportée (RECOMMANDÉ)**

Cette méthode permet de déployer sans avoir à reconstruire l'image.

#### **📋 Liste des fichiers :**

```
📁 USB/
├── 📄 mppeep-dashboard_YYYYMMDD_HHMMSS.tar  ← Image Docker exportée (généré)
├── 📄 docker-compose.prod.yml              ← Configuration production
├── 📄 .env                                 ← Variables d'environnement
├── 📄 requirements.txt                     ← Dépendances Python (optionnel)
├── 📁 deploiement_docker/
│   ├── 📄 nginx.conf                       ← Config Nginx (si utilisé)
│   └── 📄 Dockerfile.prod                  ← Pour rebuild si besoin
└── 📄 Makefile                             ← Commandes utiles (optionnel)
```

#### **🚀 Commandes pour préparer :**

```powershell
# 1. Créer le dossier de déploiement
New-Item -ItemType Directory -Path "deploiement_docker" -Force

# 2. Exporter l'image Docker
make docker-save
# OU manuellement :
docker save mppeep:latest -o deploiement_docker/mppeep-dashboard.tar

# 3. Copier les fichiers sur USB
Copy-Item -Path "deploiement_docker/mppeep-dashboard.tar" -Destination "E:/" # E: = votre USB
Copy-Item -Path "docker-compose.prod.yml" -Destination "E:/"
Copy-Item -Path ".env" -Destination "E:/"
Copy-Item -Path "Makefile" -Destination "E:/"
```

---

### **Méthode 2 : Avec le code source complet**

Si vous voulez tout rebuilder sur l'autre ordinateur.

#### **📋 Fichiers minimums :**

```
📁 USB/
├── 📁 app/                    ← Tout le code source
├── 📁 scripts/                ← Scripts d'initialisation
├── 📁 deploiement_docker/     ← Dockerfiles
├── 📄 docker-compose.prod.yml
├── 📄 .env
├── 📄 requirements.txt
├── 📄 Makefile
└── 📄 pyproject.toml
```

**OU** simplement copier tout le dossier `mppeep/` :

```powershell
# Copier tout le projet (exclure .venv, __pycache__, etc.)
robocopy "C:\...\mppeep" "E:\mppeep" /E /XD .venv __pycache__ .pytest_cache node_modules .git
```

---

## 💾 **PRÉPARATION AUTOMATIQUE :**

Utilisons votre Makefile pour créer un package complet :

### **Commande à exécuter :**

```powershell
make docker-package
```

Cela va créer un dossier `deploiement_docker/` avec tout ce qu'il faut !

---

## 📤 **Sur l'ordinateur SOURCE (développement) :**

### **Étape 1 : Exporter l'image Docker**

```powershell
# Option A : Via Makefile (RECOMMANDÉ)
make docker-save

# Option B : Manuellement
docker save mppeep:latest -o mppeep-dashboard.tar
```

**Résultat :** Un fichier `.tar` de ~200-500 MB

### **Étape 2 : Préparer les fichiers de configuration**

Créer un dossier `deploiement/` :

```powershell
# Créer le dossier
mkdir deploiement

# Copier les fichiers essentiels
Copy-Item docker-compose.prod.yml deploiement/
Copy-Item .env deploiement/
Copy-Item Makefile deploiement/
Copy-Item -Recurse deploiement_docker deploiement/
```

### **Étape 3 : Copier sur la clé USB**

```powershell
# Copier le dossier deploiement + l'image .tar
Copy-Item -Recurse deploiement E:\mppeep-deploy
Copy-Item deploiement_docker\*.tar E:\mppeep-deploy\
```

---

## 📥 **Sur l'ordinateur DESTINATION (déploiement) :**

### **Prérequis sur la machine de déploiement :**

```powershell
# Vérifier que Docker est installé
docker --version
docker-compose --version

# Vérifier que PostgreSQL est démarré (si local)
# OU que les paramètres de connexion dans .env sont corrects
```

### **Étape 1 : Copier les fichiers depuis USB**

```powershell
# Copier depuis USB vers le disque local
Copy-Item -Recurse E:\mppeep-deploy C:\mppeep-production
cd C:\mppeep-production
```

### **Étape 2 : Charger l'image Docker**

```powershell
# Option A : Via Makefile
make docker-load

# Option B : Manuellement
docker load -i mppeep-dashboard.tar
```

**Résultat attendu :**
```
Loaded image: mppeep:latest
```

### **Étape 3 : Configurer les variables d'environnement**

Éditer le fichier `.env` :

```env
# Base de données (ajuster selon l'environnement)
DATABASE_URL=postgresql://mppeepuser:mppeep@localhost:5432/mppeep
POSTGRES_USER=mppeepuser
POSTGRES_PASSWORD=VotreMotDePasseSecurise
POSTGRES_DB=mppeep

# Sécurité
SECRET_KEY=GenerezUneCleSecuriteIci

# Application
APP_NAME=MPPEEP Dashboard
DEBUG=False
ENV=prod
```

### **Étape 4 : Démarrer l'application**

```powershell
# Démarrer les conteneurs
docker-compose -f docker-compose.prod.yml up -d

# OU via Makefile
make docker-up-prod
```

### **Étape 5 : Vérifier le déploiement**

```powershell
# Voir les logs
docker-compose -f docker-compose.prod.yml logs -f

# Vérifier que ça tourne
docker-compose -f docker-compose.prod.yml ps
```

**Accéder à l'application :**
- Via Cloudflare Tunnel : `https://mppeep.skpartners.consulting`
- Ou directement : `http://localhost:9000/mppeep`

---

## 📦 **CRÉER UN PACKAGE COMPLET AUTOMATISÉ :**

Ajoutons une commande au Makefile pour créer un package USB :

```powershell
make docker-package
```

Cela va créer automatiquement :
```
📁 deploiement_docker/
├── mppeep-dashboard_20251021_120000.tar  ← Image Docker
├── docker-compose.prod.yml               ← Config
├── .env.example                          ← Template .env
├── INSTALL.md                            ← Instructions
└── Makefile                              ← Commandes
```

---

## 📊 **TAILLE DES FICHIERS :**

| Fichier | Taille approximative |
|---------|---------------------|
| Image Docker (.tar) | ~200-500 MB |
| docker-compose.prod.yml | ~5 KB |
| .env | ~1 KB |
| Makefile | ~30 KB |
| nginx.conf | ~2 KB |
| **TOTAL** | **~200-500 MB** |

**Clé USB recommandée :** Minimum 1 GB

---

## ⚠️ **POINTS IMPORTANTS :**

### **1. Sécurité du fichier `.env`**

❌ **NE JAMAIS** partager le `.env` avec les mots de passe réels !

✅ **À la place :**
- Créer un `.env.example` (sans mots de passe)
- Copier sur USB
- Sur la machine de déploiement, créer le vrai `.env`

```env
# .env.example
DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/DB
SECRET_KEY=CHANGEZ_CETTE_CLE
POSTGRES_PASSWORD=CHANGEZ_CE_MOT_DE_PASSE
```

### **2. Base de données**

⚠️ **L'image Docker ne contient PAS les données !**

Options :
- **Option A :** PostgreSQL local déjà configuré sur la machine cible
- **Option B :** Exporter aussi le dump PostgreSQL :
  ```powershell
  pg_dump -U mppeepuser mppeep > mppeep_backup.sql
  # Copier mppeep_backup.sql sur USB
  # Sur la machine cible :
  psql -U mppeepuser mppeep < mppeep_backup.sql
  ```

### **3. Cloudflare Tunnel**

Si vous utilisez Cloudflare Tunnel, assurez-vous que :
- Le tunnel est configuré sur la machine de déploiement
- Le port 9000 est exposé dans `docker-compose.prod.yml` ✅ (déjà fait)

---

## 🎯 **CHECKLIST DÉPLOIEMENT :**

### **Sur l'ordinateur SOURCE :**
- [ ] Exporter l'image Docker (`make docker-save`)
- [ ] Copier `docker-compose.prod.yml`
- [ ] Créer `.env.example` (sans mots de passe)
- [ ] Copier sur clé USB

### **Sur l'ordinateur DESTINATION :**
- [ ] Docker installé et démarré
- [ ] PostgreSQL configuré (si local)
- [ ] Copier fichiers depuis USB
- [ ] Créer `.env` avec vrais mots de passe
- [ ] Charger l'image (`make docker-load`)
- [ ] Démarrer (`docker-compose up -d`)
- [ ] Vérifier (`docker-compose ps`)
- [ ] Tester l'accès web

---

## 🚀 **COMMANDES RAPIDES :**

### **Ordinateur SOURCE (préparation) :**
```powershell
# 1. Export image
make docker-save

# 2. Package complet (si commande existe)
make docker-package
```

### **Ordinateur DESTINATION (installation) :**
```powershell
# 1. Copier depuis USB
Copy-Item E:\mppeep-deploy C:\mppeep -Recurse

# 2. Aller dans le dossier
cd C:\mppeep

# 3. Charger l'image
make docker-load

# 4. Configurer .env
notepad .env

# 5. Démarrer
make docker-up-prod
```

---

**Besoin d'aide ? Consultez les fichiers :**
- `INSTALL.md` - Instructions détaillées
- `Makefile` - Toutes les commandes disponibles
- `.env.example` - Template de configuration

