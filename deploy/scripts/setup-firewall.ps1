# Script pour configurer le pare-feu Windows
# Ouvre les ports nécessaires pour l'application

#Requires -RunAsAdministrator

param(
    [int]$Port = 8000,
    [string]$RuleName = "MPPEEP Dashboard API"
)

Write-Host "`n🔥 Configuration du pare-feu Windows..." -ForegroundColor Cyan

# Vérifier si la règle existe déjà
$existingRule = Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue

if ($existingRule) {
    Write-Host "   ⚠️  Règle existante trouvée, suppression..." -ForegroundColor Yellow
    Remove-NetFirewallRule -DisplayName $RuleName
}

# Créer la règle entrante (Inbound)
New-NetFirewallRule `
    -DisplayName $RuleName `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort $Port `
    -Action Allow `
    -Profile Domain,Private,Public `
    -Description "Autorise le trafic entrant pour $RuleName sur le port $Port"

Write-Host "   ✅ Règle entrante créée : Port $Port (TCP)" -ForegroundColor Green

# Créer la règle sortante (Outbound)
New-NetFirewallRule `
    -DisplayName "$RuleName (Outbound)" `
    -Direction Outbound `
    -Protocol TCP `
    -LocalPort $Port `
    -Action Allow `
    -Profile Domain,Private,Public `
    -Description "Autorise le trafic sortant pour $RuleName sur le port $Port"

Write-Host "   ✅ Règle sortante créée : Port $Port (TCP)" -ForegroundColor Green

# Règle pour HTTPS (443) si production
$httpsPort = 443
$httpsRule = Get-NetFirewallRule -DisplayName "$RuleName (HTTPS)" -ErrorAction SilentlyContinue

if (-not $httpsRule) {
    New-NetFirewallRule `
        -DisplayName "$RuleName (HTTPS)" `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort $httpsPort `
        -Action Allow `
        -Profile Domain,Private,Public `
        -Description "Autorise HTTPS pour $RuleName"
    
    Write-Host "   ✅ Règle HTTPS créée : Port $httpsPort (TCP)" -ForegroundColor Green
}

Write-Host "`n✅ Pare-feu configuré !" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Règles créées :" -ForegroundColor Cyan
Write-Host "   - $RuleName (Port $Port)"
Write-Host "   - $RuleName (HTTPS) (Port 443)"
Write-Host ""
Write-Host "🔧 Vérifier les règles :" -ForegroundColor Cyan
Write-Host "   Get-NetFirewallRule -DisplayName '$RuleName'"
Write-Host ""

