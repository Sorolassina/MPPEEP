-- Script pour créer la table cabinet
-- Exécuter ce script pour créer la table cabinet dans la base de données

CREATE TABLE IF NOT EXISTS cabinet (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    libelle VARCHAR(200) NOT NULL,
    description TEXT,
    actif BOOLEAN DEFAULT TRUE,
    responsable_id INTEGER REFERENCES agent_complet(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Créer un index sur le code pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_cabinet_code ON cabinet(code);

-- Ajouter la colonne cabinet_id à la table direction si elle n'existe pas
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'direction' AND column_name = 'cabinet_id'
    ) THEN
        ALTER TABLE direction ADD COLUMN cabinet_id INTEGER REFERENCES cabinet(id);
        CREATE INDEX IF NOT EXISTS idx_direction_cabinet_id ON direction(cabinet_id);
    END IF;
END $$;

-- Commentaires
COMMENT ON TABLE cabinet IS 'Cabinet du Ministre - peut avoir des directions, sous-directions ou services';
COMMENT ON COLUMN cabinet.code IS 'Code unique du cabinet';
COMMENT ON COLUMN cabinet.libelle IS 'Libellé du cabinet';
COMMENT ON COLUMN cabinet.responsable_id IS 'Responsable du cabinet (référence à agent_complet)';
COMMENT ON COLUMN direction.cabinet_id IS 'Rattachement au cabinet (exclusion mutuelle avec programme_id)';

