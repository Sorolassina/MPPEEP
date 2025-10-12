# 🚀 Déploiement sur Serveur Windows

## 🎯 Vue d'Ensemble

Ce dossier contient tous les scripts PowerShell pour déployer et gérer l'application sur votre propre serveur Windows avec Cloudflare.

### Architecture de Déploiement

```
Internet (Cloudflare CDN)
    ↓
Cloudflare SSL/DNS
    ↓
Votre Serveur Windows
    ↓
Service Windows (NSSM)
    ↓
Uvicorn (FastAPI)
    ↓
PostgreSQL / SQLite
```

---

## 📁 Structure

```
deploy/
├── config/
│   ├── deploy.json           ← Configuration centralisée
│   └── environments.ps1      ← Gestion des environnements
│
└── scripts/
    ├── deploy.ps1            ← 🚀 Déploiement complet
    ├── update.ps1            ← 🔄 Mise à jour rapide
    ├── rollback.ps1          ← ⏮️  Restauration backup
    ├── setup-service.ps1     ← 🔧 Configuration service Windows
    ├── setup-firewall.ps1    ← 🔥 Configuration pare-feu
    ├── cloudflare-dns.ps1    ← ☁️  Configuration DNS Cloudflare
    ├── health-check.ps1      ← 🏥 Vérification santé
    ├── monitor.ps1           ← 📊 Monitoring continu
    └── logs.ps1              ← 📋 Consultation des logs
```

---

## 🚀 Déploiement Initial

### Prérequis

**Sur votre serveur Windows :**

1. ✅ Python 3.11+ installé
2. ✅ Git installé
3. ✅ PostgreSQL installé (pour production)
4. ✅ NSSM installé (recommandé)
5. ✅ PowerShell 5.1+ (intégré Windows)

**Installation NSSM :**
```powershell
# Avec Chocolatey
choco install nssm

# Ou télécharger : https://nssm.cc/download
```

---

### Étape 1 : Configuration Initiale

```powershell
# 1. Cloner le projet sur le serveur
cd C:\inetpub
git clone https://github.com/votre-repo/mppeep.git
cd mppeep

# 2. Modifier la configuration
notepad deploy\config\deploy.json

# Adapter :
# - deployment.install_path
# - deployment.python_path
# - environments.production.database (credentials)
# - environments.production.allowed_hosts (votre domaine)
# - cloudflare.zone_id
```

---

### Étape 2 : Premier Déploiement

```powershell
# Lancer en tant qu'Administrateur
cd C:\inetpub\mppeep

# Déploiement en production
.\deploy\scripts\deploy.ps1 -Environment production

# Ou en staging pour tester
.\deploy\scripts\deploy.ps1 -Environment staging
```

**Le script va :**
1. ✅ Vérifier les prérequis (Python, uv)
2. 💾 Créer un backup (si données existantes)
3. 📦 Installer les dépendances
4. ⚙️  Générer le fichier .env
5. 🗄️  Créer les tables DB
6. 🧪 Lancer les tests
7. 🔧 Créer le service Windows
8. ▶️  Démarrer le service
9. 🏥 Vérifier la santé

---

### Étape 3 : Configuration Cloudflare

```powershell
# Configurer les DNS
.\deploy\scripts\cloudflare-dns.ps1 `
    -Domain "mondomaine.com" `
    -ServerIP "192.168.1.100" `
    -ApiToken "votre_token_cloudflare"

# Le script crée :
# - mondomaine.com → Votre serveur
# - www.mondomaine.com → Votre serveur
# - (optionnel) api.mondomaine.com → Votre serveur
```

**Où trouver votre API Token Cloudflare :**
1. Connexion à Cloudflare
2. Mon profil → API Tokens
3. Créer un token → Edit zone DNS
4. Copier le token

---

### Étape 4 : Configuration Pare-feu

```powershell
# Ouvrir les ports nécessaires
.\deploy\scripts\setup-firewall.ps1 -Port 8000

# Vérifie que le pare-feu autorise :
# - Port 8000 (API)
# - Port 443 (HTTPS)
```

---

## 🔄 Mises à Jour

### Mise à Jour Rapide (Code seulement)

```powershell
# Pour les petits changements
.\deploy\scripts\update.ps1

