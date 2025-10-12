# Script de vérification de santé de l'application
# Peut être utilisé pour le monitoring

param(
    [string]$Url = "http://localhost:8000/api/v1/ping",
    [int]$Timeout = 10,
    [switch]$Continuous,
    [int]$Interval = 30
)

function Test-ApplicationHealth {
    param([string]$Url, [int]$Timeout)
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    try {
        $startTime = Get-Date
        $response = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec $Timeout
        $duration = ((Get-Date) - $startTime).TotalMilliseconds
        
        if ($response.ping -eq "pong") {
            Write-Host "[$timestamp] ✅ HEALTHY - Response: $([Math]::Round($duration, 2))ms" -ForegroundColor Green
            return $true
        }
        else {
            Write-Host "[$timestamp] ⚠️  WARNING - Réponse inattendue: $response" -ForegroundColor Yellow
            return $false
        }
    }
    catch {
        Write-Host "[$timestamp] ❌ DOWN - Erreur: $_" -ForegroundColor Red
        return $false
    }
}

# Mode continu (monitoring)
if ($Continuous) {
    Write-Host "🏥 Monitoring continu de l'application..." -ForegroundColor Cyan
    Write-Host "   URL      : $Url"
    Write-Host "   Interval : $Interval secondes"
    Write-Host "   Ctrl+C pour arrêter"
    Write-Host ""
    
    $failCount = 0
    
    while ($true) {
        $healthy = Test-ApplicationHealth -Url $Url -Timeout $Timeout
        
        if (-not $healthy) {
            $failCount++
            
            if ($failCount -ge 3) {
                Write-Host "`n🚨 ALERTE : 3 échecs consécutifs !" -ForegroundColor Red
                
                # Optionnel : Envoyer une notification
                # Send-EmailAlert "Application DOWN"
                
                $failCount = 0
            }
        }
        else {
            $failCount = 0
        }
        
        Start-Sleep -Seconds $Interval
    }
}
else {
    # Mode simple (une seule vérification)
    $healthy = Test-ApplicationHealth -Url $Url -Timeout $Timeout
    
    if ($healthy) {
        exit 0
    }
    else {
        exit 1
    }
}

