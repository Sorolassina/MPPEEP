# ⚡ Démarrage Rapide - Docker Production

## 🎯 En 3 étapes simples

### 📍 Sur l'Ordinateur de DÉVELOPPEMENT

#### 1️⃣ Construire l'image
```powershell
cd mppeep
.\build-docker-prod.ps1 -SaveImage
```
✅ Crée : `docker-images\mppeep-dashboard-latest-20251020.tar`

#### 2️⃣ Copier ces fichiers sur une clé USB
- `docker-images\mppeep-dashboard-latest-20251020.tar`
- `docker-compose.prod.yml`
- `nginx.conf`
- `env.production.template`

---

### 💻 Sur l'Ordinateur de PRODUCTION

#### 1️⃣ Créer le dossier
```powershell
mkdir C:\MPPEEP-Production
cd C:\MPPEEP-Production

# Copier les fichiers depuis la clé USB
```

#### 2️⃣ Configurer

```powershell
# Créer le fichier .env
copy env.production.template .env
notepad .env

# Modifiez :
# - POSTGRES_PASSWORD (mot de passe fort)
# - SECRET_KEY (générez avec Python)
# - BASE_URL (votre domaine)
```

#### 3️⃣ Charger et Démarrer

```powershell
# Charger l'image Docker
docker load -i mppeep-dashboard-latest-20251020.tar

# Démarrer l'application
docker-compose -f docker-compose.prod.yml up -d

# Vérifier
docker-compose -f docker-compose.prod.yml ps
```

#### 4️⃣ Tester

```powershell
# Ouvrir dans le navigateur
start http://localhost:9000

# Login : admin@mppeep.com / admin123
# ⚠️ Changez ce mot de passe immédiatement !
```

---

## 🔄 Pour les Mises à Jour

### Méthode 1 : Avec Git (Automatique)

```powershell
# Sur l'ordinateur de production
cd C:\MPPEEP-Production

# Cloner le dépôt (première fois seulement)
git clone <url-de-votre-depot> .

# Pour mettre à jour (après chaque modification)
.\update-docker.ps1
```

### Méthode 2 : Sans Git (Manuel)

```powershell
# Sur l'ordi de DEV : Reconstruire
.\build-docker-prod.ps1 -SaveImage

# Copier le nouveau .tar sur USB

# Sur l'ordi de PROD :
docker-compose -f docker-compose.prod.yml stop app
docker load -i mppeep-dashboard-latest-20251021.tar
docker-compose -f docker-compose.prod.yml up -d app
```

---

## 📊 Commandes Utiles

```powershell
# Voir les logs
docker-compose -f docker-compose.prod.yml logs -f app

# Status
docker-compose -f docker-compose.prod.yml ps

# Redémarrer
docker-compose -f docker-compose.prod.yml restart app

# Arrêter tout
docker-compose -f docker-compose.prod.yml down

# Backup de la base
docker-compose -f docker-compose.prod.yml exec db pg_dump -U mppeep mppeep_prod > backup.sql
```

---

## 🎉 C'est Tout !

Votre application tourne maintenant en production avec Docker ! 🚀

**Documentation complète** : Voir `DEPLOIEMENT_DOCKER_SIMPLE.md`

