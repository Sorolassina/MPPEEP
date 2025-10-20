# 🚀 Guide Complet de Déploiement

> Déployer MPPEEP Dashboard sur Windows Server avec Cloudflare

---

## 📊 Architecture de Déploiement

```
┌─────────────────────────────────────────────────────────┐
│                   UTILISATEURS                          │
│          (Navigateur, Mobile, Autre App)                │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS
                     ↓
┌─────────────────────────────────────────────────────────┐
│                 ☁️  CLOUDFLARE                          │
│  • CDN (Cache)                                          │
│  • SSL/TLS (Certificat gratuit)                         │
│  • Protection DDoS                                      │
│  • DNS Management                                       │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS/HTTP
                     ↓
┌─────────────────────────────────────────────────────────┐
│            🖥️  VOTRE SERVEUR WINDOWS                    │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │  🔥 Pare-feu Windows                       │        │
│  │  • Port 8000 (API)                         │        │
│  │  • Port 443 (HTTPS)                        │        │
│  └───────────────────┬────────────────────────┘        │
│                      │                                   │
│  ┌───────────────────┴────────────────────────┐        │
│  │  🔧 Service Windows (NSSM)                 │        │
│  │  • Démarrage automatique                   │        │
│  │  • Gestion des logs                        │        │
│  │  • Redémarrage auto en cas de crash        │        │
│  └───────────────────┬────────────────────────┘        │
│                      │                                   │
│  ┌───────────────────┴────────────────────────┐        │
│  │  🚀 Uvicorn (Serveur ASGI)                 │        │
│  │  • Workers: 4 (production)                 │        │
│  │  • Host: 0.0.0.0                           │        │
│  │  • Port: 8000                              │        │
│  └───────────────────┬────────────────────────┘        │
│                      │                                   │
│  ┌───────────────────┴────────────────────────┐        │
│  │  🐍 FastAPI Application                    │        │
│  │  • Middlewares (CORS, Security, etc.)      │        │
│  │  • Routes API                              │        │
│  │  • Templates                               │        │
│  └───────────────────┬────────────────────────┘        │
│                      │                                   │
│  ┌───────────────────┴────────────────────────┐        │
│  │  🗄️  PostgreSQL                            │        │
│  │  • Base: mppeep_prod                       │        │
│  │  • User: mppeep_user                       │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Structure du Déploiement

```
deploy/
├── 📘 README.md                  ← Documentation complète
├── ⚡ QUICKSTART.md              ← Guide rapide (10 min)
│
├── config/
│   ├── deploy.json               ← Configuration centralisée
│   ├── environments.ps1          ← Gestion environnements
│   └── env.production.template   ← Template .env production
│
└── scripts/
    ├── 🚀 deploy.ps1             ← Déploiement complet
    ├── 🔄 update.ps1             ← Mise à jour rapide
    ├── ⏮️  rollback.ps1           ← Restauration backup
    ├── 🔧 setup-service.ps1      ← Config service Windows
    ├── 🏗️  init-server.ps1        ← Init serveur (une fois)
    ├── 🔥 setup-firewall.ps1     ← Config pare-feu
    ├── ☁️  cloudflare-dns.ps1     ← Config DNS Cloudflare
    ├── 🏥 health-check.ps1       ← Vérification santé
    ├── 📊 monitor.ps1            ← Monitoring
    └── 📋 logs.ps1               ← Consultation logs
```

---

## 🎯 Déploiement Étape par Étape

### Phase 1 : Préparation du Serveur (Une Fois)

#### 1.1 Initialiser le Serveur

```powershell
# PowerShell en Administrateur
cd C:\Temp
git clone https://github.com/votre-repo/mppeep.git
cd mppeep

# Initialisation complète
.\deploy\scripts\init-server.ps1

# Le script installe :
# ✅ Chocolatey
# ✅ Python 3.11
# ✅ Git
# ✅ NSSM
# ✅ PostgreSQL
# ✅ uv
# ✅ Crée les dossiers
```

**Temps : ~15 minutes** (téléchargements inclus)

---

#### 1.2 Configurer PostgreSQL

```sql
-- Ouvrir pgAdmin ou psql
-- Exécuter :

CREATE USER mppeep_user WITH PASSWORD 'VotreMotDePasseSecurise123!';
CREATE DATABASE mppeep_prod OWNER mppeep_user;
GRANT ALL PRIVILEGES ON DATABASE mppeep_prod TO mppeep_user;

-- Vérifier
\l  -- Liste des bases
\du -- Liste des users
```

---

#### 1.3 Configurer le Projet

```powershell
# Éditer la configuration
notepad deploy\config\deploy.json

