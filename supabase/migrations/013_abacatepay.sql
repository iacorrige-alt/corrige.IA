-- 013: Troca Stripe por AbacatePay e ajusta limites de tokens de 5M para 3M.

-- Renomear colunas
ALTER TABLE professores
  RENAME COLUMN stripe_customer_id      TO abacatepay_customer_id;
ALTER TABLE professores
  RENAME COLUMN stripe_subscription_id  TO abacatepay_subscription_id;

-- Ajustar default para 3M
ALTER TABLE professores
  ALTER COLUMN input_tokens_limite  SET DEFAULT 3000000,
  ALTER COLUMN output_tokens_limite SET DEFAULT 3000000;

-- Atualizar usuários existentes que ainda têm o default antigo de 5M
UPDATE professores
  SET input_tokens_limite  = 3000000,
      output_tokens_limite = 3000000
  WHERE input_tokens_limite  = 5000000
    AND output_tokens_limite = 5000000
    AND plano = 'free_trial';

-- Recriar índices com nomes corretos
DROP INDEX IF EXISTS professores_stripe_customer_id_idx;
DROP INDEX IF EXISTS professores_stripe_subscription_id_idx;

CREATE UNIQUE INDEX IF NOT EXISTS professores_abacatepay_customer_id_idx
  ON professores (abacatepay_customer_id)
  WHERE abacatepay_customer_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS professores_abacatepay_subscription_id_idx
  ON professores (abacatepay_subscription_id)
  WHERE abacatepay_subscription_id IS NOT NULL;
