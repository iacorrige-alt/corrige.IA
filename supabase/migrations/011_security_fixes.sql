-- Fix: unique constraint on respostas to enable safe upsert and eliminate race condition
-- First clean up any duplicate rows from the race condition window (keep latest per pair)
WITH duplicates AS (
  SELECT id,
         ROW_NUMBER() OVER (
           PARTITION BY resultado_id, questao_id
           ORDER BY id DESC
         ) AS rn
  FROM respostas
)
DELETE FROM respostas WHERE id IN (SELECT id FROM duplicates WHERE rn > 1);

ALTER TABLE respostas
  DROP CONSTRAINT IF EXISTS respostas_resultado_questao_unique;
ALTER TABLE respostas
  ADD CONSTRAINT respostas_resultado_questao_unique
  UNIQUE (resultado_id, questao_id);

-- Fix: trigger to atomically recalculate nota_total whenever a resposta is inserted/updated
CREATE OR REPLACE FUNCTION _recalcular_nota_total()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE resultados
  SET nota_total = COALESCE((
    SELECT SUM(GREATEST(0.0, LEAST(COALESCE(r.nota, 0.0), COALESCE(q.peso, 1.0))))
    FROM respostas r
    JOIN questoes q ON q.id = r.questao_id
    WHERE r.resultado_id = NEW.resultado_id
  ), 0.0)
  WHERE id = NEW.resultado_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_nota_total ON respostas;
CREATE TRIGGER trg_nota_total
AFTER INSERT OR UPDATE OF nota ON respostas
FOR EACH ROW EXECUTE FUNCTION _recalcular_nota_total();