# Le script va :
# 1. Backup rapide
# 2. Arrêter le service
# 3. Pull du code (git pull)
# 4. Mettre à jour les dépendances
# 5. Lancer les tests
# 6. Redémarrer le service
```

### Mise à Jour Complète

```powershell
# Redéploiement complet
.\deploy\scripts\deploy.ps1 -Environment production

# Options :
# -SkipTests     → Ne pas lancer les tests
# -SkipBackup    → Ne pas faire de backup
# -Force         → Continuer même si tests échouent
```

---

## ⏮️ Rollback (Restauration)

### En Cas de Problème

```powershell
# Restaurer le dernier backup
.\deploy\scripts\rollback.ps1

# Le script affiche les backups disponibles :
# [0] backup_20250108_143000.db - 2025-01-08 14:30:00
# [1] backup_20250107_120000.db - 2025-01-07 12:00:00
#
# Choisir un backup (0-9) : 0

# Ou spécifier directement
.\deploy\scripts\rollback.ps1 -BackupFile "C:\Backups\mppeep\backup_20250108_143000.db"
```

---

## 📊 Monitoring

### Monitoring Continu

```powershell
# Afficher le statut en temps réel
.\deploy\scripts\monitor.ps1

# Rafraîchit toutes les 30 secondes
# Affiche :
# - Statut du service
# - Health check
# - CPU, RAM, Disque
# - Processus Python actifs
# - Connexions réseau
```

### Monitoring Ponctuel

```powershell
# Une seule vérification
.\deploy\scripts\monitor.ps1 -Once
```

### Health Check Automatique

```powershell
# Vérification simple
.\deploy\scripts\health-check.ps1

# Monitoring continu (toutes les 30s)
.\deploy\scripts\health-check.ps1 -Continuous -Interval 30

# Custom URL
.\deploy\scripts\health-check.ps1 -Url "http://monapp.com/api/v1/ping"
```

---

## 📋 Logs

### Consulter les Logs

```powershell
# Dernières 50 lignes
.\deploy\scripts\logs.ps1

# Dernières 100 lignes
.\deploy\scripts\logs.ps1 -Lines 100

# Mode suivi (tail -f)
.\deploy\scripts\logs.ps1 -Follow

# Fichier spécifique
.\deploy\scripts\logs.ps1 -LogFile "C:\inetpub\mppeep\logs\app.log"
```

### Logs Windows Event

```powershell
# Logs du service
Get-EventLog -LogName Application -Source "mppeep-api" -Newest 50

# Filtrer par type
Get-EventLog -LogName Application -Source "mppeep-api" -EntryType Error -Newest 20
```

---

## 🔧 Gestion du Service

### Commandes Utiles

```powershell
# Démarrer
Start-Service -Name mppeep-api

# Arrêter
Stop-Service -Name mppeep-api

# Redémarrer
Restart-Service -Name mppeep-api

# Statut
Get-Service -Name mppeep-api

# Statut détaillé
Get-Service -Name mppeep-api | Format-List *

