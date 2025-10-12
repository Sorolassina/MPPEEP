#!/bin/bash
# ============================================
# Script de build Docker
# ============================================

set -e

echo "🐳 Build de l'image Docker MPPEEP..."

# Vérifier que nous sommes dans le bon dossier
if [ ! -f "Dockerfile" ]; then
    echo "❌ Erreur: Dockerfile non trouvé. Exécutez depuis la racine du projet."
    exit 1
fi

# Build avec BuildKit pour performance
export DOCKER_BUILDKIT=1

# Version (argument ou latest)
VERSION=${1:-latest}

echo "📦 Version: $VERSION"
echo "🔨 Construction de l'image..."

# Build l'image
docker build \
    --tag mppeep:$VERSION \
    --tag mppeep:latest \
    --file Dockerfile \
    .

echo "✅ Image construite avec succès!"
echo "   - mppeep:$VERSION"
echo "   - mppeep:latest"

# Afficher la taille
echo ""
echo "📊 Taille de l'image:"
docker images mppeep:latest --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

echo ""
echo "🚀 Démarrer avec: docker-compose up -d"

