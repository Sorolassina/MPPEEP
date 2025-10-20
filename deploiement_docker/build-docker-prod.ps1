# build-docker-prod.ps1 - Construction de l'image Docker pour production
# Usage : .\build-docker-prod.ps1

param(
    [switch]$SaveImage,
    [switch]$NoCache,
    [string]$Tag = "latest"
)

$ErrorActionPreference = "Stop"

Write-Host "`n╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       🏗️  CONSTRUCTION IMAGE DOCKER PRODUCTION          ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

$imageName = "mppeep-dashboard"
$fullTag = "${imageName}:${Tag}"

# ============================================
# 1. VÉRIFICATIONS
# ============================================
Write-Host "[1/5] 🔍 Vérifications..." -ForegroundColor Yellow

# Vérifier Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "   ❌ Docker n'est pas installé" -ForegroundColor Red
    exit 1
}

Write-Host "   ✅ Docker trouvé : $(docker --version)" -ForegroundColor Green

# Vérifier les fichiers nécessaires
$requiredFiles = @("Dockerfile.prod", "requirements.txt", "docker-compose.prod.yml")
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Host "   ❌ Fichier manquant : $file" -ForegroundColor Red
        exit 1
    }
}

Write-Host "   ✅ Tous les fichiers nécessaires sont présents" -ForegroundColor Green

# ============================================
# 2. NETTOYAGE (OPTIONNEL)
# ============================================
Write-Host "`n[2/5] 🧹 Nettoyage des anciennes images..." -ForegroundColor Yellow

# Supprimer les images non utilisées
docker image prune -f | Out-Null

Write-Host "   ✅ Nettoyage terminé" -ForegroundColor Green

# ============================================
# 3. CONSTRUCTION DE L'IMAGE
# ============================================
Write-Host "`n[3/5] 🔨 Construction de l'image Docker..." -ForegroundColor Yellow
Write-Host "   Image : $fullTag" -ForegroundColor Gray
Write-Host "   Fichier : Dockerfile.prod" -ForegroundColor Gray

$buildArgs = @("build", "-f", "Dockerfile.prod", "-t", $fullTag)

if ($NoCache) {
    $buildArgs += "--no-cache"
    Write-Host "   Mode : Sans cache (construction complète)" -ForegroundColor Gray
}
else {
    Write-Host "   Mode : Avec cache (plus rapide)" -ForegroundColor Gray
}

$buildArgs += "."

Write-Host ""
& docker @buildArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n   ✅ Image construite avec succès !" -ForegroundColor Green
}
else {
    Write-Host "`n   ❌ Erreur lors de la construction" -ForegroundColor Red
    exit 1
}

# ============================================
# 4. INFORMATIONS SUR L'IMAGE
# ============================================
Write-Host "`n[4/5] 📊 Informations sur l'image..." -ForegroundColor Yellow

$imageInfo = docker images $imageName --format "{{.Repository}}:{{.Tag}} | Taille: {{.Size}} | Créée: {{.CreatedSince}}"
Write-Host "   $imageInfo" -ForegroundColor Cyan

# ============================================
# 5. SAUVEGARDE (OPTIONNEL)
# ============================================
if ($SaveImage) {
    Write-Host "`n[5/5] 💾 Sauvegarde de l'image..." -ForegroundColor Yellow
    
    $outputDir = "docker-images"
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir | Out-Null
    }
    
    $outputFile = Join-Path $outputDir "${imageName}-${Tag}-$(Get-Date -Format 'yyyyMMdd').tar"
    
    Write-Host "   Fichier : $outputFile" -ForegroundColor Gray
    Write-Host "   (Cela peut prendre quelques minutes...)" -ForegroundColor Gray
    
    docker save $fullTag -o $outputFile
    
    if ($LASTEXITCODE -eq 0) {
        $fileSize = (Get-Item $outputFile).Length / 1MB
        Write-Host "   ✅ Image sauvegardée : $outputFile" -ForegroundColor Green
        Write-Host "   📦 Taille : $([math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan
    }
    else {
        Write-Host "   ❌ Erreur lors de la sauvegarde" -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host "`n[5/5] ⏭️  Sauvegarde ignorée (utilisez -SaveImage pour sauvegarder)" -ForegroundColor Gray
}

# ============================================
# RÉSUMÉ
# ============================================
Write-Host "`n╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║          ✅ CONSTRUCTION TERMINÉE !                     ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════╝`n" -ForegroundColor Green

Write-Host "📋 Résumé :" -ForegroundColor Cyan
Write-Host "   Image : $fullTag" -ForegroundColor White
Write-Host "   Status : Prête pour le déploiement" -ForegroundColor Green

if ($SaveImage) {
    Write-Host "   Fichier : $outputFile" -ForegroundColor White
    Write-Host ""
    Write-Host "📦 Pour transférer sur un autre ordinateur :" -ForegroundColor Cyan
    Write-Host "   1. Copiez le fichier .tar sur l'ordinateur de production"
    Write-Host "   2. Exécutez : docker load -i $outputFile"
    Write-Host "   3. Lancez : docker-compose -f docker-compose.prod.yml up -d"
}

Write-Host ""
Write-Host "🚀 Prochaines étapes :" -ForegroundColor Cyan
Write-Host "   Test local  : docker-compose -f docker-compose.prod.yml up -d"
Write-Host "   Voir logs   : docker-compose -f docker-compose.prod.yml logs -f app"
Write-Host "   Arrêter     : docker-compose -f docker-compose.prod.yml down"
Write-Host ""

if ($SaveImage) {
    Write-Host "💡 Pour déployer sur un autre ordinateur :" -ForegroundColor Yellow
    Write-Host "   Consultez le guide : DEPLOIEMENT_DOCKER_SIMPLE.md"
    Write-Host ""
}

