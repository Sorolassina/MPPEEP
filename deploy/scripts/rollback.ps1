# Script de rollback en cas de problème
# Restaure la dernière sauvegarde

param(
    [string]$BackupFile
)

#Requires -RunAsAdministrator

. "$PSScriptRoot\..\config\environments.ps1"
$config = Get-DeployConfig
$serviceName = $config.deployment.service_name

Write-Host "`n╔══════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║                 ⏮️  ROLLBACK                             ║" -ForegroundColor Yellow
Write-Host "╚══════════════════════════════════════════════════════════╝`n" -ForegroundColor Yellow

# Arrêter le service
Write-Host "🛑 Arrêt du service..." -ForegroundColor Cyan
Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue

# Lister les backups disponibles
$backupPath = $config.deployment.backup_path

if (-not (Test-Path $backupPath)) {
    Write-Host "❌ Aucun dossier de backup trouvé : $backupPath" -ForegroundColor Red
    exit 1
}

$backups = Get-ChildItem -Path $backupPath -Filter "backup_*.db" | Sort-Object LastWriteTime -Descending

if ($backups.Count -eq 0) {
    Write-Host "❌ Aucun backup disponible" -ForegroundColor Red
    exit 1
}

# Choisir le backup
if (-not $BackupFile) {
    Write-Host "📦 Backups disponibles :" -ForegroundColor Cyan
    for ($i = 0; $i -lt [Math]::Min(10, $backups.Count); $i++) {
        $backup = $backups[$i]
        Write-Host "   [$i] $($backup.Name) - $(Get-Date $backup.LastWriteTime -Format 'yyyy-MM-dd HH:mm:ss')"
    }
    
    $choice = Read-Host "`nChoisir un backup (0-$([Math]::Min(9, $backups.Count - 1)))"
    $BackupFile = $backups[$choice].FullName
}

if (-not (Test-Path $BackupFile)) {
    Write-Host "❌ Backup non trouvé : $BackupFile" -ForegroundColor Red
    exit 1
}

# Confirmation
Write-Host "`n⚠️  Vous allez restaurer : $BackupFile" -ForegroundColor Yellow
$confirm = Read-Host "Continuer ? (oui/non)"

if ($confirm -ne "oui") {
    Write-Host "❌ Rollback annulé" -ForegroundColor Red
    exit 0
}

# Restaurer
Write-Host "`n💾 Restauration du backup..." -ForegroundColor Cyan

# Backup de la version actuelle (au cas où)
if (Test-Path "app.db") {
    $emergencyBackup = "app_before_rollback_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
    Copy-Item "app.db" $emergencyBackup
    Write-Host "   📋 Backup de sécurité : $emergencyBackup" -ForegroundColor Yellow
}

# Restaurer
Copy-Item $BackupFile "app.db" -Force

Write-Host "   ✅ Base de données restaurée" -ForegroundColor Green

# Redémarrer le service
Write-Host "`n▶️  Redémarrage du service..." -ForegroundColor Cyan
Start-Service -Name $serviceName

if ($?) {
    Write-Host "   ✅ Service redémarré" -ForegroundColor Green
}

# Vérification
Start-Sleep -Seconds 5

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/ping" -Method Get -TimeoutSec 10
    
    if ($response.ping -eq "pong") {
        Write-Host "`n✅ Rollback réussi - Application fonctionne" -ForegroundColor Green
    }
}
catch {
    Write-Host "`n⚠️  Application ne répond pas : $_" -ForegroundColor Yellow
}

Write-Host ""

