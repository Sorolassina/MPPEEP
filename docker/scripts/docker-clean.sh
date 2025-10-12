#!/bin/bash
# ============================================
# Script de nettoyage Docker
# ============================================

set -e

echo "🧹 Nettoyage Docker pour MPPEEP..."

# Arrêter les conteneurs
echo "⏸️  Arrêt des conteneurs..."
docker-compose down 2>/dev/null || true
docker-compose -f docker-compose.dev.yml down 2>/dev/null || true

# Supprimer les images MPPEEP
echo "🗑️  Suppression des images..."
docker rmi mppeep:latest 2>/dev/null || true
docker rmi $(docker images -q mppeep) 2>/dev/null || true

# Nettoyer les images non utilisées
echo "🧽 Nettoyage des images non utilisées..."
docker image prune -f

# Nettoyer les volumes orphelins (optionnel)
read -p "⚠️  Supprimer les volumes (perte de données DB) ? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker volume rm mppeep-postgres-data 2>/dev/null || true
    docker volume rm mppeep-postgres-dev-data 2>/dev/null || true
    docker volume rm mppeep-pgadmin-data 2>/dev/null || true
    echo "✅ Volumes supprimés"
else
    echo "ℹ️  Volumes conservés"
fi

echo ""
echo "✅ Nettoyage terminé!"
echo "📊 Espace libéré:"
docker system df

