-- ─── Idempotência de webhooks ─────────────────────────────────────────────────
-- Garante que cada evento do AbacatePay seja processado exatamente uma vez.
CREATE TABLE IF NOT EXISTS webhook_events (
  id           TEXT        PRIMARY KEY,   -- checkout/subscription id do AbacatePay
  evento       TEXT        NOT NULL,
  processado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Limpeza automática de registros antigos (> 90 dias) via pg_cron ou manual
CREATE INDEX IF NOT EXISTS idx_webhook_events_processado_em
  ON webhook_events (processado_em);

-- ─── RPC: tokens negativos são silenciosamente ignorados ──────────────────────
-- Previne que bugs ou entradas maliciosas reduzam o contador de tokens usados.
CREATE OR REPLACE FUNCTION incrementar_tokens_professor(
  p_professor_id uuid,
  p_input_tokens  bigint,
  p_output_tokens bigint
) RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_in  bigint := GREATEST(0, p_input_tokens);
  v_out bigint := GREATEST(0, p_output_tokens);
BEGIN
  UPDATE professores
  SET
    input_tokens_usados  = input_tokens_usados  + v_in,
    output_tokens_usados = output_tokens_usados + v_out,
    plano = CASE
      WHEN plano = 'free_trial'
        AND (
          (input_tokens_limite  > 0 AND input_tokens_usados  + v_in  >= input_tokens_limite)
          OR
          (output_tokens_limite > 0 AND output_tokens_usados + v_out >= output_tokens_limite)
        )
      THEN 'bloqueado'
      ELSE plano
    END
  WHERE id = p_professor_id;
END;
$$;
