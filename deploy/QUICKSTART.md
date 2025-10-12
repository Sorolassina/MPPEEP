# ⚡ Guide de Démarrage Rapide - Déploiement

> Déployer votre application en 10 minutes

---

## 🎯 Prérequis (Installation Unique)

### Sur Votre Serveur Windows

```powershell
# 1. Installer Chocolatey (gestionnaire de paquets)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 2. Installer les dépendances
choco install python --version=3.11.0 -y
choco install git -y
choco install nssm -y
choco install postgresql14 -y

# 3. Installer uv (gestionnaire Python)
pip install uv

# 4. Redémarrer PowerShell
```

---

## 🚀 Déploiement en 5 Étapes

### Étape 1 : Cloner le Projet (2 min)

```powershell
# Ouvrir PowerShell en Administrateur
cd C:\inetpub
git clone https://github.com/votre-repo/mppeep.git
cd mppeep
```

---

### Étape 2 : Configurer (3 min)

```powershell
# Éditer la configuration
notepad deploy\config\deploy.json

# Modifier :
# 1. "allowed_hosts": ["votre-domaine.com"]
# 2. "zone_id": "VOTRE_ZONE_ID_CLOUDFLARE"
# 3. "email": "votre@email.com"

# Sauvegarder et fermer
```

---

### Étape 3 : Déployer (3 min)

```powershell
# Déploiement automatique
.\deploy\scripts\deploy.ps1 -Environment production

# Entrez les informations demandées :
# - Mot de passe PostgreSQL
# - Confirmation de déploiement
```

**Le script fait tout automatiquement !**

---

### Étape 4 : Configurer Cloudflare (1 min)

```powershell
# Configuration DNS
.\deploy\scripts\cloudflare-dns.ps1 `
    -Domain "votre-domaine.com" `
    -ServerIP "VOTRE_IP_SERVEUR"

# Entrez votre API Token Cloudflare quand demandé
```

---

### Étape 5 : Vérifier (1 min)

```powershell
# Vérification de santé
.\deploy\scripts\health-check.ps1

# Si ✅ HEALTHY → C'est bon !
# Si ❌ DOWN → Voir les logs
```

---

## ✅ Vérifications Post-Déploiement

### 1. Service Windows

```powershell
Get-Service -Name mppeep-api

# Statut : Running ✅
```

### 2. Health Check

```powershell
# Tester localement
curl http://localhost:8000/api/v1/ping

# Tester depuis l'extérieur
curl https://votre-domaine.com/api/v1/ping
```

### 3. Documentation API

```
https://votre-domaine.com/docs
```

### 4. Logs

```powershell
.\deploy\scripts\logs.ps1 -Lines 20

# Pas d'erreurs ? ✅ Tout va bien !
```

---

## 🔄 Mise à Jour Quotidienne

```powershell
# 1. Pull du nouveau code
cd C:\inetpub\mppeep

# 2. Mise à jour rapide
.\deploy\scripts\update.ps1

# 3. Vérification
.\deploy\scripts\health-check.ps1

# Temps total : ~1 minute
```

---

## 📊 Monitoring Quotidien

```powershell
# Afficher le statut
.\deploy\scripts\monitor.ps1 -Once

# Vérifier :
# ✅ Service : Running
# ✅ Health  : HEALTHY
# ✅ CPU     : < 70%
# ✅ RAM     : < 80%
# ✅ Disque  : < 80%
```

---

## 🆘 En Cas de Problème

### Problème Mineur

```powershell
# Redémarrer le service
Restart-Service -Name mppeep-api

# Vérifier
.\deploy\scripts\health-check.ps1
```

### Problème Majeur

```powershell
# Rollback vers le dernier backup
.\deploy\scripts\rollback.ps1

# Choisir le backup le plus récent
# Le service est automatiquement restauré
```

---

## ⏰ Planning de Maintenance

### Quotidien (Automatisé)

```powershell
# Créer une tâche planifiée Windows
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\inetpub\mppeep\deploy\scripts\health-check.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At "08:00"
Register-ScheduledTask -TaskName "MPPEEP Health Check" -Action $action -Trigger $trigger
```

### Hebdomadaire

- 📊 Vérifier les métriques
- 📋 Analyser les logs
- 💾 Vérifier les backups

### Mensuel

- 🔄 Mettre à jour les dépendances
- 🔐 Rotation des secrets
- 📈 Analyser les performances

---

## 🎯 Commandes Essentielles

```powershell
# Déploiement
.\deploy\scripts\deploy.ps1 -Environment production

# Mise à jour rapide
.\deploy\scripts\update.ps1

# Rollback
.\deploy\scripts\rollback.ps1

# Monitoring
.\deploy\scripts\monitor.ps1

# Logs
.\deploy\scripts\logs.ps1 -Follow

# Health check
.\deploy\scripts\health-check.ps1

# Gestion service
Start-Service -Name mppeep-api
Stop-Service -Name mppeep-api
Restart-Service -Name mppeep-api
Get-Service -Name mppeep-api
```

---

## 📞 Support

### Logs Utiles

```powershell
# Logs application
.\deploy\scripts\logs.ps1

# Logs Windows Event
Get-EventLog -LogName Application -Source mppeep-api -Newest 50

# Logs service (si NSSM)
type C:\inetpub\mppeep\logs\service-stdout.log
type C:\inetpub\mppeep\logs\service-stderr.log
```

### Diagnostic

```powershell
# Statut complet
.\deploy\scripts\monitor.ps1 -Once

# Test de connexion DB
python -c "from app.db.session import engine; print(engine.url)"

# Test de l'API
curl http://localhost:8000/docs
```

---

## ✨ Résumé

| Étape | Temps | Commande |
|-------|-------|----------|
| 1. Cloner | 1 min | `git clone ...` |
| 2. Config | 2 min | Éditer `deploy.json` |
| 3. Déployer | 3 min | `.\deploy\scripts\deploy.ps1 -Environment production` |
| 4. DNS | 1 min | `.\cloudflare-dns.ps1 ...` |
| 5. Vérifier | 1 min | `.\health-check.ps1` |

**Total : ~10 minutes** ⚡

---

**🎉 Votre application est maintenant en ligne et accessible au monde entier !**

