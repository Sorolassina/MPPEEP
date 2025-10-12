# Script pour créer/mettre à jour le service Windows
# Nécessite l'exécution en tant qu'administrateur

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("development", "staging", "production")]
    [string]$Environment
)

#Requires -RunAsAdministrator

. "$PSScriptRoot\..\config\environments.ps1"

$config = Get-DeployConfig
$envConfig = Get-EnvironmentConfig -Environment $Environment

$serviceName = $config.deployment.service_name
$installPath = $config.deployment.install_path
$pythonPath = $config.deployment.python_path
$venvPath = Join-Path (Get-Location) $config.deployment.venv_path

Write-Host "🔧 Configuration du service Windows..." -ForegroundColor Cyan

# Vérifier si le service existe
$service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue

if ($service) {
    Write-Host "   Service $serviceName existe déjà" -ForegroundColor Yellow
    
    # Arrêter le service
    if ($service.Status -eq "Running") {
        Write-Host "   Arrêt du service..." -ForegroundColor Yellow
        Stop-Service -Name $serviceName -Force
    }
    
    # Supprimer l'ancien service
    Write-Host "   Suppression de l'ancien service..." -ForegroundColor Yellow
    sc.exe delete $serviceName
    Start-Sleep -Seconds 2
}

# Chemin de l'exécutable Python dans le venv
$pythonExe = Join-Path $venvPath "Scripts\python.exe"

# Chemin du script de démarrage
$startScript = Join-Path (Get-Location) "deploy\scripts\start-service.ps1"

# Créer le service Windows avec NSSM (recommandé) ou sc.exe

# Option 1 : Avec NSSM (Non-Sucking Service Manager)
# Installation : choco install nssm
if (Get-Command nssm -ErrorAction SilentlyContinue) {
    Write-Host "   Création du service avec NSSM..." -ForegroundColor Cyan
    
    nssm install $serviceName $pythonExe "-m" "uvicorn" "app.main:app" "--host" $envConfig.server.host "--port" $envConfig.server.port "--workers" $envConfig.server.workers
    
    # Configuration du service
    nssm set $serviceName AppDirectory (Get-Location)
    nssm set $serviceName DisplayName "$($config.project.name) - $Environment"
    nssm set $serviceName Description "API FastAPI pour $($config.project.name)"
    nssm set $serviceName Start SERVICE_AUTO_START
    
    # Logs
    $logPath = Join-Path (Get-Location) "logs"
    New-Item -ItemType Directory -Force -Path $logPath | Out-Null
    
    nssm set $serviceName AppStdout (Join-Path $logPath "service-stdout.log")
    nssm set $serviceName AppStderr (Join-Path $logPath "service-stderr.log")
    nssm set $serviceName AppRotateFiles 1
    nssm set $serviceName AppRotateBytes 1048576  # 1MB
    
    Write-Host "   ✅ Service créé avec NSSM" -ForegroundColor Green
}
else {
    # Option 2 : Avec sc.exe (intégré Windows)
    Write-Host "   ⚠️  NSSM non trouvé, utilisation de sc.exe" -ForegroundColor Yellow
    Write-Host "   Recommandation : Installer NSSM (choco install nssm)" -ForegroundColor Yellow
    
    # Créer un wrapper script
    $wrapperPath = Join-Path (Get-Location) "deploy\scripts\service-wrapper.ps1"
    
    $wrapperContent = @"
Set-Location "$((Get-Location).Path)"
& "$pythonExe" -m uvicorn app.main:app --host $($envConfig.server.host) --port $($envConfig.server.port) --workers $($envConfig.server.workers)
"@
    
    $wrapperContent | Out-File -FilePath $wrapperPath -Encoding UTF8
    
    # Créer le service
    sc.exe create $serviceName binPath= "powershell.exe -ExecutionPolicy Bypass -File `"$wrapperPath`"" start= auto
    
    Write-Host "   ✅ Service créé avec sc.exe" -ForegroundColor Green
}

# Configuration du service
sc.exe config $serviceName start= auto
sc.exe description $serviceName "$($config.project.name) API - $Environment"

Write-Host "`n✅ Service Windows configuré : $serviceName" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Commandes utiles :" -ForegroundColor Cyan
Write-Host "   Start-Service -Name $serviceName"
Write-Host "   Stop-Service -Name $serviceName"
Write-Host "   Restart-Service -Name $serviceName"
Write-Host "   Get-Service -Name $serviceName"
Write-Host ""

