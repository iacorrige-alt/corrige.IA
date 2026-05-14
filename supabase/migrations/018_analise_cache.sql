-- Cache persistente da análise IA por turma.
-- Sobrevive a restarts do servidor e evita re-chamadas ao LLM quando as métricas não mudaram.
ALTER TABLE turmas
  ADD COLUMN IF NOT EXISTS analise_ia_cache_key  text,
  ADD COLUMN IF NOT EXISTS analise_ia_cache       jsonb,
  ADD COLUMN IF NOT EXISTS analise_ia_cache_at    timestamptz;