# Logs du service
Get-EventLog -LogName Application -Source mppeep-api -Newest 50
```

---

## ⚙️ Configuration

### Fichier deploy.json

**Sections principales :**

#### 1. Project

```json
{
  "project": {
    "name": "MPPEEP Dashboard",
    "version": "1.0.0",
    "python_version": "3.11"
  }
}
```

#### 2. Environments

Trois environnements prédéfinis :
- `development` - SQLite, Debug ON, CORS ALL
- `staging` - PostgreSQL, Debug OFF, CORS limité
- `production` - PostgreSQL, Debug OFF, CORS strict, HTTPS

#### 3. Cloudflare

```json
{
  "cloudflare": {
    "enabled": true,
    "zone_id": "VOTRE_ZONE_ID",
    "email": "votre@email.com"
  }
}
```

#### 4. Deployment

```json
{
  "deployment": {
    "service_name": "mppeep-api",
    "install_path": "C:\\inetpub\\mppeep",
    "python_path": "C:\\Python311\\python.exe",
    "backup_enabled": true,
    "backup_path": "C:\\Backups\\mppeep"
  }
}
```

---

## ☁️ Cloudflare

### Configuration DNS

Le script `cloudflare-dns.ps1` crée automatiquement :

```
mondomaine.com          A    192.168.1.100  (Proxied ✅)
www.mondomaine.com      A    192.168.1.100  (Proxied ✅)
api.mondomaine.com      A    192.168.1.100  (Proxied ✅)
```

**Proxied = Passé par Cloudflare** (CDN, SSL, Protection DDoS)

### SSL Automatique

Cloudflare fournit automatiquement :
- ✅ Certificat SSL gratuit
- ✅ HTTPS automatique
- ✅ Redirection HTTP → HTTPS

**Configuration dans Cloudflare Dashboard :**
1. SSL/TLS → Full (strict)
2. Edge Certificates → Always Use HTTPS: ON
3. Speed → Auto Minify: ON (HTML, CSS, JS)

---

## 🔐 Sécurité

### Pare-feu Windows

```powershell
# Configurer automatiquement
.\deploy\scripts\setup-firewall.ps1

# Créé les règles :
# - Port 8000 (API)
# - Port 443 (HTTPS)
```

### SSL/TLS

**Options :**

1. **Cloudflare SSL (Recommandé, Gratuit)**
   - Cloudflare gère le certificat
   - Configuration automatique
   - ✅ Facile

2. **Let's Encrypt**
   - Certificat sur votre serveur
   - Renouvellement manuel/auto
   - ⚠️ Plus complexe

3. **Certificat Commercial**
   - Achat d'un certificat
   - Installation manuelle
   - 💰 Coûteux

**Pour démarrer : Utilisez Cloudflare SSL (gratuit et automatique)**

---

## 📊 Workflows de Déploiement

### Workflow Development

```powershell
# Sur votre machine locale
pytest
git commit -m "Nouvelle fonctionnalité"
git push

# Test local
uvicorn app.main:app --reload
```

---

### Workflow Staging

```powershell
# Sur le serveur de staging
.\deploy\scripts\deploy.ps1 -Environment staging

# Tests manuels
# https://staging.mondomaine.com

# Si OK → Passer en production
```

---

### Workflow Production

```powershell
# Sur le serveur de production
.\deploy\scripts\deploy.ps1 -Environment production

# Monitoring pendant 5 minutes
.\deploy\scripts\monitor.ps1 -Once

# Si problème → Rollback
.\deploy\scripts\rollback.ps1
```

---

## 🆘 Troubleshooting

### Service ne démarre pas

```powershell
# 1. Vérifier les logs
.\deploy\scripts\logs.ps1

# 2. Vérifier le statut
Get-Service -Name mppeep-api

# 3. Essayer de démarrer manuellement
cd C:\inetpub\mppeep
.\.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 4. Voir les erreurs
```

---

### Port déjà utilisé

```powershell
# Trouver quel processus utilise le port 8000
Get-NetTCPConnection -LocalPort 8000

# Tuer le processus
Stop-Process -Id <PID> -Force

# Redémarrer le service
Start-Service -Name mppeep-api
```

---

### Base de données inaccessible

```powershell
# Vérifier PostgreSQL
Get-Service -Name postgresql*

# Démarrer PostgreSQL
Start-Service -Name postgresql-x64-14

# Tester la connexion
psql -U mppeep_user -d mppeep_prod
```

---

### Cloudflare DNS ne fonctionne pas

```powershell
# Vérifier la résolution DNS
nslookup mondomaine.com

