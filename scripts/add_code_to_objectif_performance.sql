-- scripts/add_code_to_objectif_performance.sql
-- Ajout de la colonne code à la table objectif_performance

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'objectif_performance' 
        AND column_name = 'code'
    ) THEN
        ALTER TABLE objectif_performance 
        ADD COLUMN code VARCHAR(50) NULL;
        
        -- Créer un index sur la colonne code pour améliorer les performances de tri
        CREATE INDEX IF NOT EXISTS idx_objectif_performance_code ON objectif_performance (code);
        
        RAISE NOTICE 'Colonne code ajoutée à la table objectif_performance';
    ELSE
        RAISE NOTICE 'La colonne code existe déjà dans la table objectif_performance';
    END IF;
END $$;

