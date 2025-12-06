-- Script SQL pour rendre sous_direction_id obligatoire (NOT NULL) dans la table service
-- 
-- ATTENTION: Vérifiez d'abord qu'il n'y a pas de services sans sous_direction_id
-- 
-- Pour vérifier:
-- SELECT COUNT(*) FROM service WHERE sous_direction_id IS NULL;
-- 
-- Si le résultat est > 0, corrigez d'abord ces services avant d'exécuter ce script

-- Vérifier l'état actuel
SELECT 
    column_name, 
    is_nullable,
    data_type
FROM information_schema.columns 
WHERE table_name = 'service' 
AND column_name = 'sous_direction_id';

-- Vérifier s'il y a des services sans sous_direction_id
SELECT COUNT(*) as services_sans_sous_direction
FROM service 
WHERE sous_direction_id IS NULL;

-- Lister les services sans sous_direction_id (si nécessaire)
-- SELECT id, code, libelle 
-- FROM service 
-- WHERE sous_direction_id IS NULL;

-- Rendre la colonne NOT NULL
-- DÉCOMMENTEZ LA LIGNE SUIVANTE UNIQUEMENT APRÈS AVOIR VÉRIFIÉ QU'IL N'Y A PAS DE SERVICES SANS SOUS_DIRECTION_ID
-- ALTER TABLE service ALTER COLUMN sous_direction_id SET NOT NULL;

