# Script PowerShell pour lancer l'interface graphique
# Usage: .\lancer_interface.ps1

# Changer vers le répertoire du script
Set-Location $PSScriptRoot

Write-Host "Recherche de Python..." -ForegroundColor Cyan

# Essayer uv en priorite (recommandé pour ce projet)
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "uv trouve, utilisation de uv run python..." -ForegroundColor Green
    Write-Host "Lancement de l'interface MPPEEP Dashboard..." -ForegroundColor Cyan
    uv run python make_gui.py
    if ($LASTEXITCODE -eq 0) {
        exit 0
    }
    Write-Host "uv a echoue, essai d'autres methodes..." -ForegroundColor Yellow
}

# Fonction pour trouver Python
function Find-Python {
    # Essayer python
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return "python"
    }
    
    # Essayer python3
    if (Get-Command python3 -ErrorAction SilentlyContinue) {
        return "python3"
    }
    
    # Essayer py (Python Launcher Windows)
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return "py"
    }
    
    return $null
}

$pythonCmd = Find-Python

if ($pythonCmd) {
    Write-Host "Python trouve via '$pythonCmd'" -ForegroundColor Green
    Write-Host "Lancement de l'interface MPPEEP Dashboard..." -ForegroundColor Cyan
    & $pythonCmd make_gui.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "[ERREUR] L'interface n'a pas pu demarrer." -ForegroundColor Red
        Write-Host "Code d'erreur: $LASTEXITCODE" -ForegroundColor Red
        Read-Host "Appuyez sur Entree pour quitter"
        exit 1
    }
} else {
    Write-Host ""
    Write-Host "[ERREUR] Python n'a pas ete trouve sur ce systeme." -ForegroundColor Red
    Write-Host ""
    Write-Host "Solutions:" -ForegroundColor Yellow
    Write-Host "  1. Installer Python: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "     (Cocher 'Add Python to PATH' lors de l'installation)" -ForegroundColor Gray
    Write-Host "  2. Installer uv: pip install uv" -ForegroundColor Yellow
    Write-Host "  3. Ajouter Python au PATH Windows manuellement" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}


