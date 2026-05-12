-- 012: Sistema de plano free trial com rastreamento separado de tokens de entrada e saída.
-- Quando os tokens se esgotam, o plano muda automaticamente para 'bloqueado'.
-- Planos: 'free_trial' | 'pago' | 'bloqueado'

ALTER TABLE professores
  ADD COLUMN IF NOT EXISTS input_tokens_usados     BIGINT      NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS output_tokens_usados    BIGINT      NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS input_tokens_limite     BIGINT      NOT NULL DEFAULT 5000000,
  ADD COLUMN IF NOT EXISTS output_tokens_limite    BIGINT      NOT NULL DEFAULT 5000000,
  ADD COLUMN IF NOT EXISTS plano                   TEXT        NOT NULL DEFAULT 'free_trial'
    CHECK (plano IN ('free_trial', 'pago', 'bloqueado')),
  ADD COLUMN IF NOT EXISTS plano_ativo_em          TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS stripe_customer_id      TEXT,
  ADD COLUMN IF NOT EXISTS stripe_subscription_id  TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS professores_stripe_customer_id_idx
  ON professores (stripe_customer_id)
  WHERE stripe_customer_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS professores_stripe_subscription_id_idx
  ON professores (stripe_subscription_id)
  WHERE stripe_subscription_id IS NOT NULL;

-- Substitui a RPC anterior (p_delta) por uma com p_input_tokens + p_output_tokens.
-- Auto-bloqueia contas free_trial quando qualquer um dos limites é atingido.
CREATE OR REPLACE FUNCTION incrementar_tokens_professor(
  p_professor_id   UUID,
  p_input_tokens   BIGINT,
  p_output_tokens  BIGINT
)
RETURNS VOID
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  UPDATE professores
  SET
    input_tokens_usados  = input_tokens_usados  + p_input_tokens,
    output_tokens_usados = output_tokens_usados + p_output_tokens,
    tokens_usados        = tokens_usados + p_input_tokens + p_output_tokens,
    plano = CASE
      WHEN plano = 'free_trial' AND (
        input_tokens_usados  + p_input_tokens  >= input_tokens_limite OR
        output_tokens_usados + p_output_tokens >= output_tokens_limite
      ) THEN 'bloqueado'
      ELSE plano
    END
  WHERE id = p_professor_id;
$$;
