-- Índices ausentes identificados em auditoria de performance.
-- atividades.professor_id: usado em todos os SELECTs do router de atividades.
-- uploads.atividade_id: usado em listar_uploads, resultados, reprocessar.
-- resultados.aluno_id: usado em dashboard_aluno e detecção de cópias.

CREATE INDEX IF NOT EXISTS idx_atividades_professor ON atividades(professor_id);
CREATE INDEX IF NOT EXISTS idx_uploads_atividade    ON uploads(atividade_id);
CREATE INDEX IF NOT EXISTS idx_resultados_aluno     ON resultados(aluno_id);
