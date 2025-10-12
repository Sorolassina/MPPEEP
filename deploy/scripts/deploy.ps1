# Script principal de déploiement
# Usage: .\deploy.ps1 -Environment production

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("development", "staging", "production")]
    [string]$Environment,
    
    [switch]$SkipTests,
    [switch]$SkipBackup,
    [switch]$Force
)

# Couleurs
$ErrorColor = "Red"
$SuccessColor = "Green"
$InfoColor = "Cyan"
$WarningColor = "Yellow"

# Charger la configuration
. "$PSScriptRoot\..\config\environments.ps1"
$config = Get-DeployConfig

Write-Host "`n╔══════════════════════════════════════════════════════════╗" -ForegroundColor $InfoColor
Write-Host "║          🚀 DÉPLOIEMENT - $($config.project.name)          ║" -ForegroundColor $InfoColor
Write-Host "╚══════════════════════════════════════════════════════════╝`n" -ForegroundColor $InfoColor

Write-Host "📋 Configuration:" -ForegroundColor $InfoColor
Write-Host "   Environnement : $Environment"
Write-Host "   Version       : $($config.project.version)"
Write-Host "   Date          : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host ""

# Confirmation en production
if ($Environment -eq "production" -and -not $Force) {
    Write-Host "⚠️  ATTENTION : Déploiement en PRODUCTION !" -ForegroundColor $WarningColor
    $confirm = Read-Host "Êtes-vous sûr ? (oui/non)"
    
    if ($confirm -ne "oui") {
        Write-Host "❌ Déploiement annulé" -ForegroundColor $ErrorColor
        exit 0
    }
}

# Étapes du déploiement
$step = 1

# ========================================
# ÉTAPE 1 : Vérifications préalables
# ========================================
Write-Host "`n[$step] 🔍 Vérifications préalables..." -ForegroundColor $InfoColor
$step++

# Vérifier Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python n'est pas installé ou pas dans le PATH" -ForegroundColor $ErrorColor
    exit 1
}

$pythonVersion = python --version
Write-Host "   ✅ Python trouvé : $pythonVersion" -ForegroundColor $SuccessColor

# Vérifier uv
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "❌ uv n'est pas installé" -ForegroundColor $ErrorColor
    Write-Host "   Installation : pip install uv" -ForegroundColor $WarningColor
    exit 1
}

Write-Host "   ✅ uv trouvé" -ForegroundColor $SuccessColor

# ========================================
# ÉTAPE 2 : Backup (si production)
# ========================================
if ($Environment -eq "production" -and -not $SkipBackup) {
    Write-Host "`n[$step] 💾 Backup de la base de données..." -ForegroundColor $InfoColor
    $step++
    
    $backupPath = $config.deployment.backup_path
    $backupFile = Join-Path $backupPath "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
    
    if (Test-Path $backupPath) {
        # Créer le dossier de backup si nécessaire
        New-Item -ItemType Directory -Force -Path $backupPath | Out-Null
        
        # Copier la base (si SQLite)
        if (Test-Path "app.db") {
            Copy-Item "app.db" $backupFile
            Write-Host "   ✅ Backup créé : $backupFile" -ForegroundColor $SuccessColor
        }
    }
}

# ========================================
# ÉTAPE 3 : Arrêt du service
# ========================================
Write-Host "`n[$step] 🛑 Arrêt du service..." -ForegroundColor $InfoColor
$step++

$serviceName = $config.deployment.service_name

if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
    Stop-Service -Name $serviceName -Force
    Write-Host "   ✅ Service $serviceName arrêté" -ForegroundColor $SuccessColor
}
else {
    Write-Host "   ℹ️  Service $serviceName n'existe pas (sera créé)" -ForegroundColor $WarningColor
}

# ========================================
# ÉTAPE 4 : Mise à jour du code
# ========================================
Write-Host "`n[$step] 📦 Mise à jour du code..." -ForegroundColor $InfoColor
$step++

# Pull depuis Git (si applicable)
if (Test-Path ".git") {
    Write-Host "   📥 Git pull..." -ForegroundColor $InfoColor
    git pull
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Code mis à jour" -ForegroundColor $SuccessColor
    }
    else {
        Write-Host "   ⚠️  Erreur git pull (continuons quand même)" -ForegroundColor $WarningColor
    }
}

# ========================================
# ÉTAPE 5 : Installation des dépendances
# ========================================
Write-Host "`n[$step] 📚 Installation des dépendances..." -ForegroundColor $InfoColor
$step++

uv sync

if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Dépendances installées" -ForegroundColor $SuccessColor
}
else {
    Write-Host "   ❌ Erreur installation dépendances" -ForegroundColor $ErrorColor
    exit 1
}

