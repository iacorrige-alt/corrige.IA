-- Adiciona timestamp de início da correção para detecção de jobs presos.
-- A ausência dessa coluna tornaria o cron de recovery silenciosamente inoperante.
ALTER TABLE atividades
  ADD COLUMN IF NOT EXISTS correcao_iniciada_em TIMESTAMPTZ;

-- Índice parcial: apenas atividades em correção precisam desse lookup.
-- Em produção com milhares de atividades, evita full scan na tabela.
CREATE INDEX IF NOT EXISTS idx_atividades_corrigindo
  ON atividades (correcao_iniciada_em)
  WHERE status = 'corrigindo';
