-- scripts/add_sens_appreciation_to_indicateur_performance.sql
-- Ajouter la colonne sens_appreciation à la table indicateur_performance

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'indicateur_performance' AND column_name = 'sens_appreciation') THEN
        ALTER TABLE indicateur_performance ADD COLUMN sens_appreciation VARCHAR(10) NULL DEFAULT 'haut';
    END IF;
END $$;

