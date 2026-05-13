from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# ─── Auth ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    nome: str
    email: EmailStr
    password: str

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nome não pode ser vazio.")
        return v

    @field_validator("password")
    @classmethod
    def senha_minima(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Senha deve ter no mínimo 6 caracteres.")
        return v


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: int  # Unix timestamp
    user_id: str
    email: str
    nome: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ─── Professor ───────────────────────────────────────────────────────────────

class ProfessorOut(BaseModel):
    id: str
    nome: str
    email: str
    criado_em: datetime
    plano: str = "free_trial"
    input_tokens_usados: int = 0
    output_tokens_usados: int = 0
    input_tokens_limite: int = 2000000
    output_tokens_limite: int = 2000000
    abacatepay_customer_id: Optional[str] = None
    # campos legados mantidos para retrocompatibilidade
    tokens_usados: int = 0
    limite_tokens: int = 0


# ─── Turma ───────────────────────────────────────────────────────────────────

class TurmaUpdate(BaseModel):
    nome: Optional[str] = None
    disciplina: Optional[str] = None
    cor: Optional[str] = None

    @field_validator("nome", "disciplina")
    @classmethod
    def campos_nao_vazios(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Campo não pode ser vazio.")
        return v


class TurmaCreate(BaseModel):
    nome: str
    disciplina: str
    cor: str = "#6366f1"

    @field_validator("nome", "disciplina")
    @classmethod
    def campos_nao_vazios(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Campo não pode ser vazio.")
        return v


class TurmaOut(BaseModel):
    id: str
    professor_id: str
    nome: str
    disciplina: str
    cor: str
    criado_em: datetime
    total_alunos: int = 0
    total_atividades: int = 0


# ─── Aluno ───────────────────────────────────────────────────────────────────

class AlunoUpdate(BaseModel):
    nome: str

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nome não pode ser vazio.")
        return v


class AlunoCreate(BaseModel):
    nome: str

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nome não pode ser vazio.")
        return v


class AlunoOut(BaseModel):
    id: str
    turma_id: str
    nome: str
    initials: str
    criado_em: datetime
    media: Optional[float] = None


# ─── Atividade ───────────────────────────────────────────────────────────────

class AtividadeUpdate(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[Literal["prova", "atividade", "trabalho"]] = None

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Nome não pode ser vazio.")
        return v


class QuestaoCreate(BaseModel):
    enunciado: str
    gabarito: Optional[str] = None
    tipo: Literal["dissertativa", "multipla_escolha", "verdadeiro_falso"] = "dissertativa"
    peso: float = Field(default=1.0, gt=0, description="Peso da questão (deve ser maior que zero)")
    ordem: int = Field(default=1, ge=1)


class AtividadeCreate(BaseModel):
    turma_id: str
    nome: str
    tipo: Literal["prova", "atividade", "trabalho"] = "prova"
    modo_correcao: Literal["automatico", "semi-automatico"] = "automatico"
    gabarito_texto: Optional[str] = None
    questoes: list[QuestaoCreate] = []

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nome da atividade não pode ser vazio.")
        return v


class QuestaoOut(BaseModel):
    id: str
    atividade_id: str
    enunciado: str
    gabarito: Optional[str]
    tipo: str
    peso: float
    ordem: int


class AtividadeOut(BaseModel):
    id: str
    turma_id: str
    nome: str
    tipo: str
    status: str
    modo_correcao: str
    gabarito_texto: Optional[str]
    gabarito_pdf_path: Optional[str] = None
    gabarito_pdf_content_type: Optional[str] = None
    data_criacao: datetime
    data_correcao: Optional[datetime]
    questoes: Optional[list[QuestaoOut]] = None
    total_questoes: Optional[int] = None
    total_alunos: Optional[int] = None
    media_turma: Optional[float] = None
    uploads_com_erro: int = 0


# ─── Correção / Resultados ───────────────────────────────────────────────────

class RespostaOut(BaseModel):
    id: str
    questao_id: str
    texto_resposta: Optional[str]
    nota: Optional[float]
    status: Optional[str]
    comentario_ia: Optional[str]
    flag_tipo: Optional[str]


class ProvaOut(BaseModel):
    id: str
    storage_path: str
    tipo_arquivo: str
    signed_url: Optional[str] = None


class ResultadoOut(BaseModel):
    id: str
    atividade_id: str
    aluno_id: str
    aluno_nome: Optional[str]
    aluno_initials: Optional[str]
    nota_total: Optional[float]
    criado_em: datetime
    respostas: Optional[list[RespostaOut]] = None
    flags: Optional[list[str]] = None
    provas: Optional[list[ProvaOut]] = None


class RespostaUpdate(BaseModel):
    nota: float = Field(ge=0)


# ─── Upload ──────────────────────────────────────────────────────────────────

class GabaritoUploadResponse(BaseModel):
    message: str
    atividade_id: str
    gabarito_pdf_path: str


class UploadResponse(BaseModel):
    message: str
    upload_ids: list[str]
    atividade_id: str


class StatusResponse(BaseModel):
    atividade_id: str
    status: str
    progresso: int  # 0-100
    mensagem: str
    uploads_com_erro: int = 0


# ─── Dashboard da Turma ──────────────────────────────────────────────────────

class DistribuicaoNota(BaseModel):
    faixa: str
    count: int


class EvolucaoTurma(BaseModel):
    atividade: str
    data: str
    media: float
    total_alunos: int


class RankingAluno(BaseModel):
    aluno_id: str
    nome: str
    initials: str
    media: float
    total_atividades: int
    flags: list[str]


class AnaliseIATurma(BaseModel):
    resumo: str
    pontos_de_atencao: list[str]
    sugestoes_pedagogicas: list[str]
    sugestoes_metodologicas: list[str]


class DashboardTurma(BaseModel):
    turma_id: str
    turma_nome: str
    disciplina: str
    media_geral: float
    taxa_aprovacao: float
    total_alunos_avaliados: int
    total_atividades: int
    total_flags: int
    distribuicao: list[DistribuicaoNota]
    evolucao: list[EvolucaoTurma]
    ranking: list[RankingAluno]
    analise_ia: AnaliseIATurma


# ─── Dashboard do Aluno ──────────────────────────────────────────────────────

class RadarItem(BaseModel):
    disciplina: str
    nota: float


class EvolucaoItem(BaseModel):
    atividade: str
    nota: float
    data: str


class DashboardAluno(BaseModel):
    aluno: AlunoOut
    media_geral: float
    total_atividades: int
    evolucao: list[EvolucaoItem]
    radar: list[RadarItem]
    analise_ia: str
    flags_detectadas: list[str]


# ─── Questão (atualização) ────────────────────────────────────────────────────

class QuestaoUpdate(BaseModel):
    enunciado: Optional[str] = None
    gabarito: Optional[str] = None
    tipo: Optional[Literal["dissertativa", "multipla_escolha", "verdadeiro_falso"]] = None
    peso: Optional[float] = Field(default=None, gt=0)
    ordem: Optional[int] = Field(default=None, ge=1)


# ─── Perfil ──────────────────────────────────────────────────────────────────

class ProfessorUpdate(BaseModel):
    nome: str

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nome não pode ser vazio.")
        return v


class ChangePasswordRequest(BaseModel):
    senha_atual: str
    nova_senha: str

    @field_validator("nova_senha")
    @classmethod
    def senha_minima(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("A nova senha deve ter no mínimo 6 caracteres.")
        return v


# ─── Importação de Alunos ─────────────────────────────────────────────────────

class AlunoImportResult(BaseModel):
    criados: int
    nomes: list[str]
    erros: list[str]


# ─── Uploads ──────────────────────────────────────────────────────────────────

class UploadOut(BaseModel):
    id: str
    atividade_id: str
    aluno_id: Optional[str]
    aluno_nome: Optional[str]
    storage_path: str
    content_type: str
    tipo_arquivo: str
    signed_url: Optional[str] = None


class UploadAlunoUpdate(BaseModel):
    aluno_id: Optional[str] = None
