import pytest
from pydantic import ValidationError
from app.models.schemas import (
    AlunoCreate,
    AlunoUpdate,
    ChangePasswordRequest,
    QuestaoCreate,
    RegisterRequest,
    RespostaUpdate,
    TurmaCreate,
)


class TestRegisterRequest:
    def test_valido(self):
        r = RegisterRequest(nome="Maria Silva", email="maria@example.com", password="senha123")
        assert r.nome == "Maria Silva"

    def test_nome_vazio_rejeitado(self):
        with pytest.raises(ValidationError):
            RegisterRequest(nome="  ", email="x@x.com", password="senha123")

    def test_senha_curta_rejeitada(self):
        with pytest.raises(ValidationError):
            RegisterRequest(nome="Ana", email="ana@x.com", password="abc")

    def test_email_invalido_rejeitado(self):
        with pytest.raises(ValidationError):
            RegisterRequest(nome="Ana", email="nao-e-email", password="senha123")

    def test_nome_strip(self):
        r = RegisterRequest(nome="  João  ", email="j@j.com", password="senha123")
        assert r.nome == "João"

    def test_senha_exatamente_seis_caracteres_aceita(self):
        r = RegisterRequest(nome="X", email="x@x.com", password="123456")
        assert r.password == "123456"


class TestChangePasswordRequest:
    def test_valido(self):
        r = ChangePasswordRequest(senha_atual="velha123", nova_senha="nova456")
        assert r.nova_senha == "nova456"

    def test_nova_senha_curta_rejeitada(self):
        with pytest.raises(ValidationError):
            ChangePasswordRequest(senha_atual="velha123", nova_senha="abc")

    def test_nova_senha_exatamente_seis_aceita(self):
        r = ChangePasswordRequest(senha_atual="velha123", nova_senha="123456")
        assert r.nova_senha == "123456"


class TestAlunoCreate:
    def test_valido(self):
        a = AlunoCreate(nome="Pedro Santos")
        assert a.nome == "Pedro Santos"

    def test_nome_vazio_rejeitado(self):
        with pytest.raises(ValidationError):
            AlunoCreate(nome="")

    def test_nome_so_espacos_rejeitado(self):
        with pytest.raises(ValidationError):
            AlunoCreate(nome="   ")

    def test_nome_strip(self):
        a = AlunoCreate(nome="  Luisa  ")
        assert a.nome == "Luisa"


class TestAlunoUpdate:
    def test_valido(self):
        a = AlunoUpdate(nome="Carlos Lima")
        assert a.nome == "Carlos Lima"

    def test_nome_vazio_rejeitado(self):
        with pytest.raises(ValidationError):
            AlunoUpdate(nome="")


class TestQuestaoCreate:
    def test_defaults(self):
        q = QuestaoCreate(enunciado="Explique X.")
        assert q.peso == 1.0
        assert q.tipo == "dissertativa"
        assert q.ordem == 1

    def test_peso_zero_rejeitado(self):
        with pytest.raises(ValidationError):
            QuestaoCreate(enunciado="Q", peso=0)

    def test_peso_negativo_rejeitado(self):
        with pytest.raises(ValidationError):
            QuestaoCreate(enunciado="Q", peso=-1)

    def test_peso_positivo_aceito(self):
        q = QuestaoCreate(enunciado="Q", peso=2.5)
        assert q.peso == 2.5

    def test_tipo_invalido_rejeitado(self):
        with pytest.raises(ValidationError):
            QuestaoCreate(enunciado="Q", tipo="invalido")


class TestRespostaUpdate:
    def test_valido(self):
        r = RespostaUpdate(nota=7.5)
        assert r.nota == 7.5

    def test_nota_negativa_rejeitada(self):
        with pytest.raises(ValidationError):
            RespostaUpdate(nota=-0.01)

    def test_nota_zero_aceita(self):
        r = RespostaUpdate(nota=0)
        assert r.nota == 0.0

    def test_nota_alta_aceita(self):
        r = RespostaUpdate(nota=100.0)
        assert r.nota == 100.0


class TestTurmaCreate:
    def test_valido(self):
        t = TurmaCreate(nome="7A", disciplina="Matemática")
        assert t.cor == "#6366f1"

    def test_nome_vazio_rejeitado(self):
        with pytest.raises(ValidationError):
            TurmaCreate(nome="", disciplina="Português")

    def test_disciplina_vazia_rejeitada(self):
        with pytest.raises(ValidationError):
            TurmaCreate(nome="8B", disciplina="  ")
