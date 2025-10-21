# 🚀 CI/CD avec Docker - MPPEEP Dashboard

## 📋 Vue d'Ensemble

Votre setup :
- **Machine 1** : Développement (Windows)
- **Machine 2** : Production (Linux serveur avec Cloudflare Tunnel)
- **Besoin** : Automatiser le déploiement

---

## 🎯 Stratégies de Déploiement

### Option 1 : Docker Hub (RECOMMANDÉ) ✅

**Workflow** :
```
Machine Dev → Build Image → Push Docker Hub → Machine Prod Pull → Run
```

**Avantages** :
- ✅ Simple et standard
- ✅ Versionning automatique
- ✅ Rollback facile
- ✅ Plan gratuit suffisant

### Option 2 : GitHub Actions + Docker Hub ⭐ MEILLEUR

**Workflow** :
```
Git Push → GitHub Actions → Build → Push Docker Hub → Webhook → Serveur Pull & Deploy
```

**Avantages** :
- ✅ Automatique (git push = deploy)
- ✅ Tests avant déploiement
- ✅ Historique complet
- ✅ Gratuit (GitHub Actions)

### Option 3 : Export/Import Manuel (Simple)

**Workflow** :
```
Machine Dev → docker save → Transfert (scp/rsync) → Machine Prod → docker load
```

**Avantages** :
- ✅ Pas de registry externe
- ✅ Contrôle total
- ⚠️ Manuel

---

## 🏗️ Solution 1 : Docker Hub (Simple & Rapide)

### Étape 1 : Créer un Compte Docker Hub

1. **S'inscrire** : https://hub.docker.com/signup
2. **Créer un repository** :
   - Nom : `mppeep`
   - Visibilité : Public (gratuit) ou Privé (1 gratuit)

### Étape 2 : Configuration sur Machine Dev

```powershell
# 1. Se connecter à Docker Hub
docker login
# Username: votreusername
# Password: votre-mot-de-passe

# 2. Ajouter dans votre Makefile (déjà prêt)
# Variables
DOCKER_USERNAME=votreusername
DOCKER_IMAGE=mppeep
DOCKER_TAG=latest

# 3. Builder et pousser
docker build -f Dockerfile.prod -t ${DOCKER_USERNAME}/${DOCKER_IMAGE}:${DOCKER_TAG} .
docker push ${DOCKER_USERNAME}/${DOCKER_IMAGE}:${DOCKER_TAG}
```

### Étape 3 : Déploiement sur Machine Prod

```bash
# Sur le serveur de production
# 1. Se connecter à Docker Hub (une seule fois)
docker login

# 2. Créer un script de déploiement
nano deploy.sh
```

**Fichier `deploy.sh`** :
```bash
#!/bin/bash
# Script de déploiement MPPEEP

DOCKER_USERNAME="votreusername"
DOCKER_IMAGE="mppeep"
DOCKER_TAG="latest"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Déploiement MPPEEP Dashboard"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Arrêter les containers
echo "📦 Arrêt des containers..."
docker-compose -f docker-compose.prod.yml down

# 2. Récupérer la nouvelle image
echo "⬇️  Téléchargement de la nouvelle image..."
docker pull ${DOCKER_USERNAME}/${DOCKER_IMAGE}:${DOCKER_TAG}

# 3. Mettre à jour docker-compose.prod.yml pour utiliser l'image
# (modifier image: mppeep:latest → image: votreusername/mppeep:latest)

# 4. Démarrer avec la nouvelle image
echo "🚀 Démarrage des containers..."
docker-compose -f docker-compose.prod.yml up -d

# 5. Vérifier
echo "✅ Vérification du déploiement..."
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs --tail=50 app

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Déploiement terminé !"
echo "🌐 URL : https://mppeep.skpartners.consulting/mppeep/"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

### Workflow Complet

```
┌─────────────────────────────────────────────────────────────┐
│  MACHINE DEV (Windows)                                      │
├─────────────────────────────────────────────────────────────┤
│  1. Développement du code                                   │
│  2. Tests locaux                                            │
│  3. Build de l'image :                                      │
│     docker build -f Dockerfile.prod -t user/mppeep:v1.2.0 . │
│  4. Push vers Docker Hub :                                  │
│     docker push user/mppeep:v1.2.0                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ Push vers Docker Hub
┌─────────────────────────────────────────────────────────────┐
│  🐳 DOCKER HUB (Registry Cloud)                             │
│  https://hub.docker.com/r/votreusername/mppeep             │
├─────────────────────────────────────────────────────────────┤
│  Images stockées :                                          │
│  ├─ user/mppeep:v1.0.0                                     │
│  ├─ user/mppeep:v1.1.0                                     │
│  └─ user/mppeep:v1.2.0 (latest)                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ Pull depuis Docker Hub
┌─────────────────────────────────────────────────────────────┐
│  MACHINE PROD (Linux Serveur)                               │
├─────────────────────────────────────────────────────────────┤
│  1. Pull de la nouvelle image :                             │
│     docker pull user/mppeep:v1.2.0                         │
│  2. Mise à jour docker-compose                              │
│  3. Restart :                                               │
│     docker-compose up -d                                    │
│  4. ✅ Application mise à jour !                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🤖 Solution 2 : GitHub Actions (Automatisé) ⭐ MEILLEUR