# Modifier :
{
  "environments": {
    "production": {
      "allowed_hosts": ["votre-domaine.com", "www.votre-domaine.com"]
    }
  },
  "cloudflare": {
    "zone_id": "VOTRE_ZONE_ID",
    "email": "votre@email.com"
  }
}
```

---

### Phase 2 : Premier Déploiement

```powershell
# Déploiement complet
.\deploy\scripts\deploy.ps1 -Environment production

# ✅ Le script fait TOUT automatiquement :
# 1. Vérifie les prérequis
# 2. Crée un backup
# 3. Installe les dépendances
# 4. Génère le fichier .env
# 5. Crée les tables DB
# 6. Lance les tests
# 7. Configure le service Windows
# 8. Démarre le service
# 9. Vérifie la santé
```

**Temps : ~5 minutes**

---

### Phase 3 : Configuration DNS

```powershell
# Configurer Cloudflare
.\deploy\scripts\cloudflare-dns.ps1 `
    -Domain "votre-domaine.com" `
    -ServerIP "45.123.456.789"

# Créé automatiquement :
# ✅ votre-domaine.com → 45.123.456.789
# ✅ www.votre-domaine.com → 45.123.456.789
# ✅ (optionnel) api.votre-domaine.com
```

**Temps : ~2 minutes**

---

### Phase 4 : Configuration SSL (Cloudflare)

**Dans le Dashboard Cloudflare :**

1. **SSL/TLS** → Choisir **"Full (strict)"**
2. **Edge Certificates** → Activer :
   - Always Use HTTPS: ON
   - Automatic HTTPS Rewrites: ON
   - Minimum TLS Version: TLS 1.2

3. **DNS** → Vérifier que les enregistrements sont **Proxied** (nuage orange)

**Temps : ~3 minutes**

---

## 🔄 Opérations Courantes

### Mise à Jour du Code

```powershell
# Mise à jour rapide (changements mineurs)
.\deploy\scripts\update.ps1

# Mise à jour complète (gros changements)
.\deploy\scripts\deploy.ps1 -Environment production
```

---

### Consulter les Logs

```powershell
# Dernières 50 lignes
.\deploy\scripts\logs.ps1

# Mode suivi (tail -f)
.\deploy\scripts\logs.ps1 -Follow

# Dernières 200 lignes
.\deploy\scripts\logs.ps1 -Lines 200
```

---

### Monitoring

```powershell
# Statut complet (une fois)
.\deploy\scripts\monitor.ps1 -Once

# Monitoring continu (rafraîchit toutes les 30s)
.\deploy\scripts\monitor.ps1

# Custom interval
.\deploy\scripts\monitor.ps1 -RefreshInterval 60
```

---

### Redémarrer l'Application

```powershell
# Redémarrage simple
Restart-Service -Name mppeep-api

# Mise à jour + redémarrage
.\deploy\scripts\update.ps1
```

---

### Rollback (Restauration)

```powershell
# En cas de problème après déploiement
.\deploy\scripts\rollback.ps1

# Choisir le backup à restaurer
# Le service est automatiquement redémarré
```

---

## 🛡️ Sécurité en Production

### Checklist Sécurité

- [ ] **DEBUG=false** en production
- [ ] **SECRET_KEY** unique et fort (32+ caractères)
- [ ] **CORS_ALLOW_ALL=false**
- [ ] **ALLOWED_HOSTS** configuré (liste blanche)
- [ ] **HTTPS_REDIRECT=true**
- [ ] Pare-feu Windows configuré
- [ ] PostgreSQL : mot de passe fort
- [ ] PostgreSQL : accès limité (localhost seulement)
- [ ] Cloudflare : Proxy activé (nuage orange)
- [ ] Cloudflare : SSL en mode "Full (strict)"
- [ ] Logs sécurisés (pas de secrets)
- [ ] Backups automatiques activés

---

### Configuration Sécurisée

```powershell
# Générer une SECRET_KEY sécurisée
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Utiliser dans .env
SECRET_KEY=la_cle_generee_ci_dessus
```

---

## 📊 Monitoring et Alertes

### Health Check Automatique

```powershell
# Créer une tâche planifiée (toutes les 5 minutes)
$action = New-ScheduledTaskAction `
    -Execute "PowerShell.exe" `
    -Argument "-File C:\inetpub\mppeep\deploy\scripts\health-check.ps1"

