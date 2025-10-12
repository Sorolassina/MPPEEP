# 🔄 CI/CD avec GitHub Actions

## 🎯 Vue d'Ensemble

Ce dossier contient les **workflows GitHub Actions** pour l'automatisation complète : tests, déploiement, monitoring.

### Architecture CI/CD

```
┌─────────────────────────────────────────────────────────┐
│                   DÉVELOPPEUR                           │
└────────────────────┬────────────────────────────────────┘
                     │ git push
                     ↓
┌─────────────────────────────────────────────────────────┐
│                  🐙 GITHUB                              │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │  🧪 CI - Tests Automatiques                │        │
│  │  • Tests unitaires                         │        │
│  │  • Tests intégration                       │        │
│  │  • Tests fonctionnels                      │        │
│  │  • Linting (ruff, black)                   │        │
│  │  • Sécurité (bandit, safety)               │        │
│  │  • Couverture de code                      │        │
│  └────────────────┬───────────────────────────┘        │
│                   │ Si tests ✅                          │
│                   ↓                                      │
│  ┌────────────────────────────────────────────┐        │
│  │  🚀 CD - Déploiement Automatique           │        │
│  │  • Staging (auto sur develop)              │        │
│  │  • Production (manuel + validation)        │        │
│  │  • Health checks                           │        │
│  │  • Rollback auto si erreur                 │        │
│  └────────────────┬───────────────────────────┘        │
│                   │                                      │
└───────────────────┼──────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│              🌍 APPLICATION DÉPLOYÉE                    │
│  • Staging : staging.mondomaine.com                     │
│  • Production : mondomaine.com                          │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Workflows Disponibles

```
.github/workflows/
├── ci.yml               ← 🧪 Tests automatiques (à chaque push)
├── cd-staging.yml       ← 🚀 Déploiement staging (auto)
├── cd-production.yml    ← 🚀 Déploiement production (manuel)
├── schedule.yml         ← ⏰ Tâches planifiées
└── release.yml          ← 📦 Création de releases
```

---

## 🧪 CI - Intégration Continue

### Déclenchement

```yaml
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
```

**Quand ?**
- À chaque `git push` sur `main` ou `develop`
- À chaque Pull Request

---

### Jobs Exécutés

#### 1. **Tests** (3 types)
```
✅ Tests unitaires
✅ Tests d'intégration
✅ Tests fonctionnels
✅ Couverture de code
```

**Matrice :** Python 3.11 et 3.12 (2 versions testées)

---

#### 2. **Linting** (Qualité du code)
```
✅ Ruff (linting)
✅ Black (formatage)
✅ isort (tri imports)
```

**But :** Maintenir la qualité du code

---

#### 3. **Sécurité**
```
✅ Bandit (scan vulnérabilités)
✅ Safety (dépendances vulnérables)
```

**But :** Détecter les failles de sécurité

---

### Résultat

```
✅ Tous les jobs passent
→ Badge vert dans README
→ Pull Request peut être mergée

❌ Un job échoue
→ Badge rouge
→ Pull Request bloquée
→ Notification
```

---

## 🚀 CD - Déploiement Continu

### Staging (Automatique)

**Déclenchement :**
```yaml
on:
  push:
    branches: [ develop ]
```

**Workflow :**
```
1. Push sur develop
   ↓ (automatique)
2. Tests
   ↓ (si ✅)
3. Déploiement staging
   ↓
4. Health check
   ↓
5. Notification
```

**URL :** `https://staging.mondomaine.com`

---

### Production (Manuel avec Validation)

**Déclenchement :**
```yaml
workflow_dispatch:  # Manuel uniquement
```

**Workflow :**
```
1. Clic sur "Run workflow" dans GitHub
   ↓
2. Saisir "DEPLOY" pour confirmer
   ↓
3. Tests complets
   ↓ (si ✅)
4. Scan sécurité
   ↓ (si ✅)
5. Déploiement production
   ↓
6. Health checks (5 tentatives)
   ↓
7. Notification Slack
```

**Sécurité :**
- ⚠️ Nécessite confirmation explicite
- ⚠️ Tests obligatoires avant déploiement
- ⚠️ Rollback auto si health check échoue

---

## ⏰ Tâches Planifiées

### Health Check Quotidien

```yaml
schedule:
  - cron: '0 2 * * *'  # 2h du matin UTC
```

**Actions :**
- Ping de l'application
- Alerte si DOWN
- Rapport quotidien

---

### Vérification Dépendances

**Hebdomadaire :**
- Scan des vulnérabilités
- Liste des dépendances obsolètes
- Rapport de sécurité

---

## 📦 Release Automatique

### Déclenchement

```bash
# Créer un tag
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin v1.2.0
```

**Actions automatiques :**
1. Génère le changelog depuis les commits
2. Crée une GitHub Release
3. Notifie sur Slack
4. Badge de version mis à jour

---

## 🔧 Configuration Requise

### Secrets GitHub

Dans **Settings → Secrets and variables → Actions**, ajouter :

#### Production
```
PROD_HOST          = IP ou domaine de votre serveur
PROD_USER          = Utilisateur SSH
SSH_PRIVATE_KEY    = Clé privée SSH
```

#### Staging
```
STAGING_HOST       = IP serveur staging
STAGING_USER       = Utilisateur SSH
```

#### Notifications (Optionnel)
```
SLACK_WEBHOOK      = URL webhook Slack
DISCORD_WEBHOOK    = URL webhook Discord
```

---

### Environments GitHub

Dans **Settings → Environments**, créer :