### Étape 1 : Repository GitHub

Si votre code n'est pas encore sur GitHub :

```bash
# Sur machine dev
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/votreusername/mppeep-dashboard.git
git push -u origin main
```

### Étape 2 : Créer le Workflow GitHub Actions

Créez le fichier `.github/workflows/deploy.yml` :

```yaml
name: 🚀 Build and Deploy MPPEEP

on:
  push:
    branches:
      - main  # Deploy automatique sur push main
    tags:
      - 'v*'  # Deploy sur tag (v1.0.0, v1.1.0...)
  
  workflow_dispatch:  # Permet de lancer manuellement

env:
  DOCKER_IMAGE: votreusername/mppeep
  
jobs:
  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  # JOB 1 : Build et Push l'image Docker
  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  build:
    name: 🏗️ Build Docker Image
    runs-on: ubuntu-latest
    
    steps:
      - name: 📥 Checkout code
        uses: actions/checkout@v4
      
      - name: 🐳 Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: 🔐 Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      
      - name: 🏷️ Extract version
        id: meta
        run: |
          # Si c'est un tag (v1.2.0), utiliser ce tag
          # Sinon, utiliser "latest"
          if [[ $GITHUB_REF == refs/tags/* ]]; then
            VERSION=${GITHUB_REF#refs/tags/}
          else
            VERSION=latest
          fi
          echo "version=$VERSION" >> $GITHUB_OUTPUT
          echo "date=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" >> $GITHUB_OUTPUT
      
      - name: 🏗️ Build and Push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile.prod
          push: true
          tags: |
            ${{ env.DOCKER_IMAGE }}:${{ steps.meta.outputs.version }}
            ${{ env.DOCKER_IMAGE }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
          labels: |
            org.opencontainers.image.created=${{ steps.meta.outputs.date }}
            org.opencontainers.image.version=${{ steps.meta.outputs.version }}
      
      - name: ✅ Build Summary
        run: |
          echo "### ✅ Build réussi ! 🎉" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "**Image** : \`${{ env.DOCKER_IMAGE }}:${{ steps.meta.outputs.version }}\`" >> $GITHUB_STEP_SUMMARY
          echo "**Date** : ${{ steps.meta.outputs.date }}" >> $GITHUB_STEP_SUMMARY
  
  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  # JOB 2 : Déploiement sur le serveur
  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  deploy:
    name: 🚢 Deploy to Production
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'  # Seulement sur main
    
    steps:
      - name: 🚀 Deploy via SSH
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.PROD_SERVER_HOST }}
          username: ${{ secrets.PROD_SERVER_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          port: 22
          script: |
            cd ~/mppeep
            
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "🚀 Déploiement MPPEEP Dashboard"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            
            # Arrêter les containers
            echo "📦 Arrêt des containers..."
            docker-compose -f docker-compose.prod.yml down
            
            # Pull la nouvelle image
            echo "⬇️  Téléchargement de la nouvelle image..."
            docker pull ${{ env.DOCKER_IMAGE }}:latest
            
            # Démarrer avec la nouvelle image
            echo "🚀 Démarrage des containers..."
            docker-compose -f docker-compose.prod.yml up -d
            
            # Attendre que l'app démarre
            echo "⏳ Attente du démarrage..."
            sleep 10
            
            # Vérifier la santé
            echo "🏥 Vérification de la santé..."
            docker-compose -f docker-compose.prod.yml ps
            
            # Test du health endpoint
            if curl -f http://localhost:9000/mppeep/api/v1/health; then
              echo "✅ Application déployée avec succès !"
            else
              echo "❌ Erreur : Health check échoué"
              exit 1
            fi
            
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "✅ Déploiement terminé !"
            echo "🌐 URL : https://mppeep.skpartners.consulting/mppeep/"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      
      - name: 📢 Deployment Summary
        run: |
          echo "### 🚀 Déploiement réussi !" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "**URL** : https://mppeep.skpartners.consulting/mppeep/" >> $GITHUB_STEP_SUMMARY
          echo "**Version** : latest" >> $GITHUB_STEP_SUMMARY
```

