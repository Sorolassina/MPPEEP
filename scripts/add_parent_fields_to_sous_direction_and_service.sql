-- Script pour ajouter les champs programme_id et cabinet_id aux tables sous_direction et service
-- Permet de rattacher directement les sous-directions et services au cabinet ou au programme

-- Ajouter programme_id et cabinet_id à la table sous_direction
DO $$
BEGIN
    -- Ajouter programme_id si n'existe pas
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'sous_direction' AND column_name = 'programme_id') THEN
        ALTER TABLE sous_direction ADD COLUMN programme_id INTEGER REFERENCES programme(id);
    END IF;
    
    -- Ajouter cabinet_id si n'existe pas
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'sous_direction' AND column_name = 'cabinet_id') THEN
        ALTER TABLE sous_direction ADD COLUMN cabinet_id INTEGER REFERENCES cabinet(id);
    END IF;
END $$;

-- Ajouter programme_id et cabinet_id à la table service
-- Note: sous_direction_id devient optionnel (peut être NULL)
DO $$
BEGIN
    -- Rendre sous_direction_id optionnel si ce n'est pas déjà le cas
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'service' AND column_name = 'sous_direction_id' AND is_nullable = 'NO') THEN
        ALTER TABLE service ALTER COLUMN sous_direction_id DROP NOT NULL;
    END IF;
    
    -- Ajouter programme_id si n'existe pas
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'service' AND column_name = 'programme_id') THEN
        ALTER TABLE service ADD COLUMN programme_id INTEGER REFERENCES programme(id);
    END IF;
    
    -- Ajouter cabinet_id si n'existe pas
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'service' AND column_name = 'cabinet_id') THEN
        ALTER TABLE service ADD COLUMN cabinet_id INTEGER REFERENCES cabinet(id);
    END IF;
END $$;

-- Commentaires pour documentation
COMMENT ON COLUMN sous_direction.programme_id IS 'Rattachement optionnel à un programme (exclusion mutuelle avec direction_id et cabinet_id)';
COMMENT ON COLUMN sous_direction.cabinet_id IS 'Rattachement optionnel à un cabinet (exclusion mutuelle avec direction_id et programme_id)';
COMMENT ON COLUMN service.programme_id IS 'Rattachement optionnel à un programme (exclusion mutuelle avec sous_direction_id, direction_id et cabinet_id)';
COMMENT ON COLUMN service.cabinet_id IS 'Rattachement optionnel à un cabinet (exclusion mutuelle avec sous_direction_id, direction_id et programme_id)';

