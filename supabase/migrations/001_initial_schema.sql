-- CorrigeAI - Initial Schema
-- Run this in your Supabase SQL editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TABLES
-- ============================================================

CREATE TABLE professores (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  nome        TEXT NOT NULL,
  email       TEXT UNIQUE NOT NULL,
  criado_em   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE turmas (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  professor_id  UUID NOT NULL REFERENCES professores(id) ON DELETE CASCADE,
  nome          TEXT NOT NULL,
  disciplina    TEXT NOT NULL,
  cor           TEXT NOT NULL DEFAULT '#6366f1',
  criado_em     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE alunos (
  id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  turma_id  UUID NOT NULL REFERENCES turmas(id) ON DELETE CASCADE,
  nome      TEXT NOT NULL,
  initials  TEXT NOT NULL,
  criado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE atividades (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  turma_id        UUID NOT NULL REFERENCES turmas(id) ON DELETE CASCADE,
  nome            TEXT NOT NULL,
  tipo            TEXT NOT NULL DEFAULT 'prova', -- prova | atividade | trabalho
  status          TEXT NOT NULL DEFAULT 'pendente', -- pendente | corrigindo | concluida
  modo_correcao   TEXT NOT NULL DEFAULT 'automatico', -- automatico | semi-automatico
  gabarito_texto  TEXT,
  data_criacao    TIMESTAMPTZ DEFAULT NOW(),
  data_correcao   TIMESTAMPTZ
);

CREATE TABLE questoes (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  atividade_id UUID NOT NULL REFERENCES atividades(id) ON DELETE CASCADE,
  enunciado    TEXT NOT NULL,
  gabarito     TEXT,
  tipo         TEXT NOT NULL DEFAULT 'dissertativa', -- dissertativa | multipla_escolha
  peso         NUMERIC(5,2) DEFAULT 1.0,
  ordem        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE resultados (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  atividade_id UUID NOT NULL REFERENCES atividades(id) ON DELETE CASCADE,
  aluno_id     UUID NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
  nota_total   NUMERIC(5,2),
  criado_em    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(atividade_id, aluno_id)
);

CREATE TABLE respostas (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  resultado_id  UUID NOT NULL REFERENCES resultados(id) ON DELETE CASCADE,
  questao_id    UUID NOT NULL REFERENCES questoes(id) ON DELETE CASCADE,
  texto_resposta TEXT,
  nota          NUMERIC(5,2),
  status        TEXT, -- correto | parcial | errado
  comentario_ia TEXT,
  flag_tipo     TEXT  -- null | ia | copia | plagio
);

CREATE TABLE uploads (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  atividade_id UUID NOT NULL REFERENCES atividades(id) ON DELETE CASCADE,
  aluno_id     UUID REFERENCES alunos(id),
  storage_path TEXT NOT NULL,
  tipo_arquivo TEXT NOT NULL, -- image | pdf
  content_type TEXT,          -- e.g. image/jpeg, image/png, application/pdf
  criado_em    TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX idx_turmas_professor ON turmas(professor_id);
CREATE INDEX idx_alunos_turma ON alunos(turma_id);
CREATE INDEX idx_atividades_turma ON atividades(turma_id);
CREATE INDEX idx_questoes_atividade ON questoes(atividade_id);
CREATE INDEX idx_resultados_atividade ON resultados(atividade_id);
CREATE INDEX idx_resultados_aluno ON resultados(aluno_id);
CREATE INDEX idx_respostas_resultado ON respostas(resultado_id);
CREATE INDEX idx_uploads_atividade ON uploads(atividade_id);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE professores ENABLE ROW LEVEL SECURITY;
ALTER TABLE turmas ENABLE ROW LEVEL SECURITY;
ALTER TABLE alunos ENABLE ROW LEVEL SECURITY;
ALTER TABLE atividades ENABLE ROW LEVEL SECURITY;
ALTER TABLE questoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE resultados ENABLE ROW LEVEL SECURITY;
ALTER TABLE respostas ENABLE ROW LEVEL SECURITY;
ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;

-- Professores: cada um vê apenas seu próprio registro
CREATE POLICY "professor_own" ON professores
  FOR ALL USING (id = auth.uid());

-- Turmas: professor vê apenas suas turmas
CREATE POLICY "turmas_own" ON turmas
  FOR ALL USING (professor_id = auth.uid());

-- Alunos: professor vê alunos das suas turmas
CREATE POLICY "alunos_own" ON alunos
  FOR ALL USING (
    turma_id IN (SELECT id FROM turmas WHERE professor_id = auth.uid())
  );

-- Atividades: professor vê atividades das suas turmas
CREATE POLICY "atividades_own" ON atividades
  FOR ALL USING (
    turma_id IN (SELECT id FROM turmas WHERE professor_id = auth.uid())
  );

-- Questões: professor vê questões das suas atividades
CREATE POLICY "questoes_own" ON questoes
  FOR ALL USING (
    atividade_id IN (
      SELECT a.id FROM atividades a
      JOIN turmas t ON a.turma_id = t.id
      WHERE t.professor_id = auth.uid()
    )
  );

-- Resultados
CREATE POLICY "resultados_own" ON resultados
  FOR ALL USING (
    atividade_id IN (
      SELECT a.id FROM atividades a
      JOIN turmas t ON a.turma_id = t.id
      WHERE t.professor_id = auth.uid()
    )
  );

-- Respostas
CREATE POLICY "respostas_own" ON respostas
  FOR ALL USING (
    resultado_id IN (
      SELECT r.id FROM resultados r
      JOIN atividades a ON r.atividade_id = a.id
      JOIN turmas t ON a.turma_id = t.id
      WHERE t.professor_id = auth.uid()
    )
  );

-- Uploads
CREATE POLICY "uploads_own" ON uploads
  FOR ALL USING (
    atividade_id IN (
      SELECT a.id FROM atividades a
      JOIN turmas t ON a.turma_id = t.id
      WHERE t.professor_id = auth.uid()
    )
  );

-- ============================================================
-- TRIGGER: Criar perfil de professor ao registrar no Auth
-- ============================================================

CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO professores (id, nome, email)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'nome', split_part(NEW.email, '@', 1)),
    NEW.email
  )
  ON CONFLICT (email) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ============================================================
-- STORAGE BUCKET
-- ============================================================
-- Run this separately in Supabase dashboard > Storage:
-- Create a bucket called "provas" with:
--   public: false
--   file size limit: 50MB
--   allowed mime types: image/jpeg, image/png, image/webp, application/pdf