$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 5) `
    -RepetitionDuration ([TimeSpan]::MaxValue)

Register-ScheduledTask `
    -TaskName "MPPEEP Health Check" `
    -Action $action `
    -Trigger $trigger `
    -Description "Vérifie la santé de l'application toutes les 5 minutes"

Write-Host "✅ Tâche planifiée créée : Health Check toutes les 5 minutes"
```

---

### Backup Automatique

```powershell
# Tâche planifiée de backup quotidien (2h du matin)
$action = New-ScheduledTaskAction `
    -Execute "PowerShell.exe" `
    -Argument "-Command `"Copy-Item C:\inetpub\mppeep\app.db C:\Backups\mppeep\backup_`$(Get-Date -Format 'yyyyMMdd').db`""

$trigger = New-ScheduledTaskTrigger -Daily -At "02:00"

Register-ScheduledTask `
    -TaskName "MPPEEP Daily Backup" `
    -Action $action `
    -Trigger $trigger

Write-Host "✅ Backup quotidien configuré (2h du matin)"
```

---

## 🎯 Environnements

### Development (Local)

```
Machine      : Votre PC
Base de données : SQLite (app.db)
Debug        : ON
CORS         : Autorise tout
Workers      : 1
```

**Lancement :**
```powershell
uvicorn app.main:app --reload
```

---

### Staging (Serveur de Test)

```
Machine      : Serveur Windows
Base de données : PostgreSQL (mppeep_staging)
Debug        : OFF
CORS         : staging.mondomaine.com seulement
Workers      : 2
URL          : https://staging.mondomaine.com
```

**Déploiement :**
```powershell
.\deploy\scripts\deploy.ps1 -Environment staging
```

---

### Production (Serveur Live)

```
Machine      : Serveur Windows
Base de données : PostgreSQL (mppeep_prod)
Debug        : OFF
CORS         : mondomaine.com seulement
Workers      : 4
HTTPS        : Redirect activé
URL          : https://mondomaine.com
```

**Déploiement :**
```powershell
.\deploy\scripts\deploy.ps1 -Environment production
```

---

## ☁️ Configuration Cloudflare

### DNS Records

| Type | Name | Content | Proxy | TTL |
|------|------|---------|-------|-----|
| A | @ | 45.123.456.789 | ✅ Proxied | Auto |
| A | www | 45.123.456.789 | ✅ Proxied | Auto |
| A | api | 45.123.456.789 | ✅ Proxied | Auto |
| CNAME | staging | @ | ✅ Proxied | Auto |

---

### Page Rules (Optimisations)

```
1. api.mondomaine.com/*
   - Cache Level: Bypass
   - Security Level: High

2. mondomaine.com/static/*
   - Cache Level: Cache Everything
   - Edge Cache TTL: 1 month
   - Browser Cache TTL: 4 hours

3. *.mondomaine.com/*
   - Always Use HTTPS: ON
   - Automatic HTTPS Rewrites: ON
```

---

### Firewall Rules (Protection)

```
1. Bloquer les pays suspects
   - (Country) not in {FR, BE, CH, CA} → Challenge

2. Rate Limiting
   - /api/v1/login → Max 5 requêtes/minute
   - /api/v1/* → Max 100 requêtes/minute

3. Bot Fight Mode
   - Activer : ON
```

---

## 🔧 Configuration Serveur Windows

### IIS (Optionnel - Si Reverse Proxy)

Si vous voulez utiliser IIS comme reverse proxy :

```powershell
# Installer IIS
Install-WindowsFeature -Name Web-Server -IncludeManagementTools

# Installer URL Rewrite et ARR
choco install urlrewrite -y
choco install iis-arr -y

# Configuration IIS (à adapter)
# ...
```

**Note :** NSSM + Uvicorn direct est plus simple que IIS

---

### Service Windows avec NSSM

**Avantages de NSSM :**
- ✅ Service Windows natif
- ✅ Démarrage automatique
- ✅ Redémarrage auto en cas de crash
- ✅ Gestion des logs
- ✅ Interface graphique : `nssm edit mppeep-api`

**Commandes NSSM :**
```powershell
# Éditer le service
nssm edit mppeep-api

# Voir la config
nssm dump mppeep-api

# Redémarrer
nssm restart mppeep-api

# Supprimer
nssm remove mppeep-api confirm
```

---

## 📈 Performance

### Optimisations Recommandées

#### 1. Uvicorn Workers

```json
"workers": 4  // Production (2 × cores + 1)
```

#### 2. PostgreSQL

```sql
-- Optimisations PostgreSQL
ALTER DATABASE mppeep_prod SET work_mem = '16MB';
ALTER DATABASE mppeep_prod SET maintenance_work_mem = '64MB';
ALTER DATABASE mppeep_prod SET effective_cache_size = '256MB';
```