# Vérifier dans Cloudflare Dashboard
# DNS → Enregistrements
# Statut : Proxied (nuage orange)
```

---

## 📝 Checklist de Déploiement

### Avant le Premier Déploiement

- [ ] Python 3.11+ installé
- [ ] PostgreSQL installé et configuré
- [ ] NSSM installé
- [ ] Pare-feu Windows configuré
- [ ] Domaine pointé vers le serveur
- [ ] Compte Cloudflare configuré
- [ ] API Token Cloudflare créé
- [ ] `deploy.json` configuré
- [ ] `.env` avec secrets sécurisés

---

### Avant Chaque Déploiement

- [ ] Tests passent localement
- [ ] Code commité et pushé
- [ ] Backup de la base de données
- [ ] Notification aux utilisateurs (si maintenance)
- [ ] Plan de rollback prêt

---

### Après Chaque Déploiement

- [ ] Health check OK
- [ ] Tests de fumée (smoke tests)
- [ ] Vérifier les logs (pas d'erreurs)
- [ ] Monitoring pendant 30 minutes
- [ ] Notification de fin de maintenance

---

## ⚙️ Configuration Multi-Environnements

### Development (Local)

```json
{
  "server": {"host": "localhost", "port": 8000, "workers": 1},
  "database": {"type": "sqlite"},
  "debug": true,
  "cors_allow_all": true
}
```

**Usage :**
```powershell
# Pas de déploiement, juste lancer localement
uvicorn app.main:app --reload
```

---

### Staging (Serveur de Test)

```json
{
  "server": {"host": "0.0.0.0", "port": 8000, "workers": 2},
  "database": {"type": "postgresql", "name": "mppeep_staging"},
  "debug": false,
  "allowed_hosts": ["staging.mondomaine.com"]
}
```

**Usage :**
```powershell
.\deploy\scripts\deploy.ps1 -Environment staging
```

---

### Production (Serveur Live)

```json
{
  "server": {"host": "0.0.0.0", "port": 8000, "workers": 4},
  "database": {"type": "postgresql", "name": "mppeep_prod"},
  "debug": false,
  "allowed_hosts": ["mondomaine.com", "www.mondomaine.com"],
  "https_redirect": true
}
```

**Usage :**
```powershell
.\deploy\scripts\deploy.ps1 -Environment production
```

---

## 🔄 Workflows Complets

### Workflow 1 : Nouvelle Fonctionnalité

```powershell
# === SUR VOTRE MACHINE ===
# 1. Développer
code app/api/v1/endpoints/new_feature.py

# 2. Tester
pytest

# 3. Commit
git add .
git commit -m "feat: nouvelle fonctionnalité"
git push

# === SUR LE SERVEUR ===
# 4. Déployer en staging
.\deploy\scripts\deploy.ps1 -Environment staging

# 5. Tester manuellement
# https://staging.mondomaine.com

# 6. Si OK → Production
.\deploy\scripts\deploy.ps1 -Environment production

# 7. Monitoring
.\deploy\scripts\monitor.ps1
```

---

### Workflow 2 : Hotfix Urgent

```powershell
# 1. Sur le serveur
cd C:\inetpub\mppeep

# 2. Backup d'urgence
Copy-Item app.db "app_emergency_backup.db"

# 3. Fix rapide directement
code app/api/v1/endpoints/probleme.py

# 4. Mise à jour
.\deploy\scripts\update.ps1 -SkipTests

# 5. Vérifier
.\deploy\scripts\health-check.ps1

# 6. Commit le fix (après validation)
git add .
git commit -m "hotfix: correction bug critique"
git push
```

---

### Workflow 3 : Problème en Production

```powershell
# 1. Vérifier les logs
.\deploy\scripts\logs.ps1

# 2. Monitoring
.\deploy\scripts\monitor.ps1 -Once

# 3. Si problème grave → Rollback
.\deploy\scripts\rollback.ps1

# 4. Le service est restauré avec le dernier backup fonctionnel

