-- Muda limites do free trial de 3M para 2M
ALTER TABLE professores
  ALTER COLUMN input_tokens_limite SET DEFAULT 2000000,
  ALTER COLUMN output_tokens_limite SET DEFAULT 2000000;

-- Atualiza usuários existentes que estão com 3M (padrão anterior)
UPDATE professores
SET
  input_tokens_limite  = 2000000,
  output_tokens_limite = 2000000
WHERE
  input_tokens_limite  = 3000000
  AND output_tokens_limite = 3000000;

-- RPC: adiciona tokens quando uma recarga é comprada
-- Reativa contas bloqueadas automaticamente
CREATE OR REPLACE FUNCTION adicionar_tokens_recarga(
  p_professor_id uuid,
  p_input_tokens  bigint,
  p_output_tokens bigint
) RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  UPDATE professores
  SET
    input_tokens_limite  = input_tokens_limite  + p_input_tokens,
    output_tokens_limite = output_tokens_limite + p_output_tokens,
    plano = CASE WHEN plano = 'bloqueado' THEN 'free_trial' ELSE plano END
  WHERE id = p_professor_id;
END;
$$;
