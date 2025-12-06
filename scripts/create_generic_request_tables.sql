-- Script SQL pour créer les tables pour le système de demandes génériques
-- Utilisable dans tous les modules (RH, Budget, Stock, Performance, etc.)

-- Table principale pour les demandes génériques
CREATE TABLE IF NOT EXISTS generic_request (
    id SERIAL PRIMARY KEY,
    module VARCHAR(50) NOT NULL,
    type VARCHAR(50) NOT NULL,
    objet VARCHAR(500) NOT NULL,
    motif TEXT,
    description TEXT,
    date_debut DATE,
    date_fin DATE,
    nb_jours DOUBLE PRECISION,
    donnees_metier TEXT,  -- JSON stringifié pour données spécifiques au module
    document_joint VARCHAR(500),
    document_filename VARCHAR(255),
    satisfaction_note INTEGER CHECK (satisfaction_note >= 1 AND satisfaction_note <= 5),
    satisfaction_commentaire TEXT,
    demandeur_id INTEGER NOT NULL REFERENCES agent_complet(id),
    demandeur_user_id INTEGER REFERENCES "user"(id),
    current_state VARCHAR(50) NOT NULL DEFAULT 'Brouillon',
    current_assignee_role VARCHAR(100),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_generic_request_module ON generic_request(module);
CREATE INDEX IF NOT EXISTS idx_generic_request_type ON generic_request(type);
CREATE INDEX IF NOT EXISTS idx_generic_request_demandeur_id ON generic_request(demandeur_id);
CREATE INDEX IF NOT EXISTS idx_generic_request_current_state ON generic_request(current_state);
CREATE INDEX IF NOT EXISTS idx_generic_request_created_at ON generic_request(created_at DESC);

-- Table pour l'historique des transitions de workflow
CREATE TABLE IF NOT EXISTS generic_workflow_history (
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES generic_request(id) ON DELETE CASCADE,
    from_state VARCHAR(50) NOT NULL,
    to_state VARCHAR(50) NOT NULL,
    acted_by_user_id INTEGER REFERENCES "user"(id),
    acted_by_role VARCHAR(100),
    comment TEXT,
    acted_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL
);

-- Index pour l'historique
CREATE INDEX IF NOT EXISTS idx_generic_workflow_history_request_id ON generic_workflow_history(request_id);
CREATE INDEX IF NOT EXISTS idx_generic_workflow_history_acted_at ON generic_workflow_history(acted_at DESC);

-- Commentaires pour documentation
COMMENT ON TABLE generic_request IS 'Table générique pour les demandes utilisables dans tous les modules (RH, Budget, Stock, Performance, etc.)';
COMMENT ON COLUMN generic_request.module IS 'Module d''origine de la demande (rh, budget, stock, performance, etc.)';
COMMENT ON COLUMN generic_request.type IS 'Code du type de demande (correspond à RequestTypeCustom.code)';
COMMENT ON COLUMN generic_request.donnees_metier IS 'Données spécifiques au module au format JSON (ex: {"montant": 1000000, "programme_id": 1} pour Budget)';
COMMENT ON COLUMN generic_request.current_state IS 'État actuel dans le workflow (WorkflowState)';
COMMENT ON COLUMN generic_request.current_assignee_role IS 'Rôle actuellement assigné à la validation (ex: "N1", "DRH", "DAF")';

COMMENT ON TABLE generic_workflow_history IS 'Historique des transitions de workflow pour les demandes génériques';
COMMENT ON COLUMN generic_workflow_history.from_state IS 'État d''origine de la transition';
COMMENT ON COLUMN generic_workflow_history.to_state IS 'État de destination de la transition';

