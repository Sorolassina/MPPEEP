-- scripts/add_cibles_N_plus_to_indicateur_performance.sql
-- Ajout des colonnes cible_N_plus_1 et cible_N_plus_2 à la table indicateur_performance

DO $$
BEGIN
    -- Ajouter la colonne cible_N_plus_1
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'indicateur_performance' 
        AND column_name = 'cible_N_plus_1'
    ) THEN
        ALTER TABLE indicateur_performance 
        ADD COLUMN cible_N_plus_1 NUMERIC(15, 2) NULL;
        
        RAISE NOTICE 'Colonne cible_N_plus_1 ajoutée à la table indicateur_performance';
    ELSE
        RAISE NOTICE 'La colonne cible_N_plus_1 existe déjà dans la table indicateur_performance';
    END IF;

    -- Ajouter la colonne cible_N_plus_2
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'indicateur_performance' 
        AND column_name = 'cible_N_plus_2'
    ) THEN
        ALTER TABLE indicateur_performance 
        ADD COLUMN cible_N_plus_2 NUMERIC(15, 2) NULL;
        
        RAISE NOTICE 'Colonne cible_N_plus_2 ajoutée à la table indicateur_performance';
    ELSE
        RAISE NOTICE 'La colonne cible_N_plus_2 existe déjà dans la table indicateur_performance';
    END IF;
END $$;