#### 3. Cloudflare

- ✅ Auto Minify (HTML, CSS, JS)
- ✅ Brotli compression
- ✅ HTTP/3 (QUIC)
- ✅ Early Hints

---

## 🆘 Guide de Dépannage

### Service ne démarre pas

```powershell
# 1. Voir les logs
.\deploy\scripts\logs.ps1

# 2. Tester manuellement
cd C:\inetpub\mppeep
.\.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 3. Vérifier l'erreur exacte
```

**Erreurs courantes :**

| Erreur | Cause | Solution |
|--------|-------|----------|
| Port already in use | Port 8000 occupé | Arrêter l'autre processus |
| Database connection failed | PostgreSQL pas démarré | `Start-Service postgresql-x64-14` |
| Import error | Dépendances manquantes | `uv sync` |
| Permission denied | Droits insuffisants | Lancer en administrateur |

---

### Site inaccessible

```powershell
# 1. Vérifier le service
Get-Service -Name mppeep-api
# Status doit être "Running"

# 2. Tester localement
curl http://localhost:8000/api/v1/ping
# Doit retourner {"ping": "pong"}

# 3. Vérifier le pare-feu
Get-NetFirewallRule -DisplayName "MPPEEP*"

# 4. Vérifier Cloudflare
# Dashboard → DNS → Vérifier les enregistrements
```

---

### Erreur 502 Bad Gateway

```
Cloudflare → Serveur OK
Serveur → Application DOWN
```

**Solutions :**
```powershell
# Redémarrer le service
Restart-Service -Name mppeep-api

# Vérifier les logs
.\deploy\scripts\logs.ps1

# Health check
.\deploy\scripts\health-check.ps1
```

---

## 📅 Planning de Maintenance

### Quotidien (Automatisé)

- ✅ Health check (toutes les 5 min)
- ✅ Backup automatique (2h du matin)
- ✅ Rotation des logs

---

### Hebdomadaire (Manuel)

```powershell
# Lundi matin :

# 1. Vérifier les métriques
.\deploy\scripts\monitor.ps1 -Once

# 2. Analyser les logs
.\deploy\scripts\logs.ps1 -Lines 500 | Select-String "ERROR"

# 3. Vérifier l'espace disque
Get-PSDrive C
```

---

### Mensuel (Manuel)

```powershell
# 1. Mettre à jour les dépendances
.\deploy\scripts\update.ps1

# 2. Nettoyer les anciens backups (garder 30 derniers)
Get-ChildItem C:\Backups\mppeep -Filter "backup_*.db" | 
    Sort-Object LastWriteTime -Descending | 
    Select-Object -Skip 30 | 
    Remove-Item

# 3. Optimiser PostgreSQL
psql -U mppeep_user -d mppeep_prod -c "VACUUM ANALYZE;"

# 4. Vérifier les certificats SSL (Cloudflare les gère, mais vérifier)
```

---

## 📊 Métriques à Surveiller

### Application

- ✅ Temps de réponse API (< 200ms)
- ✅ Taux d'erreur (< 1%)
- ✅ Disponibilité (> 99.9%)

### Serveur

- ✅ CPU (< 70%)
- ✅ RAM (< 80%)
- ✅ Disque (< 80%)
- ✅ Connexions réseau

### Base de Données

- ✅ Taille DB (monitoring)
- ✅ Connexions actives
- ✅ Queries lentes

---

## 🎉 Résultat Final

Après le déploiement complet, vous avez :

### ✅ Infrastructure

- 🖥️ Service Windows (démarrage auto)
- 🗄️ PostgreSQL (base de données)
- ☁️ Cloudflare (CDN + SSL + DNS)
- 🔥 Pare-feu (ports 8000, 443)

### ✅ Monitoring

- 📊 Dashboard monitoring
- 🏥 Health checks automatiques
- 📋 Logs centralisés
- 💾 Backups automatiques

### ✅ URLs Actives

- `https://votre-domaine.com` - Application
- `https://votre-domaine.com/docs` - Documentation API
- `https://votre-domaine.com/api/v1/ping` - Health check
- `https://staging.votre-domaine.com` - Staging (optionnel)

---

## 📚 Ressources

- [README.md](README.md) - Documentation complète
- [QUICKSTART.md](QUICKSTART.md) - Guide rapide 10 min
- [Cloudflare Docs](https://developers.cloudflare.com/)
- [NSSM Docs](https://nssm.cc/)
- [PostgreSQL Windows](https://www.postgresql.org/download/windows/)

---

**🚀 Votre application est maintenant déployée, sécurisée et monitorée !**

