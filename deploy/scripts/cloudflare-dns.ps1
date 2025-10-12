# Script pour configurer les DNS Cloudflare
# Nécessite : API Token Cloudflare

param(
    [Parameter(Mandatory=$true)]
    [string]$Domain,
    
    [Parameter(Mandatory=$true)]
    [string]$ServerIP,
    
    [string]$ApiToken,
    [string]$ZoneId
)

. "$PSScriptRoot\..\config\environments.ps1"
$config = Get-DeployConfig

# Récupérer les credentials Cloudflare
if (-not $ApiToken) {
    $ApiToken = Read-Host "API Token Cloudflare"
}

if (-not $ZoneId) {
    $ZoneId = $config.cloudflare.zone_id
    
    if (-not $ZoneId) {
        $ZoneId = Read-Host "Zone ID Cloudflare"
    }
}

Write-Host "`n☁️  Configuration DNS Cloudflare..." -ForegroundColor Cyan
Write-Host "   Domaine   : $Domain"
Write-Host "   IP Serveur: $ServerIP"
Write-Host ""

# Headers pour l'API Cloudflare
$headers = @{
    "Authorization" = "Bearer $ApiToken"
    "Content-Type" = "application/json"
}

# URL de l'API
$apiUrl = "https://api.cloudflare.com/v4/zones/$ZoneId/dns_records"

# Fonction pour créer/mettre à jour un enregistrement DNS
function Set-CloudflareDNS {
    param(
        [string]$Name,
        [string]$Type,
        [string]$Content,
        [bool]$Proxied = $true
    )
    
    Write-Host "   📝 Configuration : $Name ($Type) → $Content" -ForegroundColor Cyan
    
    # Vérifier si l'enregistrement existe
    try {
        $existingRecords = Invoke-RestMethod -Uri "$apiUrl?name=$Name&type=$Type" -Headers $headers -Method Get
        
        if ($existingRecords.result.Count -gt 0) {
            # Mettre à jour
            $recordId = $existingRecords.result[0].id
            
            $body = @{
                type = $Type
                name = $Name
                content = $Content
                ttl = 1  # Auto
                proxied = $Proxied
            } | ConvertTo-Json
            
            $result = Invoke-RestMethod -Uri "$apiUrl/$recordId" -Headers $headers -Method Put -Body $body
            
            if ($result.success) {
                Write-Host "      ✅ Enregistrement mis à jour" -ForegroundColor Green
            }
        }
        else {
            # Créer
            $body = @{
                type = $Type
                name = $Name
                content = $Content
                ttl = 1
                proxied = $Proxied
            } | ConvertTo-Json
            
            $result = Invoke-RestMethod -Uri $apiUrl -Headers $headers -Method Post -Body $body
            
            if ($result.success) {
                Write-Host "      ✅ Enregistrement créé" -ForegroundColor Green
            }
        }
    }
    catch {
        Write-Host "      ❌ Erreur : $_" -ForegroundColor Red
    }
}

# Créer les enregistrements DNS
Write-Host "`n📋 Création des enregistrements DNS..." -ForegroundColor Cyan

# A Record pour le domaine principal
Set-CloudflareDNS -Name $Domain -Type "A" -Content $ServerIP -Proxied $true

# A Record pour www
Set-CloudflareDNS -Name "www.$Domain" -Type "A" -Content $ServerIP -Proxied $true

# A Record pour api (si sous-domaine)
$createApiSubdomain = Read-Host "`nCréer un sous-domaine api.$Domain ? (oui/non)"
if ($createApiSubdomain -eq "oui") {
    Set-CloudflareDNS -Name "api.$Domain" -Type "A" -Content $ServerIP -Proxied $true
}

Write-Host "`n✅ Configuration DNS terminée !" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Domaines configurés :" -ForegroundColor Cyan
Write-Host "   - https://$Domain"
Write-Host "   - https://www.$Domain"

if ($createApiSubdomain -eq "oui") {
    Write-Host "   - https://api.$Domain"
}

Write-Host ""
Write-Host "ℹ️  Note : La propagation DNS peut prendre quelques minutes" -ForegroundColor Yellow
Write-Host ""

