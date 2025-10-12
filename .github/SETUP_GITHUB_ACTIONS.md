# 🔧 Configuration GitHub Actions - Guide Complet

## 🎯 Objectif

Ce guide vous explique comment activer et configurer GitHub Actions pour votre projet.

---

## ✅ Prérequis

- ✅ Compte GitHub
- ✅ Repository GitHub (public ou privé)
- ✅ Accès Settings du repository

---

## 📋 Étapes de Configuration

### 1️⃣ Activer GitHub Actions

```bash
# 1. Pusher votre code sur GitHub
git remote add origin https://github.com/votre-user/mppeep.git
git branch -M main
git push -u origin main

# 2. Les workflows sont automatiquement détectés dans .github/workflows/
```

✅ **C'est automatique !** Dès que vous pushez, GitHub détecte les `.yml` dans `.github/workflows/`

---

### 2️⃣ Configurer les Secrets

**Aller dans :** `Settings → Secrets and variables → Actions → New repository secret`

#### Secrets Requis

| Secret | Description | Exemple |
|--------|-------------|---------|
| `PROD_HOST` | IP/domaine serveur production | `123.45.67.89` |
| `PROD_USER` | Utilisateur SSH | `deploy` |
| `SSH_PRIVATE_KEY` | Clé privée SSH | Contenu de `~/.ssh/id_rsa` |
| `STAGING_HOST` | IP/domaine serveur staging | `staging.example.com` |
| `STAGING_USER` | Utilisateur SSH staging | `deploy` |

#### Secrets Optionnels (Notifications)

| Secret | Description |
|--------|-------------|
| `SLACK_WEBHOOK` | URL webhook Slack |
| `DISCORD_WEBHOOK` | URL webhook Discord |

---

### 3️⃣ Configurer les Environments

**Aller dans :** `Settings → Environments → New environment`

#### **Environment : staging**

```yaml
Name: staging
Protection rules: Aucune
Deployment branches: develop
```

**Secrets spécifiques :**
- Aucun (utilise les secrets du repo)

---

#### **Environment : production**

```yaml
Name: production
Protection rules:
  ✅ Required reviewers: 1 personne minimum
  ✅ Wait timer: 15 minutes (optionnel)
Deployment branches: main only
```

**But :** Empêche les déploiements accidentels en production

---

### 4️⃣ Générer une Clé SSH

**Sur votre serveur de déploiement :**

```bash
# 1. Générer une paire de clés
ssh-keygen -t rsa -b 4096 -C "github-actions-deploy"

# Sauvegarder dans : /home/deploy/.ssh/id_rsa_github
# Ne PAS mettre de passphrase (pour automatisation)

# 2. Copier la clé publique sur le serveur
cat ~/.ssh/id_rsa_github.pub >> ~/.ssh/authorized_keys

# 3. Tester la connexion
ssh -i ~/.ssh/id_rsa_github deploy@votre-serveur

# 4. Copier la clé privée pour GitHub
cat ~/.ssh/id_rsa_github
# → Copier tout le contenu (-----BEGIN ... END-----)
# → Coller dans GitHub Secret SSH_PRIVATE_KEY
```

---

### 5️⃣ Configurer les Notifications (Optionnel)

#### Slack

```bash
# 1. Aller sur https://api.slack.com/apps
# 2. Créer une App
# 3. Activer "Incoming Webhooks"
# 4. Créer un webhook
# 5. Copier l'URL (https://hooks.slack.com/services/...)
# 6. Ajouter dans GitHub Secrets → SLACK_WEBHOOK
```

#### Discord

```bash
# 1. Aller sur votre serveur Discord
# 2. Paramètres serveur → Intégrations → Webhooks
# 3. Créer un webhook
# 4. Copier l'URL
# 5. Ajouter dans GitHub Secrets → DISCORD_WEBHOOK
```

---

## 🎮 Utilisation

### CI - Tests Automatiques

**Déclenchement automatique :**
```bash
# À chaque push sur main ou develop
git push origin main

# À chaque Pull Request
git checkout -b feat/nouvelle
git push origin feat/nouvelle
# → Créer une PR sur GitHub
```

