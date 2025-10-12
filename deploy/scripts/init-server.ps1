# Script d'initialisation complète du serveur
# À lancer UNE SEULE FOIS lors de la première installation

#Requires -RunAsAdministrator

param(
    [string]$InstallPath = "C:\inetpub\mppeep",
    [switch]$SkipDependencies
)

$ErrorActionPreference = "Stop"

Write-Host "`n╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║      🏗️  INITIALISATION DU SERVEUR                       ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# ========================================
# VÉRIFICATION ADMINISTRATEUR
# ========================================
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ Ce script nécessite les droits administrateur" -ForegroundColor Red
    Write-Host "   Relancez PowerShell en tant qu'Administrateur" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Exécution avec les droits administrateur`n" -ForegroundColor Green

# ========================================
# INSTALLATION DES DÉPENDANCES
# ========================================
if (-not $SkipDependencies) {
    Write-Host "📦 Installation des dépendances système...`n" -ForegroundColor Cyan
    
    # Chocolatey
    if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
        Write-Host "   Installing Chocolatey..." -ForegroundColor Yellow
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        
        Write-Host "   ✅ Chocolatey installé" -ForegroundColor Green
    }
    else {
        Write-Host "   ✅ Chocolatey déjà installé" -ForegroundColor Green
    }
    
    # Python
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Host "   Installation Python 3.11..." -ForegroundColor Yellow
        choco install python --version=3.11.0 -y
        refreshenv
        Write-Host "   ✅ Python installé" -ForegroundColor Green
    }
    else {
        $pythonVersion = python --version
        Write-Host "   ✅ Python déjà installé : $pythonVersion" -ForegroundColor Green
    }
    
    # Git
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Host "   Installation Git..." -ForegroundColor Yellow
        choco install git -y
        refreshenv
        Write-Host "   ✅ Git installé" -ForegroundColor Green
    }
    else {
        Write-Host "   ✅ Git déjà installé" -ForegroundColor Green
    }
    
    # NSSM
    if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
        Write-Host "   Installation NSSM..." -ForegroundColor Yellow
        choco install nssm -y
        refreshenv
        Write-Host "   ✅ NSSM installé" -ForegroundColor Green
    }
    else {
        Write-Host "   ✅ NSSM déjà installé" -ForegroundColor Green
    }
    
    # PostgreSQL
    if (-not (Get-Service -Name postgresql* -ErrorAction SilentlyContinue)) {
        Write-Host "   Installation PostgreSQL 14..." -ForegroundColor Yellow
        choco install postgresql14 -y
        Write-Host "   ✅ PostgreSQL installé" -ForegroundColor Green
        Write-Host "   ⚠️  Noter le mot de passe PostgreSQL !" -ForegroundColor Yellow
    }
    else {
        Write-Host "   ✅ PostgreSQL déjà installé" -ForegroundColor Green
    }
    
    # uv
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "   Installation uv..." -ForegroundColor Yellow
        pip install uv
        Write-Host "   ✅ uv installé" -ForegroundColor Green
    }
    else {
        Write-Host "   ✅ uv déjà installé" -ForegroundColor Green
    }
}

# ========================================
# CRÉATION DES DOSSIERS
# ========================================
Write-Host "`n📁 Création de la structure de dossiers...`n" -ForegroundColor Cyan

$folders = @(
    "C:\inetpub",
    "C:\Backups\mppeep",
    "$InstallPath\logs"
)

foreach ($folder in $folders) {
    if (-not (Test-Path $folder)) {
        New-Item -ItemType Directory -Force -Path $folder | Out-Null
        Write-Host "   ✅ Créé : $folder" -ForegroundColor Green
    }
    else {
        Write-Host "   ✅ Existe : $folder" -ForegroundColor Green
    }
}

# ========================================
# CONFIGURATION POSTGRESQL
# ========================================
Write-Host "`n🗄️  Configuration PostgreSQL...`n" -ForegroundColor Cyan

Write-Host "   Créer la base de données et l'utilisateur :" -ForegroundColor Yellow
Write-Host "   1. Ouvrir pgAdmin ou psql"
Write-Host "   2. Exécuter les commandes SQL suivantes :"
Write-Host ""
Write-Host "   -- Créer l'utilisateur" -ForegroundColor Gray
Write-Host "   CREATE USER mppeep_user WITH PASSWORD 'votre_mot_de_passe';" -ForegroundColor Gray
Write-Host ""
Write-Host "   -- Créer la base de données" -ForegroundColor Gray
Write-Host "   CREATE DATABASE mppeep_prod OWNER mppeep_user;" -ForegroundColor Gray
Write-Host ""
Write-Host "   -- Donner tous les droits" -ForegroundColor Gray
Write-Host "   GRANT ALL PRIVILEGES ON DATABASE mppeep_prod TO mppeep_user;" -ForegroundColor Gray
Write-Host ""

$continue = Read-Host "   Configuration PostgreSQL terminée ? (oui/non)"

if ($continue -ne "oui") {
    Write-Host "`n⚠️  Finalisez la configuration PostgreSQL puis relancez ce script" -ForegroundColor Yellow
    exit 0
}

# ========================================
# CONFIGURATION DU PARE-FEU
# ========================================
Write-Host "`n🔥 Configuration du pare-feu...`n" -ForegroundColor Cyan

$configureFw = Read-Host "   Configurer le pare-feu Windows ? (oui/non)"

if ($configureFw -eq "oui") {
    & "$PSScriptRoot\setup-firewall.ps1"
}

# ========================================
# RÉSUMÉ
# ========================================
Write-Host "`n╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║            ✅ INITIALISATION TERMINÉE !                  ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════╝`n" -ForegroundColor Green

Write-Host "📝 Prochaines étapes :`n" -ForegroundColor Cyan

Write-Host "1. Cloner votre projet (si pas encore fait) :" -ForegroundColor Yellow
Write-Host "   cd C:\inetpub"
Write-Host "   git clone https://github.com/votre-repo/mppeep.git"
Write-Host "   cd mppeep"
Write-Host ""

Write-Host "2. Configurer le déploiement :" -ForegroundColor Yellow
Write-Host "   notepad deploy\config\deploy.json"
Write-Host ""

Write-Host "3. Lancer le déploiement :" -ForegroundColor Yellow
Write-Host "   .\deploy\scripts\deploy.ps1 -Environment production"
Write-Host ""

Write-Host "4. Configurer Cloudflare DNS :" -ForegroundColor Yellow
Write-Host "   .\deploy\scripts\cloudflare-dns.ps1 -Domain mondomaine.com -ServerIP VOTRE_IP"
Write-Host ""

Write-Host "🎉 Serveur prêt pour le déploiement !" -ForegroundColor Green
Write-Host ""

