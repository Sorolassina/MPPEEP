# Script de monitoring complet de l'application
# Vérifie l'état du service, CPU, mémoire, espace disque

param(
    [int]$RefreshInterval = 30,
    [switch]$Once
)

. "$PSScriptRoot\..\config\environments.ps1"
$config = Get-DeployConfig
$serviceName = $config.deployment.service_name

function Show-ApplicationStatus {
    Clear-Host
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║          📊 MONITORING - $($config.project.name)         ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host "Dernière mise à jour : $timestamp`n" -ForegroundColor Gray
    
    # ========================================
    # SERVICE STATUS
    # ========================================
    Write-Host "🔧 SERVICE" -ForegroundColor Yellow
    
    $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    
    if ($service) {
        $status = $service.Status
        $statusColor = if ($status -eq "Running") { "Green" } else { "Red" }
        
        Write-Host "   Nom    : $serviceName"
        Write-Host "   Statut : $status" -ForegroundColor $statusColor
        Write-Host "   Type   : $($service.StartType)"
    }
    else {
        Write-Host "   ❌ Service non trouvé" -ForegroundColor Red
    }
    
    # ========================================
    # HEALTH CHECK
    # ========================================
    Write-Host "`n🏥 HEALTH CHECK" -ForegroundColor Yellow
    
    try {
        $startTime = Get-Date
        $response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/ping" -Method Get -TimeoutSec 5
        $responseTime = ((Get-Date) - $startTime).TotalMilliseconds
        
        if ($response.ping -eq "pong") {
            Write-Host "   Statut        : " -NoNewline
            Write-Host "✅ HEALTHY" -ForegroundColor Green
            Write-Host "   Temps réponse : $([Math]::Round($responseTime, 2))ms"
        }
    }
    catch {
        Write-Host "   Statut : " -NoNewline
        Write-Host "❌ DOWN" -ForegroundColor Red
        Write-Host "   Erreur : $_"
    }
    
    # ========================================
    # RESSOURCES SYSTÈME
    # ========================================
    Write-Host "`n💻 RESSOURCES SYSTÈME" -ForegroundColor Yellow
    
    # CPU
    $cpu = Get-Counter '\Processor(_Total)\% Processor Time' -ErrorAction SilentlyContinue
    if ($cpu) {
        $cpuUsage = [Math]::Round($cpu.CounterSamples[0].CookedValue, 2)
        $cpuColor = if ($cpuUsage -lt 70) { "Green" } elseif ($cpuUsage -lt 90) { "Yellow" } else { "Red" }
        Write-Host "   CPU   : $cpuUsage%" -ForegroundColor $cpuColor
    }
    
    # Mémoire
    $os = Get-CimInstance Win32_OperatingSystem
    $totalMem = [Math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
    $freeMem = [Math]::Round($os.FreePhysicalMemory / 1MB, 2)
    $usedMem = $totalMem - $freeMem
    $memPercent = [Math]::Round(($usedMem / $totalMem) * 100, 2)
    $memColor = if ($memPercent -lt 70) { "Green" } elseif ($memPercent -lt 90) { "Yellow" } else { "Red" }
    
    Write-Host "   RAM   : $usedMem GB / $totalMem GB ($memPercent%)" -ForegroundColor $memColor
    
    # Disque
    $drive = Get-PSDrive -Name C -ErrorAction SilentlyContinue
    if ($drive) {
        $totalSpace = [Math]::Round($drive.Free / 1GB + $drive.Used / 1GB, 2)
        $freeSpace = [Math]::Round($drive.Free / 1GB, 2)
        $usedSpace = [Math]::Round($drive.Used / 1GB, 2)
        $diskPercent = [Math]::Round(($usedSpace / $totalSpace) * 100, 2)
        $diskColor = if ($diskPercent -lt 70) { "Green" } elseif ($diskPercent -lt 90) { "Yellow" } else { "Red" }
        
        Write-Host "   Disque: $usedSpace GB / $totalSpace GB ($diskPercent%)" -ForegroundColor $diskColor
    }
    
    # ========================================
    # PROCESSUS PYTHON
    # ========================================
    Write-Host "`n🐍 PROCESSUS PYTHON" -ForegroundColor Yellow
    
    $pythonProcesses = Get-Process -Name python* -ErrorAction SilentlyContinue
    
    if ($pythonProcesses) {
        foreach ($proc in $pythonProcesses) {
            $cpuProc = [Math]::Round($proc.CPU, 2)
            $memProc = [Math]::Round($proc.WorkingSet64 / 1MB, 2)
            
            Write-Host "   PID $($proc.Id) - CPU: $cpuProc s, RAM: $memProc MB"
        }
    }
    else {
        Write-Host "   ℹ️  Aucun processus Python actif" -ForegroundColor Gray
    }
    
    # ========================================
    # CONNEXIONS RÉSEAU
    # ========================================
    Write-Host "`n🌐 CONNEXIONS ACTIVES" -ForegroundColor Yellow
    
    $connections = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    
    if ($connections) {
        Write-Host "   Port 8000 : " -NoNewline
        Write-Host "✅ En écoute" -ForegroundColor Green
    }
    else {
        Write-Host "   Port 8000 : " -NoNewline
        Write-Host "❌ Non en écoute" -ForegroundColor Red
    }
    
    # ========================================
    # ESPACE DISQUE BASE DE DONNÉES
    # ========================================
    Write-Host "`n💾 BASE DE DONNÉES" -ForegroundColor Yellow
    
    if (Test-Path "app.db") {
        $dbSize = [Math]::Round((Get-Item "app.db").Length / 1MB, 2)
        Write-Host "   Taille : $dbSize MB"
        Write-Host "   Chemin : $(Resolve-Path 'app.db')"
    }
    else {
        Write-Host "   ℹ️  Fichier app.db non trouvé (PostgreSQL ?)" -ForegroundColor Gray
    }
    
    Write-Host ""
}

# Mode monitoring continu
if (-not $Once) {
    Write-Host "🔄 Mode monitoring continu (Ctrl+C pour arrêter)`n" -ForegroundColor Cyan
    
    while ($true) {
        Show-ApplicationStatus
        Write-Host "⏳ Prochaine mise à jour dans $RefreshInterval secondes..." -ForegroundColor Gray
        Start-Sleep -Seconds $RefreshInterval
    }
}
else {
    # Affichage unique
    Show-ApplicationStatus
}

