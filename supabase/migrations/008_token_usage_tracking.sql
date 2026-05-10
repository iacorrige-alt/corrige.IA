-- Rastreamento de uso de tokens OpenAI por professor.
-- tokens_usados: contador acumulado (incrementado após cada correção/extração).
-- limite_tokens: cota configurável por professor (0 = sem limite).

ALTER TABLE professores
  ADD COLUMN IF NOT EXISTS tokens_usados BIGINT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS limite_tokens BIGINT NOT NULL DEFAULT 2000000;

-- Incremento atômico via RPC — evita race condition quando múltiplas correções
-- concluem simultaneamente e tentam atualizar o mesmo contador.
CREATE OR REPLACE FUNCTION incrementar_tokens_professor(
  p_professor_id UUID,
  p_delta        BIGINT
)
RETURNS VOID
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  UPDATE professores
  SET tokens_usados = tokens_usados + p_delta
  WHERE id = p_professor_id;
$$;