# 5. Investiguer le problème offline
git log -5
git diff HEAD~1
```

---

## 🎯 Bonnes Pratiques

### ✅ DO (À Faire)

1. **Toujours tester en staging d'abord**
   ```powershell
   .\deploy\scripts\deploy.ps1 -Environment staging
   # Puis si OK →
   .\deploy\scripts\deploy.ps1 -Environment production
   ```

2. **Backups automatiques**
   ```json
   "backup_enabled": true  // Dans deploy.json
   ```

3. **Monitoring après déploiement**
   ```powershell
   # Surveiller pendant 30 minutes
   .\deploy\scripts\monitor.ps1
   ```

4. **Logs rotatifs**
   ```powershell
   # NSSM gère automatiquement la rotation
   # Fichiers de 1MB max
   ```

---

### ❌ DON'T (À Éviter)

1. **❌ Déployer sans tests**
   ```powershell
   # Toujours lancer les tests sauf urgence
   .\deploy\scripts\deploy.ps1 -SkipTests  # Éviter
   ```

2. **❌ Déployer en production sans staging**
   ```powershell
   # Toujours tester en staging d'abord !
   ```

3. **❌ Pas de backup en production**
   ```powershell
   # Ne JAMAIS skip le backup en prod
   .\deploy\scripts\deploy.ps1 -SkipBackup  # DANGEREUX
   ```

---

## 📈 Optimisations

### Workers Uvicorn

```json
"workers": 4  // Production
"workers": 2  // Staging
"workers": 1  // Development
```

**Règle :** `workers = (2 × CPU cores) + 1`

Serveur avec 2 cores → 5 workers optimal

---

### Cache Cloudflare

**Dans Cloudflare Dashboard :**
1. Caching → Configuration
2. Caching Level: Standard
3. Browser Cache TTL: 4 hours
4. Edge Cache TTL: 2 hours

**Pour les API :**
- Créer Page Rules :
  - `api.mondomaine.com/*` → Cache Level: Bypass
  - `mondomaine.com/static/*` → Cache Level: Cache Everything

---

## 🔒 Sécurité Production

### Checklist Sécurité

- [ ] DEBUG=false en production
- [ ] SECRET_KEY unique et fort
- [ ] CORS_ALLOW_ALL=false
- [ ] ALLOWED_HOSTS configuré (liste blanche)
- [ ] HTTPS redirect activé
- [ ] Pare-feu configuré
- [ ] Cloudflare protection DDoS activée
- [ ] Rate limiting activé (middlewares)
- [ ] Mots de passe PostgreSQL forts
- [ ] Logs sécurisés (pas de mots de passe)

---

## 📊 Monitoring Recommandé

### Vérifications Quotidiennes

```powershell
# Script à lancer chaque jour
.\deploy\scripts\health-check.ps1
.\deploy\scripts\monitor.ps1 -Once
```

### Alertes (À Configurer)

**Options :**
1. Email (SMTP)
2. Slack webhook
3. Discord webhook
4. SMS (Twilio)

**Exemple avec email :**
```powershell
# Dans health-check.ps1
if (-not $healthy) {
    Send-MailMessage `
        -To "admin@example.com" `
        -From "monitoring@example.com" `
        -Subject "🚨 Application DOWN" `
        -Body "L'application ne répond pas !" `
        -SmtpServer "smtp.gmail.com" `
        -Port 587 `
        -UseSsl
}
```

---

## 📚 Ressources

### Documentation

- [NSSM Documentation](https://nssm.cc/)
- [Cloudflare API](https://developers.cloudflare.com/api/)
- [PowerShell Services](https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.management/new-service)
- [Uvicorn Deployment](https://www.uvicorn.org/deployment/)

### Outils Utiles

- **NSSM** - Service Manager
- **Cloudflare** - CDN + SSL
- **PostgreSQL** - Base de données
- **Git** - Versioning

---

## ✨ Résumé

| Script | Rôle | Quand |
|--------|------|-------|
| `deploy.ps1` | Déploiement complet | Premier déploiement, gros changements |
| `update.ps1` | Mise à jour rapide | Petits changements de code |
| `rollback.ps1` | Restauration | Problème après déploiement |
| `setup-service.ps1` | Config service Windows | Installation initiale |
| `setup-firewall.ps1` | Config pare-feu | Installation initiale |
| `cloudflare-dns.ps1` | Config DNS | Installation initiale |
| `health-check.ps1` | Vérification santé | Monitoring |
| `monitor.ps1` | Monitoring complet | Surveillance continue |
| `logs.ps1` | Consultation logs | Debug, investigation |

---

**🚀 Système de déploiement complet et professionnel pour Windows Server + Cloudflare !**

