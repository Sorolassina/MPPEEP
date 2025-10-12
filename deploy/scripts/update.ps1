# Script de mise à jour rapide (sans réinstallation complète)
# Pour les petits changements de code

param(
    [switch]$SkipTests,
    [switch]$SkipBackup
)

#Requires -RunAsAdministrator

. "$PSScriptRoot\..\config\environments.ps1"
$config = Get-DeployConfig
$serviceName = $config.deployment.service_name

Write-Host "`n🔄 Mise à jour rapide..." -ForegroundColor Cyan

# 1. Backup rapide
if (-not $SkipBackup) {
    if (Test-Path "app.db") {
        $backupFile = "app_before_update_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
        Copy-Item "app.db" $backupFile
        Write-Host "✅ Backup : $backupFile" -ForegroundColor Green
    }
}

# 2. Arrêter le service
Write-Host "🛑 Arrêt du service..." -ForegroundColor Cyan
Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue

# 3. Pull du code
if (Test-Path ".git") {
    Write-Host "📥 Git pull..." -ForegroundColor Cyan
    git pull
}

# 4. Mise à jour des dépendances (si pyproject.toml modifié)
Write-Host "📚 Vérification des dépendances..." -ForegroundColor Cyan
uv sync

# 5. Tests rapides
if (-not $SkipTests) {
    Write-Host "🧪 Tests unitaires..." -ForegroundColor Cyan
    pytest tests/unit/ -q
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Tests échoués !" -ForegroundColor Red
        
        $continue = Read-Host "Continuer quand même ? (oui/non)"
        if ($continue -ne "oui") {
            exit 1
        }
    }
}

# 6. Redémarrer
Write-Host "▶️  Redémarrage du service..." -ForegroundColor Cyan
Start-Service -Name $serviceName

# 7. Vérifier
Start-Sleep -Seconds 5

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/ping" -Method Get -TimeoutSec 10
    
    if ($response.ping -eq "pong") {
        Write-Host "`n✅ Mise à jour réussie !" -ForegroundColor Green
    }
}
catch {
    Write-Host "`n⚠️  Application ne répond pas" -ForegroundColor Yellow
}

Write-Host ""

