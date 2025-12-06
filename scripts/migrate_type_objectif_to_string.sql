-- Migration: Convertir type_objectif de ENUM à VARCHAR
-- Date: 2025-12-04
-- Description: Convertit la colonne type_objectif de objectif_performance 
--              d'un enum PostgreSQL vers VARCHAR pour stocker des strings

-- Étape 1: Créer une nouvelle colonne temporaire de type VARCHAR
ALTER TABLE objectif_performance 
ADD COLUMN type_objectif_new VARCHAR(50);

-- Étape 2: Copier les données de l'ancienne colonne vers la nouvelle
-- Conversion des valeurs enum en strings
UPDATE objectif_performance 
SET type_objectif_new = CASE 
    WHEN type_objectif::text = 'GLOBAL' THEN 'global'
    WHEN type_objectif::text = 'SPECIFIQUE' THEN 'specifique'
    WHEN type_objectif::text = 'FINANCIER' THEN 'FINANCIER'
    WHEN type_objectif::text = 'RH' THEN 'RH'
    WHEN type_objectif::text = 'QUALITE' THEN 'QUALITE'
    WHEN type_objectif::text = 'CLIENT' THEN 'CLIENT'
    ELSE type_objectif::text
END;

-- Étape 3: Définir une valeur par défaut pour la nouvelle colonne
ALTER TABLE objectif_performance 
ALTER COLUMN type_objectif_new SET DEFAULT 'specifique';

-- Étape 4: Rendre la colonne NOT NULL si nécessaire (après avoir copié les données)
-- Note: Si des valeurs NULL existent, cette étape échouera
-- ALTER TABLE objectif_performance 
-- ALTER COLUMN type_objectif_new SET NOT NULL;

-- Étape 5: Supprimer l'ancienne colonne enum
ALTER TABLE objectif_performance 
DROP COLUMN type_objectif;

-- Étape 6: Renommer la nouvelle colonne
ALTER TABLE objectif_performance 
RENAME COLUMN type_objectif_new TO type_objectif;

-- Étape 7 (Optionnel): Supprimer le type enum s'il n'est plus utilisé ailleurs
-- ATTENTION: Ne le faites que si vous êtes sûr qu'il n'est utilisé nulle part ailleurs
-- DROP TYPE IF EXISTS typeobjectif;

-- Vérification: Afficher la structure de la colonne
SELECT 
    column_name, 
    data_type, 
    character_maximum_length,
    column_default
FROM information_schema.columns 
WHERE table_name = 'objectif_performance' 
AND column_name = 'type_objectif';