**Résultat :**
- ✅ Tests lancés automatiquement
- ✅ Badge vert/rouge
- ✅ Blocage PR si tests échouent

---

### CD - Déploiement Staging

**Déclenchement automatique :**
```bash
# Push sur develop
git checkout develop
git merge feat/nouvelle
git push origin develop

# → Déploiement staging automatique
```

**Résultat :**
- ✅ Tests
- ✅ Déploiement staging
- ✅ Health check
- ✅ Notification

---

### CD - Déploiement Production

**Déclenchement MANUEL :**
```bash
# 1. Merger dans main
git checkout main
git merge develop
git push origin main

# 2. Aller sur GitHub
GitHub → Actions → CD - Production → Run workflow

# 3. Saisir "DEPLOY" pour confirmer

# → Déploiement après validation
```

**Résultat :**
- ✅ Validation manuelle
- ✅ Tests complets
- ✅ Scan sécurité
- ✅ Déploiement
- ✅ Health checks
- ✅ Notification

---

## 🐛 Troubleshooting

### ❌ Workflow ne se lance pas

**Solution :**
```bash
# Vérifier que les fichiers sont bien dans .github/workflows/
ls -la .github/workflows/

# Vérifier la syntaxe YAML
# Aller sur GitHub → Actions → Onglet "Workflows"
# Voir les erreurs de syntaxe
```

---

### ❌ SSH Connection Failed

**Erreur :**
```
Permission denied (publickey)
```

**Solution :**
```bash
# 1. Vérifier la clé SSH
ssh -i ~/.ssh/id_rsa_github deploy@serveur

# 2. Vérifier authorized_keys
cat ~/.ssh/authorized_keys
# → Doit contenir la clé publique

# 3. Permissions correctes
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
chmod 600 ~/.ssh/id_rsa_github

# 4. Vérifier le secret GitHub
GitHub → Settings → Secrets → SSH_PRIVATE_KEY
# → Doit contenir TOUTE la clé (-----BEGIN ... END-----)
```

---

### ❌ Tests échouent sur GitHub mais passent en local

**Causes possibles :**

1. **Variables d'environnement manquantes**
```yaml
# Ajouter dans le workflow
env:
  DEBUG: true
  DATABASE_URL: sqlite:///:memory:
```

2. **Dépendances manquantes**
```bash
# Vérifier pyproject.toml
# Vérifier que uv sync installe tout
```

3. **Différence Python version**
```yaml
# Workflow teste Python 3.11 et 3.12
# Tester localement avec les 2 versions
```

---

### ❌ Déploiement échoue

**Health check timeout**
```bash
# 1. Vérifier que l'app démarre
ssh user@serveur
systemctl status mppeep-prod

# 2. Vérifier les logs
journalctl -u mppeep-prod -f

# 3. Augmenter le timeout dans le workflow
run: sleep 30  # au lieu de 15
```

---

## 📊 Vérifier que Tout Fonctionne

### Checklist Complète

```bash
✅ Secrets GitHub configurés
   GitHub → Settings → Secrets
   
✅ Environments créés
   GitHub → Settings → Environments
   
✅ SSH fonctionne
   ssh -i ~/.ssh/id_rsa deploy@serveur
   
✅ Workflows visibles
   GitHub → Actions → Onglet Workflows
   
✅ Tests passent
   git push → GitHub Actions → CI vert
   
✅ Badge README
   [![CI](badge)](lien)
```

---

## 🎓 Liens Utiles

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GitHub Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments)
- [SSH Actions](https://github.com/marketplace/actions/ssh-remote-commands)

---

## 🎉 Résultat Final

Une fois configuré :

```
✅ Tests automatiques à chaque push
✅ Déploiement staging automatique
✅ Déploiement production sécurisé
✅ Notifications Slack/Discord
✅ Badges dans README
✅ Zero configuration supplémentaire
```

**Workflow automatisé de A à Z ! 🚀**