### Étape 3 : Configurer les Secrets GitHub

Dans GitHub : **Settings → Secrets and variables → Actions**

Ajouter :
```
DOCKER_USERNAME       = votreusername
DOCKER_PASSWORD       = votre-token-docker-hub
PROD_SERVER_HOST      = IP_ou_hostname_serveur
PROD_SERVER_USER      = votre-user-ssh
PROD_SSH_KEY          = votre-clé-privée-ssh
```

### Étape 4 : Modifier docker-compose.prod.yml

```yaml
services:
  app:
    # Utiliser l'image depuis Docker Hub au lieu de builder localement
    image: votreusername/mppeep:latest
    # Supprimer la section build:
    # build:
    #   context: .
    #   dockerfile: Dockerfile.prod
```

### Étape 5 : Workflow Quotidien

```bash
# Sur Machine Dev (Windows)
# 1. Développer votre code
# 2. Tester localement
# 3. Commit et push

git add .
git commit -m "feat: Nouvelle fonctionnalité RH"
git push origin main

# ✅ GitHub Actions se déclenche automatiquement :
#    → Build l'image
#    → Push sur Docker Hub
#    → Se connecte au serveur via SSH
#    → Pull la nouvelle image
#    → Redémarre les containers
#    → Vérifie la santé

# 5-10 minutes plus tard → Application déployée ! 🎉
```

---

## 🏗️ Solution 2 : GitLab CI/CD (Alternative)

Si vous utilisez GitLab :

### .gitlab-ci.yml

```yaml
stages:
  - build
  - deploy

variables:
  DOCKER_IMAGE: $CI_REGISTRY_IMAGE
  DOCKER_TAG: $CI_COMMIT_SHORT_SHA

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STAGE 1 : Build
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
build:
  stage: build
  image: docker:24-dind
  services:
    - docker:24-dind
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - docker build -f Dockerfile.prod -t $DOCKER_IMAGE:$DOCKER_TAG .
    - docker tag $DOCKER_IMAGE:$DOCKER_TAG $DOCKER_IMAGE:latest
    - docker push $DOCKER_IMAGE:$DOCKER_TAG
    - docker push $DOCKER_IMAGE:latest
  only:
    - main
    - tags

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STAGE 2 : Deploy
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
deploy:
  stage: deploy
  image: alpine:latest
  before_script:
    - apk add --no-cache openssh-client
    - eval $(ssh-agent -s)
    - echo "$SSH_PRIVATE_KEY" | tr -d '\r' | ssh-add -
    - mkdir -p ~/.ssh
    - chmod 700 ~/.ssh
    - ssh-keyscan $PROD_SERVER >> ~/.ssh/known_hosts
  script:
    - |
      ssh $PROD_USER@$PROD_SERVER << 'EOF'
        cd ~/mppeep
        docker-compose -f docker-compose.prod.yml down
        docker pull $DOCKER_IMAGE:latest
        docker-compose -f docker-compose.prod.yml up -d
        docker-compose -f docker-compose.prod.yml ps
      EOF
  only:
    - main
```

