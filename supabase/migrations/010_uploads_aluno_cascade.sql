-- FK uploads.aluno_id → alunos: troca NO ACTION por SET NULL.
-- Quando um aluno é deletado, os uploads ficam sem dono (aluno_id = NULL)
-- mas não são removidos — preserva o histórico de arquivos enviados.
ALTER TABLE uploads
  DROP CONSTRAINT IF EXISTS uploads_aluno_id_fkey,
  ADD CONSTRAINT uploads_aluno_id_fkey
    FOREIGN KEY (aluno_id) REFERENCES alunos(id) ON DELETE SET NULL;
