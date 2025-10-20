# update-docker.ps1 - Script de mise à jour Docker pour MPPEEP Dashboard
# Usage : .\update-docker.ps1

param(
    [switch]$SkipBackup,
    [switch]$NoCache
)

$ErrorActionPreference = "Stop"

Write-Host "`n╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       🔄 MISE À JOUR MPPEEP DASHBOARD (Docker)          ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# ============================================
# 1. BACKUP BASE DE DONNÉES
# ============================================
if (-not $SkipBackup) {
    Write-Host "[1/6] 💾 Backup de la base de données..." -ForegroundColor Yellow
    
    $backupDir = "backups"
    if (-not (Test-Path $backupDir)) {
        New-Item -ItemType Directory -Path $backupDir | Out-Null
    }
    
    $backupFile = Join-Path $backupDir "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"
    
    try {
        docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U mppeep mppeep_prod > $backupFile
        Write-Host "   ✅ Backup créé : $backupFile" -ForegroundColor Green
    }
    catch {
        Write-Host "   ⚠️ Backup échoué (continuons quand même)" -ForegroundColor Yellow
    }
}
else {
    Write-Host "[1/6] ⏭️  Backup ignoré (--SkipBackup)" -ForegroundColor Gray
}

# ============================================
# 2. ARRÊT DE L'APPLICATION
# ============================================
Write-Host "`n[2/6] 🛑 Arrêt de l'application..." -ForegroundColor Yellow

docker-compose -f docker-compose.prod.yml stop app

Write-Host "   ✅ Application arrêtée" -ForegroundColor Green

# ============================================
# 3. RÉCUPÉRATION DU CODE
# ============================================
Write-Host "`n[3/6] 📥 Récupération des mises à jour..." -ForegroundColor Yellow

if (Test-Path ".git") {
    $currentBranch = git branch --show-current
    Write-Host "   Branche actuelle : $currentBranch" -ForegroundColor Gray
    
    git pull origin $currentBranch
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Code mis à jour depuis Git" -ForegroundColor Green
    }
    else {
        Write-Host "   ⚠️ Erreur Git pull" -ForegroundColor Yellow
    }
}
else {
    Write-Host "   ℹ️  Pas de dépôt Git (mise à jour manuelle requise)" -ForegroundColor Gray
}

# ============================================
# 4. RECONSTRUCTION DE L'IMAGE
# ============================================
Write-Host "`n[4/6] 🔨 Reconstruction de l'image Docker..." -ForegroundColor Yellow

$buildArgs = @("build", "app")
if ($NoCache) {
    $buildArgs += "--no-cache"
}

docker-compose -f docker-compose.prod.yml @buildArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Image reconstruite" -ForegroundColor Green
}
else {
    Write-Host "   ❌ Erreur de construction" -ForegroundColor Red
    exit 1
}

# ============================================
# 5. REDÉMARRAGE
# ============================================
Write-Host "`n[5/6] ▶️ Redémarrage de l'application..." -ForegroundColor Yellow

docker-compose -f docker-compose.prod.yml up -d app

Write-Host "   ✅ Application redémarrée" -ForegroundColor Green

# ============================================
# 6. VÉRIFICATION DE SANTÉ
# ============================================
Write-Host "`n[6/6] 🏥 Vérification de santé..." -ForegroundColor Yellow
Write-Host "   Attente du démarrage (15 secondes)..." -ForegroundColor Gray

Start-Sleep -Seconds 15

try {
    $response = Invoke-RestMethod -Uri "http://localhost:9000/api/v1/health" -Method Get -TimeoutSec 10
    
    if ($response.status -eq "healthy") {
        Write-Host "   ✅ Application saine !" -ForegroundColor Green
        Write-Host "   📊 Version : $($response.version)" -ForegroundColor Cyan
        Write-Host "   🗄️  Database : OK" -ForegroundColor Cyan
    }
}
catch {
    Write-Host "   ⚠️ Health check échoué" -ForegroundColor Yellow
    Write-Host "   Vérifiez les logs : docker-compose -f docker-compose.prod.yml logs app" -ForegroundColor Gray
}

# ============================================
# RÉSUMÉ
# ============================================
Write-Host "`n╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║            ✅ MISE À JOUR TERMINÉE !                    ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════╝`n" -ForegroundColor Green

Write-Host "🎯 Commandes utiles :" -ForegroundColor Cyan
Write-Host "   Logs temps réel  : docker-compose -f docker-compose.prod.yml logs -f app"
Write-Host "   Status           : docker-compose -f docker-compose.prod.yml ps"
Write-Host "   Redémarrer       : docker-compose -f docker-compose.prod.yml restart app"
Write-Host "   Arrêter          : docker-compose -f docker-compose.prod.yml down"
Write-Host ""

Write-Host "🌐 Application disponible sur :" -ForegroundColor Cyan
Write-Host "   http://localhost:9000" -ForegroundColor White
Write-Host ""

