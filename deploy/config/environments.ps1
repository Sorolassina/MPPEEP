# Configuration des environnements pour le déploiement
# Ce fichier définit les variables pour chaque environnement

# Fonction pour charger la configuration JSON
function Get-DeployConfig {
    param(
        [string]$ConfigPath = "$PSScriptRoot\deploy.json"
    )
    
    if (-not (Test-Path $ConfigPath)) {
        Write-Error "❌ Fichier de configuration non trouvé : $ConfigPath"
        exit 1
    }
    
    $config = Get-Content $ConfigPath | ConvertFrom-Json
    return $config
}

# Fonction pour obtenir la config d'un environnement spécifique
function Get-EnvironmentConfig {
    param(
        [Parameter(Mandatory=$true)]
        [ValidateSet("development", "staging", "production")]
        [string]$Environment
    )
    
    $config = Get-DeployConfig
    return $config.environments.$Environment
}

# Fonction pour créer le fichier .env depuis la config
function New-EnvFile {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Environment,
        
        [Parameter(Mandatory=$true)]
        [string]$OutputPath
    )
    
    $config = Get-DeployConfig
    $envConfig = $config.environments.$Environment
    
    # Créer le contenu du fichier .env
    $envContent = @"
# Configuration générée automatiquement pour : $Environment
# Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

# Application
APP_NAME=$($config.project.name)
ENV=$Environment
DEBUG=$($envConfig.debug.ToString().ToLower())
SECRET_KEY=$(New-Guid)

# Base de données
"@

    if ($envConfig.database.type -eq "sqlite") {
        $envContent += "`nDATABASE_URL=sqlite:///$($envConfig.database.path)"
    }
    elseif ($envConfig.database.type -eq "postgresql") {
        $dbPassword = Read-Host "Mot de passe PostgreSQL" -AsSecureString
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($dbPassword)
        $password = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        
        $envContent += @"
`nPOSTGRES_HOST=$($envConfig.database.host)
POSTGRES_PORT=$($envConfig.database.port)
POSTGRES_DB=$($envConfig.database.name)
POSTGRES_USER=$($envConfig.database.user)
POSTGRES_PASSWORD=$password
"@
    }

    # CORS
    if ($envConfig.allowed_hosts) {
        $hosts = $envConfig.allowed_hosts -join ","
        $envContent += "`nALLOWED_HOSTS=$hosts"
    }
    
    $envContent += "`nCORS_ALLOW_ALL=$($envConfig.cors_allow_all.ToString().ToLower())"
    
    # Middlewares
    if ($envConfig.https_redirect) {
        $envContent += "`nENABLE_HTTPS_REDIRECT=$($envConfig.https_redirect.ToString().ToLower())"
    }

    # Sauvegarder
    $envContent | Out-File -FilePath $OutputPath -Encoding UTF8
    
    Write-Host "✅ Fichier .env créé : $OutputPath" -ForegroundColor Green
}

# Exporter les fonctions
Export-ModuleMember -Function Get-DeployConfig, Get-EnvironmentConfig, New-EnvFile

