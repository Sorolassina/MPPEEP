-- scripts/add_valeur_actuelle_to_orientation_and_resultat.sql
-- Ajout du champ valeur_actuelle aux tables orientation_strategique et resultat_strategique

DO $$
BEGIN
    -- Ajouter valeur_actuelle à orientation_strategique
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'orientation_strategique' 
        AND column_name = 'valeur_actuelle'
    ) THEN
        ALTER TABLE orientation_strategique 
        ADD COLUMN valeur_actuelle NUMERIC(15, 2) DEFAULT 0;
    END IF;

    -- Ajouter valeur_actuelle à resultat_strategique
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'resultat_strategique' 
        AND column_name = 'valeur_actuelle'
    ) THEN
        ALTER TABLE resultat_strategique 
        ADD COLUMN valeur_actuelle NUMERIC(15, 2) DEFAULT 0;
    END IF;
END $$;