---

## 🛠️ Solution 3 : Export/Import Manuel (Sans Registry)

### Sur Machine Dev

Ajoutez ces commandes à votre Makefile :

```makefile
# Makefile - Ajout des commandes CI/CD

.PHONY: docker-export-for-deploy
docker-export-for-deploy: ## Exporter l'image pour déploiement
	@Write-Host "==========================================" -ForegroundColor Cyan
	@Write-Host "EXPORT POUR DEPLOIEMENT" -ForegroundColor Yellow
	@Write-Host "==========================================" -ForegroundColor Cyan
	@$$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
	@$$exportFile = "mppeep-$$timestamp.tar"
	@Write-Host "📦 Construction de l'image..." -ForegroundColor White
	docker-compose -f docker-compose.prod.yml build --no-cache
	@Write-Host ""
	@Write-Host "💾 Export de l'image..." -ForegroundColor White
	docker save mppeep:latest -o $$exportFile
	@$$size = [math]::Round((Get-Item $$exportFile).Length / 1MB, 2)
	@Write-Host ""
	@Write-Host "==========================================" -ForegroundColor Cyan
	@Write-Host "EXPORT TERMINE !" -ForegroundColor Green
	@Write-Host "==========================================" -ForegroundColor Cyan
	@Write-Host "Fichier : $$exportFile" -ForegroundColor White
	@Write-Host "Taille  : $${size} MB" -ForegroundColor White
	@Write-Host ""
	@Write-Host "PROCHAINES ETAPES:" -ForegroundColor Yellow
	@Write-Host "1. Transférer vers le serveur:" -ForegroundColor White
	@Write-Host "   scp $$exportFile user@serveur:~/mppeep/" -ForegroundColor Gray
	@Write-Host "2. Sur le serveur:" -ForegroundColor White
	@Write-Host "   cd ~/mppeep" -ForegroundColor Gray
	@Write-Host "   ./deploy.sh $$exportFile" -ForegroundColor Gray
```

### Sur Machine Prod

Créez `deploy.sh` :

```bash
#!/bin/bash
# deploy.sh - Script de déploiement avec fichier .tar

if [ -z "$1" ]; then
    echo "Usage: ./deploy.sh mppeep-YYYYMMDD_HHMMSS.tar"
    exit 1
fi

IMAGE_FILE=$1

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Déploiement MPPEEP Dashboard"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Arrêter les containers
echo "📦 Arrêt des containers..."
docker-compose -f docker-compose.prod.yml down

# 2. Charger la nouvelle image
echo "📥 Chargement de l'image $IMAGE_FILE..."
docker load -i $IMAGE_FILE

# 3. Démarrer
echo "🚀 Démarrage des containers..."
docker-compose -f docker-compose.prod.yml up -d

# 4. Vérifier
echo "✅ Vérification..."
sleep 5
docker-compose -f docker-compose.prod.yml ps

# 5. Test health
if curl -f http://localhost:9000/mppeep/api/v1/health; then
    echo "✅ Déploiement réussi !"
else
    echo "❌ Health check échoué"
    docker-compose -f docker-compose.prod.yml logs --tail=50 app
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

### Workflow Complet

```bash
# ═══════════════════════════════════════════════════
# MACHINE DEV
# ═══════════════════════════════════════════════════

# 1. Développer et tester
# 2. Exporter l'image
make docker-export-for-deploy
# → Crée : mppeep-20251020_235959.tar

# 3. Transférer vers le serveur
scp mppeep-20251020_235959.tar user@serveur:~/mppeep/

# ═══════════════════════════════════════════════════
# MACHINE PROD
# ═══════════════════════════════════════════════════

# 4. Se connecter au serveur
ssh user@serveur

# 5. Déployer
cd ~/mppeep
./deploy.sh mppeep-20251020_235959.tar

