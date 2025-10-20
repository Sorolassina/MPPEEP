# ============================================
# Script d'activation de l'environnement
# MPPEEP Dashboard
# ============================================
# Note: Avec 'uv', l'environnement est géré automatiquement !
# Ce script est fourni pour référence, mais vous n'avez pas besoin
# de l'utiliser si vous utilisez les commandes 'make' ou 'uv run'.
# ============================================

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "🔧 MPPEEP Dashboard - Environnement" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier si uv est installé
Write-Host "📦 Vérification de uv..." -ForegroundColor Yellow
if (!(Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "❌ uv n'est pas installé !" -ForegroundColor Red
    Write-Host ""
    Write-Host "Installation de uv :" -ForegroundColor Yellow
    Write-Host "   pip install uv" -ForegroundColor White
    Write-Host ""
    exit 1
}

$uvVersion = uv --version
Write-Host "✅ $uvVersion" -ForegroundColor Green
Write-Host ""

# Afficher les informations sur l'environnement
Write-Host "🐍 Python (via uv):" -ForegroundColor Yellow
uv run python --version
Write-Host ""

Write-Host "📂 Répertoire de travail:" -ForegroundColor Yellow
Get-Location
Write-Host ""

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "ℹ️  INFORMATION IMPORTANTE" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Avec 'uv', vous n'avez PAS besoin d'activer" -ForegroundColor Yellow
Write-Host "manuellement un environnement virtuel !" -ForegroundColor Yellow
Write-Host ""
Write-Host "Utilisez simplement :" -ForegroundColor Green
Write-Host "   uv run python <script.py>" -ForegroundColor White
Write-Host "   uv run uvicorn app.main:app" -ForegroundColor White
Write-Host "   uv run pytest" -ForegroundColor White
Write-Host ""
Write-Host "Ou encore mieux, utilisez les commandes Make :" -ForegroundColor Green
Write-Host "   make start          # Lancer l'application" -ForegroundColor White
Write-Host "   make test           # Lancer les tests" -ForegroundColor White
Write-Host "   make help           # Voir toutes les commandes" -ForegroundColor White
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "🎯 Variables d'environnement" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Variables d'environnement courantes
$envVars = @(
    @{Name="DEBUG"; Value=$env:DEBUG; Description="Mode debug"},
    @{Name="ENV"; Value=$env:ENV; Description="Environnement (dev/prod)"},
    @{Name="DATABASE_URL"; Value=$env:DATABASE_URL; Description="URL de la base de données"}
)

foreach ($var in $envVars) {
    if ($var.Value) {
        Write-Host "✅ $($var.Name)=" -NoNewline -ForegroundColor Green
        Write-Host "$($var.Value)" -ForegroundColor White
    } else {
        Write-Host "⚪ $($var.Name)=" -NoNewline -ForegroundColor Gray
        Write-Host "(non défini) - $($var.Description)" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "🚀 Commandes disponibles" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "DÉVELOPPEMENT:" -ForegroundColor Yellow
Write-Host "   make start          # Lancer l'app (hot-reload)" -ForegroundColor White
Write-Host "   make stop           # Arrêter l'app" -ForegroundColor White
Write-Host "   make restart        # Redémarrer l'app" -ForegroundColor White
Write-Host ""
Write-Host "TESTS:" -ForegroundColor Yellow
Write-Host "   make test           # Tous les tests" -ForegroundColor White
Write-Host "   make test-unit      # Tests unitaires" -ForegroundColor White
Write-Host "   make test-cov       # Tests avec couverture" -ForegroundColor White
Write-Host ""
Write-Host "BASE DE DONNÉES:" -ForegroundColor Yellow
Write-Host "   make db-init        # Initialiser la DB" -ForegroundColor White
Write-Host "   make db-reset       # Réinitialiser la DB" -ForegroundColor White
Write-Host "   make db-backup      # Sauvegarder la DB" -ForegroundColor White
Write-Host ""
Write-Host "QUALITÉ:" -ForegroundColor Yellow
Write-Host "   make lint           # Vérifier le code" -ForegroundColor White
Write-Host "   make format         # Formater le code" -ForegroundColor White
Write-Host "   make clean-code     # Nettoyage complet" -ForegroundColor White
Write-Host ""
Write-Host "AIDE:" -ForegroundColor Yellow
Write-Host "   make help           # Afficher toutes les commandes" -ForegroundColor White
Write-Host "   make env-check      # Vérifier l'environnement" -ForegroundColor White
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "💡 Guide complet : MAKEFILE_GUIDE.md" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

