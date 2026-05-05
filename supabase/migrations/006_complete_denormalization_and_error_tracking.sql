-- Migration 006: Completar desnormalização RLS + rastreamento de falhas parciais
--
-- Parte 1: professor_id em questoes e uploads (RLS O(1) nas 4 tabelas restantes)
-- Parte 2: uploads_com_erro em atividades (visibilidade de falhas parciais)

-- ─── 1. professor_id em questoes ─────────────────────────────────────────────

ALTER TABLE questoes
  ADD COLUMN IF NOT EXISTS professor_id UUID REFERENCES professores(id) ON DELETE CASCADE;

UPDATE questoes q
SET professor_id = (
  SELECT t.professor_id
  FROM atividades a
  JOIN turmas t ON a.turma_id = t.id
  WHERE a.id = q.atividade_id
)
WHERE professor_id IS NULL;

ALTER TABLE questoes ALTER COLUMN professor_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_questoes_professor ON questoes(professor_id);

CREATE OR REPLACE FUNCTION _set_questao_professor_id()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  SELECT t.professor_id INTO NEW.professor_id
  FROM atividades a
  JOIN turmas t ON a.turma_id = t.id
  WHERE a.id = NEW.atividade_id;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_questao_professor_id ON questoes;
CREATE TRIGGER trg_questao_professor_id
  BEFORE INSERT ON questoes
  FOR EACH ROW EXECUTE FUNCTION _set_questao_professor_id();

DROP POLICY IF EXISTS "questoes_own" ON questoes;
CREATE POLICY "questoes_own" ON questoes
  FOR ALL USING (professor_id = auth.uid());

-- ─── 2. professor_id em uploads ──────────────────────────────────────────────

ALTER TABLE uploads
  ADD COLUMN IF NOT EXISTS professor_id UUID REFERENCES professores(id) ON DELETE CASCADE;

UPDATE uploads u
SET professor_id = (
  SELECT t.professor_id
  FROM atividades a
  JOIN turmas t ON a.turma_id = t.id
  WHERE a.id = u.atividade_id
)
WHERE professor_id IS NULL;

ALTER TABLE uploads ALTER COLUMN professor_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_uploads_professor ON uploads(professor_id);

CREATE OR REPLACE FUNCTION _set_upload_professor_id()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  SELECT t.professor_id INTO NEW.professor_id
  FROM atividades a
  JOIN turmas t ON a.turma_id = t.id
  WHERE a.id = NEW.atividade_id;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_upload_professor_id ON uploads;
CREATE TRIGGER trg_upload_professor_id
  BEFORE INSERT ON uploads
  FOR EACH ROW EXECUTE FUNCTION _set_upload_professor_id();

DROP POLICY IF EXISTS "uploads_own" ON uploads;
CREATE POLICY "uploads_own" ON uploads
  FOR ALL USING (professor_id = auth.uid());

-- ─── 3. uploads_com_erro em atividades ───────────────────────────────────────
-- Rastreia quantos uploads falharam em cada correção.
-- 0 = sucesso total. > 0 = falha parcial, frontend exibe aviso.

ALTER TABLE atividades
  ADD COLUMN IF NOT EXISTS uploads_com_erro INTEGER NOT NULL DEFAULT 0;