# ✅ Application mise à jour !
```

---

## 📊 Comparaison des Solutions

| Aspect | Docker Hub | GitHub Actions | Export/Import |
|--------|-----------|----------------|---------------|
| **Automatisation** | ⚠️ Semi-auto | ✅ Full auto | ❌ Manuel |
| **Complexité** | ⚡ Simple | ⚡⚡ Moyen | ⚡ Très simple |
| **Coût** | ✅ Gratuit | ✅ Gratuit | ✅ Gratuit |
| **Vitesse** | ⚡⚡ Rapide | ⚡⚡⚡ Très rapide | ⚡ Lent (transfert) |
| **Rollback** | ✅ Facile | ✅ Très facile | ⚠️ Difficile |
| **Historique** | ✅ Oui | ✅ Complet | ❌ Non |
| **Tests auto** | ❌ Non | ✅ Oui | ❌ Non |
| **Setup initial** | 5 min | 30 min | 2 min |

---

## 🎯 Recommandation pour Vous

### ⭐ **Solution Recommandée : GitHub Actions + Docker Hub**

**Pourquoi ?**
1. ✅ **Automatique** : git push = déploiement automatique
2. ✅ **Gratuit** : GitHub Actions + Docker Hub Free
3. ✅ **Versionning** : Tags git = versions Docker
4. ✅ **Rollback facile** : Revert git + redeploy
5. ✅ **Tests** : Peut ajouter des tests avant deploy
6. ✅ **Notifications** : Email/Slack si échec

### 🚀 Setup Rapide (30 minutes)

```bash
# 1. Créer compte Docker Hub (5 min)
https://hub.docker.com/signup

# 2. Créer repository sur GitHub (2 min)
# 3. Copier le workflow ci-dessus (5 min)
# 4. Configurer les secrets GitHub (5 min)
# 5. Modifier docker-compose.prod.yml (2 min)
# 6. Git push (1 min)
# 7. ✅ Premier déploiement automatique ! (10 min)
```

**Ensuite** : Chaque `git push` déclenche automatiquement le déploiement ! 🎉

---

## 📝 Fichiers à Créer

Voulez-vous que je crée :

1. ✅ `.github/workflows/deploy.yml` - Workflow GitHub Actions
2. ✅ `deploy.sh` - Script de déploiement pour le serveur
3. ✅ Commandes Makefile pour export/import
4. ✅ Guide de configuration GitHub Secrets

Quelle solution préférez-vous ? GitHub Actions ou Export/Import manuel ?

---

## 💡 Workflow Idéal avec GitHub Actions

```
┌─────────────────────────────────────────────────────────────┐
│  MACHINE DEV (Windows)                                      │
├─────────────────────────────────────────────────────────────┤
│  1. Développer                                              │
│  2. git add . && git commit -m "..."                       │
│  3. git push origin main                                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ Git Push
┌─────────────────────────────────────────────────────────────┐
│  ☁️  GITHUB ACTIONS (CI/CD Automatique)                     │
├─────────────────────────────────────────────────────────────┤
│  1. ✅ Tests (optionnel)                                    │
│  2. 🏗️ Build Docker Image                                   │
│  3. 📤 Push vers Docker Hub                                 │
│  4. 🔐 SSH vers Serveur Prod                                │
│  5. 📥 Pull nouvelle image                                  │
│  6. 🔄 Restart containers                                   │
│  7. 🏥 Health check                                         │
│  8. 📧 Notification (success/fail)                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ Automatique
┌─────────────────────────────────────────────────────────────┐
│  🐳 DOCKER HUB                                              │
│  votreusername/mppeep:latest                               │
│  votreusername/mppeep:v1.2.0                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ Pull
┌─────────────────────────────────────────────────────────────┐
│  MACHINE PROD (Linux Serveur + Cloudflare)                 │
├─────────────────────────────────────────────────────────────┤
│  ✅ Application mise à jour automatiquement !               │
│  🌐 https://mppeep.skpartners.consulting/mppeep/           │
└─────────────────────────────────────────────────────────────┘
```

**Temps total : 5-10 minutes** depuis `git push` jusqu'à déploiement complet ! ⚡

---

**Prêt à mettre en place le CI/CD ?** 🚀

