-- ================================================================
-- Fix 1: RLS policies — substituir auth.uid() por (select auth.uid())
-- Evita reavaliação por linha em tabelas grandes
-- ================================================================

-- professores
DROP POLICY IF EXISTS "professor_own" ON professores;
CREATE POLICY "professor_own" ON professores
  FOR ALL USING (id = (SELECT auth.uid()));

-- turmas
DROP POLICY IF EXISTS "turmas_own" ON turmas;
CREATE POLICY "turmas_own" ON turmas
  FOR ALL USING (professor_id = (SELECT auth.uid()));

-- alunos
DROP POLICY IF EXISTS "alunos_own" ON alunos;
CREATE POLICY "alunos_own" ON alunos
  FOR ALL USING (
    turma_id IN (
      SELECT id FROM turmas WHERE professor_id = (SELECT auth.uid())
    )
  );

-- atividades
DROP POLICY IF EXISTS "atividades_own" ON atividades;
CREATE POLICY "atividades_own" ON atividades
  FOR ALL USING (
    turma_id IN (
      SELECT id FROM turmas WHERE professor_id = (SELECT auth.uid())
    )
  );

-- questoes
DROP POLICY IF EXISTS "questoes_own" ON questoes;
CREATE POLICY "questoes_own" ON questoes
  FOR ALL USING (
    atividade_id IN (
      SELECT a.id FROM atividades a
      JOIN turmas t ON a.turma_id = t.id
      WHERE t.professor_id = (SELECT auth.uid())
    )
  );

-- resultados
DROP POLICY IF EXISTS "resultados_own" ON resultados;
CREATE POLICY "resultados_own" ON resultados
  FOR ALL USING (
    atividade_id IN (
      SELECT a.id FROM atividades a
      JOIN turmas t ON a.turma_id = t.id
      WHERE t.professor_id = (SELECT auth.uid())
    )
  );

-- respostas
DROP POLICY IF EXISTS "respostas_own" ON respostas;
CREATE POLICY "respostas_own" ON respostas
  FOR ALL USING (
    resultado_id IN (
      SELECT r.id FROM resultados r
      JOIN atividades a ON r.atividade_id = a.id
      JOIN turmas t ON a.turma_id = t.id
      WHERE t.professor_id = (SELECT auth.uid())
    )
  );

-- uploads
DROP POLICY IF EXISTS "uploads_own" ON uploads;
CREATE POLICY "uploads_own" ON uploads
  FOR ALL USING (
    atividade_id IN (
      SELECT a.id FROM atividades a
      JOIN turmas t ON a.turma_id = t.id
      WHERE t.professor_id = (SELECT auth.uid())
    )
  );

-- ================================================================
-- Fix 2: Índices para FKs sem cobertura
-- ================================================================

CREATE INDEX IF NOT EXISTS idx_respostas_questao ON respostas(questao_id);
CREATE INDEX IF NOT EXISTS idx_uploads_aluno ON uploads(aluno_id);
