-- scripts/add_doc_justif_to_indicateur_performance.sql
-- Ajouter la colonne doc_justif à la table indicateur_performance

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'indicateur_performance' AND column_name = 'doc_justif') THEN
        ALTER TABLE indicateur_performance ADD COLUMN doc_justif VARCHAR(500) NULL;
    END IF;
END $$;