# ========================================
# ÉTAPE 6 : Génération du fichier .env
# ========================================
Write-Host "`n[$step] ⚙️  Génération du fichier .env..." -ForegroundColor $InfoColor
$step++

New-EnvFile -Environment $Environment -OutputPath ".env"

# ========================================
# ÉTAPE 7 : Migrations base de données
# ========================================
Write-Host "`n[$step] 🗄️  Migrations base de données..." -ForegroundColor $InfoColor
$step++

python -c "from app.db.session import init_db; init_db()"

if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Migrations exécutées" -ForegroundColor $SuccessColor
}
else {
    Write-Host "   ❌ Erreur migrations" -ForegroundColor $ErrorColor
    exit 1
}

# ========================================
# ÉTAPE 8 : Tests (si pas skippés)
# ========================================
if (-not $SkipTests) {
    Write-Host "`n[$step] 🧪 Exécution des tests..." -ForegroundColor $InfoColor
    $step++
    
    pytest tests/unit/ -v
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Tests réussis" -ForegroundColor $SuccessColor
    }
    else {
        Write-Host "   ❌ Tests échoués" -ForegroundColor $ErrorColor
        
        if (-not $Force) {
            Write-Host "   Déploiement annulé (utilisez -Force pour ignorer)" -ForegroundColor $WarningColor
            exit 1
        }
    }
}

# ========================================
# ÉTAPE 9 : Configuration du service Windows
# ========================================
Write-Host "`n[$step] 🔧 Configuration du service Windows..." -ForegroundColor $InfoColor
$step++

& "$PSScriptRoot\setup-service.ps1" -Environment $Environment

# ========================================
# ÉTAPE 10 : Démarrage du service
# ========================================
Write-Host "`n[$step] ▶️  Démarrage du service..." -ForegroundColor $InfoColor
$step++

Start-Service -Name $serviceName

if ($?) {
    Write-Host "   ✅ Service $serviceName démarré" -ForegroundColor $SuccessColor
}
else {
    Write-Host "   ❌ Erreur démarrage service" -ForegroundColor $ErrorColor
    exit 1
}

# ========================================
# ÉTAPE 11 : Vérification de santé
# ========================================
Write-Host "`n[$step] 🏥 Vérification de santé..." -ForegroundColor $InfoColor
$step++

Start-Sleep -Seconds 5  # Attendre que le service démarre

$envConfig = Get-EnvironmentConfig -Environment $Environment
$healthUrl = "http://localhost:$($envConfig.server.port)/api/v1/ping"

try {
    $response = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 10
    
    if ($response.ping -eq "pong") {
        Write-Host "   ✅ Application fonctionne correctement" -ForegroundColor $SuccessColor
    }
}
catch {
    Write-Host "   ⚠️  Health check échoué : $_" -ForegroundColor $WarningColor
}

# ========================================
# RÉSUMÉ
# ========================================
Write-Host "`n╔══════════════════════════════════════════════════════════╗" -ForegroundColor $SuccessColor
Write-Host "║             ✅ DÉPLOIEMENT TERMINÉ !                     ║" -ForegroundColor $SuccessColor
Write-Host "╚══════════════════════════════════════════════════════════╝`n" -ForegroundColor $SuccessColor

Write-Host "📊 Résumé du déploiement :" -ForegroundColor $InfoColor
Write-Host "   Environnement : $Environment"
Write-Host "   Service       : $serviceName"
Write-Host "   Port          : $($envConfig.server.port)"
Write-Host "   Workers       : $($envConfig.server.workers)"
Write-Host "   Database      : $($envConfig.database.type)"
Write-Host ""

if ($envConfig.allowed_hosts) {
    Write-Host "🌐 Domaines autorisés :" -ForegroundColor $InfoColor
    foreach ($host in $envConfig.allowed_hosts) {
        Write-Host "   - $host"
    }
    Write-Host ""
}

Write-Host "🔗 URLs d'accès :" -ForegroundColor $InfoColor
Write-Host "   API      : http://localhost:$($envConfig.server.port)"
Write-Host "   Docs     : http://localhost:$($envConfig.server.port)/docs"
Write-Host "   Health   : http://localhost:$($envConfig.server.port)/api/v1/ping"
Write-Host ""

Write-Host "📝 Commandes utiles :" -ForegroundColor $InfoColor
Write-Host "   Voir les logs     : Get-EventLog -LogName Application -Source $serviceName -Newest 50"
Write-Host "   Redémarrer        : Restart-Service -Name $serviceName"
Write-Host "   Arrêter           : Stop-Service -Name $serviceName"
Write-Host "   Status            : Get-Service -Name $serviceName"
Write-Host ""

