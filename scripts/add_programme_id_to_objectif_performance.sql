-- Script pour ajouter le champ programme_id à la table objectif_performance
-- Permet d'assigner un programme à un Objectif Global (OG)

DO $$
BEGIN
    -- Ajouter programme_id si n'existe pas
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'objectif_performance' AND column_name = 'programme_id') THEN
        ALTER TABLE objectif_performance ADD COLUMN programme_id INTEGER REFERENCES programme(id);
        CREATE INDEX IF NOT EXISTS idx_objectif_performance_programme_id ON objectif_performance (programme_id);
    END IF;
END $$;

-- Commentaire pour documentation
COMMENT ON COLUMN objectif_performance.programme_id IS 'Programme associé à un Objectif Global (OG). Optionnel.';

