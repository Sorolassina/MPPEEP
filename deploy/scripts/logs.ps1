# Script pour voir les logs de l'application

param(
    [int]$Lines = 50,
    [switch]$Follow,
    [string]$LogFile
)

. "$PSScriptRoot\..\config\environments.ps1"
$config = Get-DeployConfig
$serviceName = $config.deployment.service_name

Write-Host "📋 Logs de l'application..." -ForegroundColor Cyan
Write-Host ""

# Dossier de logs
$logPath = Join-Path (Get-Location) "logs"

if (-not $LogFile) {
    # Logs du service NSSM
    if (Test-Path (Join-Path $logPath "service-stdout.log")) {
        $LogFile = Join-Path $logPath "service-stdout.log"
    }
    # Logs de l'application
    elseif (Test-Path (Join-Path $logPath "app.log")) {
        $LogFile = Join-Path $logPath "app.log"
    }
    else {
        # Logs Windows Event
        Write-Host "📋 Logs du service Windows (EventLog)..." -ForegroundColor Cyan
        Get-EventLog -LogName Application -Source $serviceName -Newest $Lines | Format-Table -AutoSize
        return
    }
}

# Afficher les logs
if ($Follow) {
    # Mode suivi (tail -f)
    Write-Host "📋 Suivi des logs : $LogFile" -ForegroundColor Cyan
    Write-Host "   Ctrl+C pour arrêter"
    Write-Host ""
    
    Get-Content $LogFile -Tail $Lines -Wait
}
else {
    # Dernières lignes
    Write-Host "📋 Dernières $Lines lignes : $LogFile" -ForegroundColor Cyan
    Write-Host ""
    
    Get-Content $LogFile -Tail $Lines
}