#### **staging**
- Protection rules: Aucune
- Deployment branches: `develop`

#### **production**
- Protection rules:
  - ✅ Required reviewers (1 personne minimum)
  - ✅ Wait timer (15 minutes)
- Deployment branches: `main` uniquement

---

## 🎮 Utilisation

### Workflow Développement

```bash
# 1. Créer une branche
git checkout -b feat/nouvelle-fonctionnalite

# 2. Développer
# ...

# 3. Commit
git add .
git commit -m "feat: nouvelle fonctionnalité"

# 4. Push
git push origin feat/nouvelle-fonctionnalite

# → CI lancé automatiquement
# → Tests exécutés
# → Résultat visible dans GitHub
```

---

### Workflow Staging

```bash
# 1. Merger dans develop
git checkout develop
git merge feat/nouvelle-fonctionnalite
git push origin develop

# → CD Staging lancé automatiquement
# → Déploiement sur staging.mondomaine.com
# → Notification quand terminé
```

---

### Workflow Production

```bash
# 1. Merger dans main
git checkout main
git merge develop
git push origin main

# 2. Aller sur GitHub
# Actions → CD - Production → Run workflow

# 3. Saisir "DEPLOY" pour confirmer

# → Tests lancés
# → Déploiement si tests OK
# → Health checks
# → Notification
```

---

## 🎯 Comparaison : CI/CD vs Scripts PowerShell

### Les Deux Systèmes

| Aspect | GitHub Actions (CI/CD) | Scripts PowerShell |
|--------|------------------------|-------------------|
| **Déclenchement** | ✅ Auto (git push) | ❌ Manuel |
| **Tests** | ✅ Auto | ✅ Auto (si lancés) |
| **Déploiement** | ✅ Auto | ❌ Manuel |
| **Plateforme** | ☁️ GitHub (cloud) | 🖥️ Votre serveur |
| **OS** | 🐧 Linux/Mac/Windows | 🪟 Windows seulement |
| **Coût** | 💰 Gratuit (limites) | 💰 Gratuit |
| **Setup** | 📝 YAML | 📝 PowerShell |
| **Backup** | ❌ Non inclus | ✅ Automatique |
| **Rollback** | ⚠️ Complexe | ✅ Simple (1 script) |
| **Monitoring** | ⚠️ Limité | ✅ Complet |

---

## 💡 Approche Recommandée : Hybride

### Utiliser les DEUX !

**GitHub Actions (CI) :**
```
✅ Tests automatiques à chaque push
✅ Linting automatique
✅ Scan sécurité
✅ Validation Pull Requests
```

**Scripts PowerShell (CD) :**
```
✅ Déploiement manuel contrôlé
✅ Backup automatique
✅ Rollback facile
✅ Monitoring local
✅ Service Windows (NSSM)
```

---

### Workflow Hybride Idéal

```
1. DÉVELOPPEMENT
   git push
   ↓
   GitHub Actions → Tests auto ✅
   
2. VALIDATION
   Si tests OK → Notification
   
3. DÉPLOIEMENT (Manuel)
   .\deploy\scripts\deploy.ps1 -Environment production
   ↓
   Backup → Deploy → Health Check ✅
   
4. MONITORING
   .\deploy\scripts\monitor.ps1
```

**Meilleur des deux mondes !**

---

## 📊 Badge pour README

Ajoutez dans votre README.md :

```markdown
# MPPEEP Dashboard

[![CI Tests](https://github.com/votre-user/mppeep/actions/workflows/ci.yml/badge.svg)](https://github.com/votre-user/mppeep/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.118+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
```

**Résultat :**

![CI Tests](https://img.shields.io/badge/tests-passing-green)
![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)

---

## 🆘 Troubleshooting GitHub Actions

### Workflow échoue

```
# Voir les logs détaillés
Actions → Workflow échoué → Cliquer sur le job → Voir les logs
```

### Secrets manquants

```
Error: Secret PROD_HOST not found

Solution :
Settings → Secrets and variables → Actions → New repository secret
```

### SSH ne fonctionne pas

```
# Vérifier la clé SSH
ssh -i ~/.ssh/id_rsa user@serveur

# Ajouter la clé publique sur le serveur
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
```

---

## ✨ Résumé

| Workflow | Déclenchement | Rôle |
|----------|---------------|------|
| `ci.yml` | Push, PR | Tests automatiques |
| `cd-staging.yml` | Push develop | Déploie staging auto |
| `cd-production.yml` | Manuel | Déploie prod avec validation |
| `schedule.yml` | Quotidien | Health checks, rapports |
| `release.yml` | Tag v*.*.* | Crée releases auto |

---

## 🎯 Votre Choix

Vous avez maintenant **DEUX systèmes** :

### Option 1 : Scripts PowerShell (Serveur Windows)
```
✅ Contrôle total
✅ Backup/Rollback faciles
✅ Service Windows (NSSM)
✅ Monitoring local
```

**Usage :**
```powershell
.\deploy\scripts\deploy.ps1 -Environment production
```

---

### Option 2 : GitHub Actions (Cloud)
```
✅ Tests automatiques
✅ CI/CD complet
✅ Multi-plateforme
✅ Gratuit (2000 min/mois)
```

**Usage :**
```bash
git push  # Tests automatiques
# Puis clic "Deploy" dans GitHub
```

---

### Option 3 : Hybride (Recommandé)
```
GitHub Actions : Tests + Validation
PowerShell : Déploiement + Monitoring

Meilleur des deux mondes !
```

---

**🎉 Vous avez maintenant un système CI/CD complet + Scripts de déploiement Windows !**

