-- scripts/create_suivi_activite_table.sql
-- Création de la table suivi_activite pour le suivi périodique des activités SIGOBE

CREATE TABLE IF NOT EXISTS suivi_activite (
    id SERIAL PRIMARY KEY,
    sigobe_execution_id INTEGER REFERENCES sigobe_execution(id),
    chargement_id INTEGER REFERENCES sigobe_chargement(id),
    code_activite VARCHAR(100),
    libelle_activite VARCHAR(500) NOT NULL,
    programme VARCHAR(500),
    action VARCHAR(500),
    structures_responsables VARCHAR(500) NOT NULL,
    resultat_attendu TEXT NOT NULL,
    resultat_operationnel TEXT,
    preuve_realisation VARCHAR(500),
    preuve_filename VARCHAR(255),
    observations TEXT,
    annee INTEGER NOT NULL,
    periode_type VARCHAR(20) NOT NULL,
    periode_valeur INTEGER,
    date_periode DATE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    created_by_id INTEGER NOT NULL REFERENCES "user"(id),
    updated_by_id INTEGER REFERENCES "user"(id)
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_suivi_activite_annee ON suivi_activite (annee);
CREATE INDEX IF NOT EXISTS idx_suivi_activite_periode_type ON suivi_activite (periode_type);
CREATE INDEX IF NOT EXISTS idx_suivi_activite_code_activite ON suivi_activite (code_activite);
CREATE INDEX IF NOT EXISTS idx_suivi_activite_date_periode ON suivi_activite (date_periode);
CREATE INDEX IF NOT EXISTS idx_suivi_activite_sigobe_execution_id ON suivi_activite (sigobe_execution_id);
CREATE INDEX IF NOT EXISTS idx_suivi_activite_chargement_id ON suivi_activite (chargement_id);

