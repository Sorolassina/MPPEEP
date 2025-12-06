-- scripts/add_fields_to_indicateur_performance.sql
-- Ajout des colonnes méthode, mode_collecte_donnees et derniere_valeur_connue à la table indicateur_performance

DO $$
BEGIN
    -- Ajouter la colonne methode
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'indicateur_performance' 
        AND column_name = 'methode'
    ) THEN
        ALTER TABLE indicateur_performance 
        ADD COLUMN methode VARCHAR(500) NULL;
        
        RAISE NOTICE 'Colonne methode ajoutée à la table indicateur_performance';
    ELSE
        RAISE NOTICE 'La colonne methode existe déjà dans la table indicateur_performance';
    END IF;

    -- Ajouter la colonne mode_collecte_donnees
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'indicateur_performance' 
        AND column_name = 'mode_collecte_donnees'
    ) THEN
        ALTER TABLE indicateur_performance 
        ADD COLUMN mode_collecte_donnees VARCHAR(50) NULL;
        
        RAISE NOTICE 'Colonne mode_collecte_donnees ajoutée à la table indicateur_performance';
    ELSE
        RAISE NOTICE 'La colonne mode_collecte_donnees existe déjà dans la table indicateur_performance';
    END IF;

    -- Ajouter la colonne derniere_valeur_connue
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'indicateur_performance' 
        AND column_name = 'derniere_valeur_connue'
    ) THEN
        ALTER TABLE indicateur_performance 
        ADD COLUMN derniere_valeur_connue NUMERIC(15, 2) NULL;
        
        RAISE NOTICE 'Colonne derniere_valeur_connue ajoutée à la table indicateur_performance';
    ELSE
        RAISE NOTICE 'La colonne derniere_valeur_connue existe déjà dans la table indicateur_performance';
    END IF;
END $$;

