#!/bin/bash
# ============================================
# Script de backup PostgreSQL Docker
# ============================================

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/mppeep_backup_${TIMESTAMP}.sql"

echo "💾 Backup de la base de données MPPEEP..."

# Créer le dossier de backups
mkdir -p $BACKUP_DIR

# Vérifier que le conteneur DB tourne
if ! docker-compose ps db | grep -q "Up"; then
    echo "❌ Le conteneur de base de données n'est pas démarré"
    echo "   Démarrez-le avec: docker-compose up -d db"
    exit 1
fi

# Effectuer le backup
echo "📦 Création du backup..."
docker-compose exec -T db pg_dump -U postgres mppeep > $BACKUP_FILE

# Compresser
echo "🗜️  Compression..."
gzip $BACKUP_FILE

echo ""
echo "✅ Backup créé avec succès!"
echo "📁 Fichier: ${BACKUP_FILE}.gz"
echo "📊 Taille: $(du -h ${BACKUP_FILE}.gz | cut -f1)"

# Lister les backups
echo ""
echo "📚 Backups disponibles:"
ls -lh $BACKUP_DIR/

# Nettoyer les backups de plus de 30 jours (optionnel)
echo ""
read -p "🧹 Supprimer les backups de plus de 30 jours ? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
    echo "✅ Anciens backups supprimés"
fi

