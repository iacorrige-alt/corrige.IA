-- ─── Mantém tokens_usados sincronizado com input + output ───────────────────
-- O campo tokens_usados é legado (adicionado em 008) e parou de ser atualizado
-- quando a migration 015 substituiu o RPC incrementar_tokens_professor.
-- Esta migration corrige o RPC para manter o campo em sincronia.

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
    tokens_usados        = COALESCE(tokens_usados, 0) + v_in + v_out,
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
