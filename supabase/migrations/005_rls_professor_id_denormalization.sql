-- Migration 005: Desnormalizar professor_id em resultados e respostas
--
-- Problema: As políticas RLS nestas tabelas usam subqueries correlacionadas
-- com múltiplos JOINs que executam para CADA row verificada, tornando SELECTs
-- de N rows custosos O(N × JOIN depth).
--
-- Solução: Propagar professor_id diretamente nas tabelas hot (resultados,
-- respostas). A RLS vira uma comparação direta O(1) por row — sem JOINs.
--
-- Trade-off aceito: leve desnormalização em favor de performance real.
-- professor_id é imutável no ciclo de vida de uma atividade.

-- ─── 1. Adicionar coluna professor_id ────────────────────────────────────────

ALTER TABLE resultados
  ADD COLUMN IF NOT EXISTS professor_id UUID REFERENCES professores(id) ON DELETE CASCADE;

ALTER TABLE respostas
  ADD COLUMN IF NOT EXISTS professor_id UUID REFERENCES professores(id) ON DELETE CASCADE;

-- ─── 2. Backfill dados existentes ────────────────────────────────────────────

UPDATE resultados r
SET professor_id = (
  SELECT t.professor_id
  FROM atividades a
  JOIN turmas t ON a.turma_id = t.id
  WHERE a.id = r.atividade_id
)
WHERE professor_id IS NULL;

UPDATE respostas resp
SET professor_id = (
  SELECT r.professor_id
  FROM resultados r
  WHERE r.id = resp.resultado_id
)
WHERE professor_id IS NULL;

-- ─── 3. Enforce NOT NULL após backfill ───────────────────────────────────────

ALTER TABLE resultados ALTER COLUMN professor_id SET NOT NULL;
ALTER TABLE respostas  ALTER COLUMN professor_id SET NOT NULL;

-- ─── 4. Indexes para a nova coluna (RLS path + queries comuns) ───────────────

CREATE INDEX IF NOT EXISTS idx_resultados_professor ON resultados(professor_id);
CREATE INDEX IF NOT EXISTS idx_respostas_professor  ON respostas(professor_id);

-- ─── 5. Triggers para propagar automaticamente em INSERTs futuros ────────────

CREATE OR REPLACE FUNCTION _set_resultado_professor_id()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  SELECT t.professor_id
    INTO NEW.professor_id
    FROM atividades a
    JOIN turmas t ON a.turma_id = t.id
   WHERE a.id = NEW.atividade_id;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_resultado_professor_id ON resultados;
CREATE TRIGGER trg_resultado_professor_id
  BEFORE INSERT ON resultados
  FOR EACH ROW EXECUTE FUNCTION _set_resultado_professor_id();


CREATE OR REPLACE FUNCTION _set_resposta_professor_id()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  SELECT professor_id
    INTO NEW.professor_id
    FROM resultados
   WHERE id = NEW.resultado_id;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_resposta_professor_id ON respostas;
CREATE TRIGGER trg_resposta_professor_id
  BEFORE INSERT ON respostas
  FOR EACH ROW EXECUTE FUNCTION _set_resposta_professor_id();

-- ─── 6. Substituir políticas RLS por comparação direta ───────────────────────

DROP POLICY IF EXISTS "resultados_own" ON resultados;
CREATE POLICY "resultados_own" ON resultados
  FOR ALL USING (professor_id = auth.uid());

DROP POLICY IF EXISTS "respostas_own" ON respostas;
CREATE POLICY "respostas_own" ON respostas
  FOR ALL USING (professor_id = auth.uid());
