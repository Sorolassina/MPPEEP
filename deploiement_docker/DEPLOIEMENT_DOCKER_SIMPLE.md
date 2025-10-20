# 🚀 Déploiement Docker - Guide Simplifié

## 🎯 Objectif

Déployer l'application MPPEEP Dashboard sur un autre ordinateur avec Docker et permettre les mises à jour automatiques.

---

## 📋 Prérequis sur l'Ordinateur de Production

1. **Docker Desktop** ou **Docker Engine** installé
2. **Docker Compose** installé
3. **Git** installé (pour les mises à jour)
4. **Port 9000** disponible (ou modifiable)

---

## 🏗️ ÉTAPE 1 : Construire l'Image Docker (Ordinateur de Développement)

### Option A : Construction Simple

```powershell
# Dans le dossier mppeep
cd mppeep

# Construire l'image de production
docker build -f Dockerfile.prod -t mppeep-dashboard:latest .

# Sauvegarder l'image dans un fichier (pour transfert)
docker save mppeep-dashboard:latest -o mppeep-dashboard-latest.tar
```

**Résultat** : Fichier `mppeep-dashboard-latest.tar` (~500 MB) prêt pour le transfert

### Option B : Avec Docker Compose (Recommandé)

```powershell
# Construire l'image + services
docker-compose -f docker-compose.prod.yml build

# Sauvegarder
docker save mppeep_app:latest -o mppeep-app.tar
```

---

## 📦 ÉTAPE 2 : Transfert sur l'Ordinateur de Production

Copiez ces fichiers :
- `mppeep-dashboard-latest.tar` (image Docker)
- `docker-compose.prod.yml`
- `nginx.conf`
- `.env` (à créer sur prod)

---

## ⚙️ ÉTAPE 3 : Démarrage sur Production

```powershell
# 1. Charger l'image
docker load -i mppeep-dashboard-latest.tar

# 2. Créer le .env (voir exemple ci-dessous)

# 3. Démarrer
docker-compose -f docker-compose.prod.yml up -d

# 4. Vérifier
docker-compose -f docker-compose.prod.yml ps
start http://localhost:9000
```

---

## 🔄 MISE À JOUR AUTOMATIQUE

Créez `update-docker.ps1` :

```powershell
Write-Host "🔄 Mise à jour..." -ForegroundColor Cyan

# Backup
docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U mppeep mppeep_prod > "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"

# Pull code (si Git)
git pull origin main

# Rebuild + Restart
docker-compose -f docker-compose.prod.yml up -d --build app

Write-Host "✅ Mise à jour terminée !" -ForegroundColor Green
```

---

**🐳 Votre déploiement Docker est prêt !**

