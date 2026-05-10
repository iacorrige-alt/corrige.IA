-- Migration 009: professor_id em atividades + índice em status
--
-- Problema: atividades é a única tabela "hot" sem professor_id desnormalizado.
-- Isso força 2 round-trips em listar, get, upload e status (busca atividade → verifica
-- professor via turma). Resulta também em RLS com subquery em vez de comparação O(1).
--
-- Parte 1: professor_id para RLS O(1) e queries de 1 round-trip
-- Parte 2: index em status para o filtro do dashboard (status = 'concluida')

-- ─── 1. Adicionar coluna professor_id ────────────────────────────────────────

ALTER TABLE atividades
  ADD COLUMN IF NOT EXISTS professor_id UUID REFERENCES professores(id) ON DELETE CASCADE;

UPDATE atividades a
SET professor_id = (
  SELECT professor_id FROM turmas WHERE id = a.turma_id
)
WHERE professor_id IS NULL;

ALTER TABLE atividades ALTER COLUMN professor_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_atividades_professor ON atividades(professor_id);

-- Trigger para propagar professor_id automaticamente em INSERTs futuros
CREATE OR REPLACE FUNCTION _set_atividade_professor_id()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  SELECT professor_id INTO NEW.professor_id FROM turmas WHERE id = NEW.turma_id;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_atividade_professor_id ON atividades;
CREATE TRIGGER trg_atividade_professor_id
  BEFORE INSERT ON atividades
  FOR EACH ROW EXECUTE FUNCTION _set_atividade_professor_id();

-- RLS passa de subquery para comparação direta O(1)
DROP POLICY IF EXISTS "atividades_own" ON atividades;
CREATE POLICY "atividades_own" ON atividades
  FOR ALL USING (professor_id = (SELECT auth.uid()));

-- ─── 2. Índice em status ──────────────────────────────────────────────────────
-- dashboard_turma filtra .eq("status", "concluida") sem cobertura de índice.

CREATE INDEX IF NOT EXISTS idx_atividades_status ON atividades(status);
