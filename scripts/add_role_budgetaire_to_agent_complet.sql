-- Migration: Ajouter la colonne role_budgetaire à la table agent_complet
-- Date: 2025-12-04
-- Description: Ajoute une colonne pour stocker le rôle budgétaire d'un agent (RPROG, RFFIM, RUO, RBOP)

-- Vérifier si la colonne existe déjà
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'agent_complet' 
        AND column_name = 'role_budgetaire'
    ) THEN
        -- Ajouter la colonne role_budgetaire
        ALTER TABLE agent_complet 
        ADD COLUMN role_budgetaire VARCHAR(10) NULL;
        
        -- Ajouter un commentaire pour documenter la colonne
        COMMENT ON COLUMN agent_complet.role_budgetaire IS 'Rôle budgétaire de l''agent: RPROG (Responsable de Programme), RFFIM (Responsable Financier et Financier), RUO (Responsable d''Unité Opérationnelle), RBOP (Responsable Budget Opérationnel de Programme)';
        
        RAISE NOTICE 'Colonne role_budgetaire ajoutée avec succès à la table agent_complet';
    ELSE
        RAISE NOTICE 'La colonne role_budgetaire existe déjà dans la table agent_complet';
    END IF;
END $$;

