# CorrigeAI

Plataforma SaaS de correção automática de provas e atividades escolares com IA.  
Professores fazem upload de fotos ou PDFs das provas — a IA corrige tudo, questão a questão.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | Python 3.11 + FastAPI |
| Banco / Auth / Storage | Supabase |
| IA | OpenAI GPT-4o + GPT-4o Vision |
| Deploy Frontend | Vercel |
| Deploy Backend | Railway |

---

## Setup local

### Pré-requisitos

- Node.js 20+
- Python 3.11+
- Conta no [Supabase](https://supabase.com) (gratuita)
- Chave da [OpenAI API](https://platform.openai.com)

### 1. Clone e configure variáveis

```bash
git clone <url-do-repo>
cd corrigeai
cp .env.example .env
# Edite .env com suas chaves
```

### 2. Supabase — criar projeto e rodar migrations

1. Crie um projeto em [supabase.com](https://supabase.com)
2. Copie as chaves em **Project Settings > API**
3. Abra o **SQL Editor** e cole o conteúdo de `supabase/migrations/001_initial_schema.sql`
4. Execute o SQL — isso cria todas as tabelas, RLS policies e o trigger de criação de professor
5. Vá em **Storage > New bucket**:
   - Nome: `provas`
   - Public: **não**
   - File size limit: 50 MB
   - Allowed MIME types: `image/jpeg, image/png, image/webp, application/pdf`

### 3. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copie as vars de ambiente para o backend
cp ../.env .env

uvicorn app.main:app --reload
# API disponível em http://localhost:8000
# Docs em http://localhost:8000/docs
```

### 4. Frontend

```bash
cd frontend
npm install

# Crie frontend/.env.local com:
# VITE_SUPABASE_URL=...
# VITE_SUPABASE_ANON_KEY=...
# VITE_API_URL=http://localhost:8000

npm run dev
# App disponível em http://localhost:5173
```

---

## Deploy

### Backend — Railway

1. Crie uma conta em [railway.app](https://railway.app)
2. Crie um novo projeto > **Deploy from GitHub repo** > selecione a pasta `backend/`
3. Em **Variables**, adicione todas as vars do `.env.example` (sem o prefixo `VITE_`)
4. O `railway.json` já configura o start command automaticamente
5. Copie a URL gerada (ex: `https://corrigeai-backend.railway.app`)

### Frontend — Vercel

1. Crie uma conta em [vercel.com](https://vercel.com)
2. **New Project** > importe o repositório > selecione a pasta `frontend/` como root
3. Em **Environment Variables**, adicione:
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
   - `VITE_API_URL` → URL do backend no Railway
4. O `vercel.json` já configura o SPA rewrite
5. Deploy automático em cada push para main

### CORS

No Railway, adicione a variável:
```
CORS_ORIGINS=https://seu-projeto.vercel.app
```

---

## Variáveis de Ambiente

| Variável | Onde usar | Descrição |
|----------|-----------|-----------|
| `SUPABASE_URL` | Backend | URL do projeto Supabase |
| `SUPABASE_ANON_KEY` | Backend | Chave anon (pública) |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend | Chave service role (secreta) |
| `OPENAI_API_KEY` | Backend | Chave da OpenAI |
| `CORS_ORIGINS` | Backend | Origens permitidas (vírgula) |
| `VITE_SUPABASE_URL` | Frontend | URL do projeto Supabase |
| `VITE_SUPABASE_ANON_KEY` | Frontend | Chave anon (pública) |
| `VITE_API_URL` | Frontend | URL base do backend |

---

## Arquitetura

```
Upload de prova (foto/PDF)
        ↓
Storage (Supabase)
        ↓
GPT-4o Vision → Transcrição do texto manuscrito
        ↓
Identificação do aluno (Vision → match na lista da turma)
        ↓
GPT-4o → Correção questão a questão com feedback
        ↓
detection_service → Comparação entre alunos (SequenceMatcher)
        ↓
Banco (resultados + respostas + flags)
        ↓
Dashboard do professor / Dashboard do aluno
```

### Decisões de arquitetura (beta/50 usuários)

- **Correção assíncrona via BackgroundTasks do FastAPI** — simples, sem Celery/Redis. Para escala maior, migrar para filas (Redis + RQ ou Cloud Tasks).
- **Service Role Key no backend** — o backend usa a chave service role para bypassar RLS onde necessário (ex: identificar aluno). As políticas RLS protegem o acesso direto via frontend.
- **Polling de status** — o frontend usa React Query com `refetchInterval` para checar o progresso. Para produção maior, considerar WebSockets ou Server-Sent Events.
- **difflib para detecção de cópia** — suficiente para texto curto. Threshold de 75% foi calibrado para evitar falsos positivos em respostas factuais curtas.

---

## Fluxo do usuário

1. Professor cria conta no Supabase Auth (ou pelo dashboard do Supabase)
2. Faz login → dashboard com resumo das turmas
3. Cria turma → cadastra alunos
4. Cria atividade → define questões e gabarito (opcional)
5. Faz upload das provas físicas (foto ou PDF escaneado)
6. IA transcreve, identifica o aluno, corrige e gera feedback
7. Professor vê resultados com flags de possível cópia/IA
8. Aluno pode ser acessado pelo dashboard individual com gráficos de evolução
