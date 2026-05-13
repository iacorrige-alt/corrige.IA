"""
Testes de segurança dos endpoints HTTP.

Cobre:
- Autenticação obrigatória (403 sem token)
- IDOR em editar_resposta (403 quando resposta pertence a outra atividade)
- Atividade não encontrada retorna 404, não vaza dados de outros professores
- Quota esgotada retorna 402 antes de processar o upload
"""
import io
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_current_user

FAKE_USER = {"id": "prof-aaa", "email": "prof@test.com"}


@pytest.fixture
def client_auth():
    """TestClient com autenticação mockada."""
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth():
    """TestClient sem override de autenticação."""
    app.dependency_overrides.clear()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestAutenticacaoObrigatoria:
    """Endpoints protegidos devem rejeitar requisições sem token com 4xx."""

    def test_listar_atividades_sem_token_rejeitado(self, client_no_auth):
        resp = client_no_auth.get("/atividades")
        assert resp.status_code in (401, 403)

    def test_me_sem_token_rejeitado(self, client_no_auth):
        resp = client_no_auth.get("/auth/me")
        assert resp.status_code in (401, 403)

    def test_criar_atividade_sem_token_rejeitado(self, client_no_auth):
        resp = client_no_auth.post("/atividades", json={
            "turma_id": "t-1", "nome": "Prova", "tipo": "prova",
        })
        assert resp.status_code in (401, 403)


class TestAtividadeNaoEncontrada:
    """Atividade de outro professor deve retornar 404 (não 403 nem dados vazados)."""

    def test_editar_resposta_atividade_inexistente_retorna_404(self, client_auth):
        mock_sb = MagicMock()
        # atividade lookup → not found (não pertence a este professor)
        (
            mock_sb.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .single.return_value
            .execute.return_value
        ) = MagicMock(data=None)

        with patch("app.routers.atividades.get_supabase", return_value=mock_sb):
            resp = client_auth.patch(
                "/atividades/ativ-X/respostas/resp-1",
                json={"nota": 5.0},
            )
        assert resp.status_code == 404

    def test_status_atividade_inexistente_retorna_404(self, client_auth):
        mock_sb = MagicMock()
        (
            mock_sb.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .single.return_value
            .execute.return_value
        ) = MagicMock(data=None)

        with patch("app.routers.correcao.get_supabase", return_value=mock_sb):
            resp = client_auth.get("/atividades/ativ-X/status")
        assert resp.status_code == 404


class TestIDOR:
    """Proteção contra Insecure Direct Object Reference em editar_resposta."""

    def test_resposta_de_outra_atividade_retorna_403(self, client_auth):
        mock_sb = MagicMock()

        # Call 1: table("atividades").select("id").eq(id).eq(prof_id).single().execute
        # Caminho com dois .eq() antes do .single()
        (
            mock_sb.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .single.return_value
            .execute.return_value
        ) = MagicMock(data={"id": "ativ-A"})

        # Call 2: table("respostas").select(...).eq(id).single().execute
        # Caminho com um único .eq() antes do .single()
        (
            mock_sb.table.return_value
            .select.return_value
            .eq.return_value
            .single.return_value
            .execute.return_value
        ) = MagicMock(data={
            "id": "resp-1",
            "resultado_id": "res-1",
            "questao_id": "q-1",
            "questoes": {"peso": 2.0},
            "resultados": {"atividade_id": "ativ-B"},  # pertence a outra atividade!
        })

        with patch("app.routers.atividades.get_supabase", return_value=mock_sb):
            resp = client_auth.patch(
                "/atividades/ativ-A/respostas/resp-1",
                json={"nota": 1.5},
            )
        assert resp.status_code == 403

    def test_resposta_da_atividade_correta_aceita(self, client_auth):
        mock_sb = MagicMock()

        (
            mock_sb.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .single.return_value
            .execute.return_value
        ) = MagicMock(data={"id": "ativ-A"})

        (
            mock_sb.table.return_value
            .select.return_value
            .eq.return_value
            .single.return_value
            .execute.return_value
        ) = MagicMock(data={
            "id": "resp-1",
            "resultado_id": "res-1",
            "questao_id": "q-1",
            "questoes": {"peso": 10.0},
            "resultados": {"atividade_id": "ativ-A"},  # mesma atividade ✓
        })

        # update e resultado lookup também retornam mocks válidos
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

        with patch("app.routers.atividades.get_supabase", return_value=mock_sb):
            resp = client_auth.patch(
                "/atividades/ativ-A/respostas/resp-1",
                json={"nota": 7.0},
            )
        # Não esperamos 403 nem 404
        assert resp.status_code not in (403, 404)


class TestLockOrdemUpload:
    """Regressão: lock atômico deve ser adquirido ANTES do insert em uploads.
    Se o lock falhar (atividade já em 'corrigindo'), nenhuma linha de upload
    deve ser inserida no DB — evita uploads órfãos.
    """

    def test_lock_falha_nao_chama_insert(self, client_auth):
        mock_sb = MagicMock()

        # atividade lookup: encontrada, status=pendente
        (
            mock_sb.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .single.return_value
            .execute.return_value
        ) = MagicMock(data={"id": "ativ-A", "status": "pendente"})

        # lock atômico retorna data=[] → lock falhou (outro request foi mais rápido)
        mock_sb.table.return_value.update.return_value.eq.return_value.neq.return_value.execute.return_value = MagicMock(data=[])

        fake_file = io.BytesIO(b"conteudo")

        insert_mock = mock_sb.table.return_value.insert.return_value.execute

        with patch("app.routers.correcao.get_supabase", return_value=mock_sb), \
             patch("app.routers.correcao.checar_limite_tokens", new=AsyncMock()), \
             patch("app.routers.correcao.upload_file", new=AsyncMock(return_value="ativ-A/fake.jpg")):
            resp = client_auth.post(
                "/atividades/ativ-A/upload",
                files={"files": ("prova.jpg", fake_file, "image/jpeg")},
            )

        assert resp.status_code == 409
        # Insert em uploads NÃO deve ter sido chamado
        insert_mock.assert_not_called()

    def test_lock_sucesso_chama_insert(self, client_auth):
        mock_sb = MagicMock()

        (
            mock_sb.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .single.return_value
            .execute.return_value
        ) = MagicMock(data={"id": "ativ-A", "status": "pendente"})

        # lock retorna data com 1 item → sucesso
        mock_sb.table.return_value.update.return_value.eq.return_value.neq.return_value.execute.return_value = MagicMock(
            data=[{"id": "ativ-A", "status": "corrigindo"}]
        )
        mock_sb.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "upload-1"}]
        )

        fake_file = io.BytesIO(b"conteudo")

        with patch("app.routers.correcao.get_supabase", return_value=mock_sb), \
             patch("app.routers.correcao.checar_limite_tokens", new=AsyncMock()), \
             patch("app.routers.correcao.upload_file", new=AsyncMock(return_value="ativ-A/fake.jpg")), \
             patch("app.routers.correcao.corrigir_atividade"):
            resp = client_auth.post(
                "/atividades/ativ-A/upload",
                files={"files": ("prova.jpg", fake_file, "image/jpeg")},
            )

        assert resp.status_code == 200
        mock_sb.table.return_value.insert.return_value.execute.assert_called_once()


class TestQuotaUpload:
    """Upload deve ser bloqueado com 402 quando a cota de tokens está esgotada."""

    def test_upload_com_cota_esgotada_retorna_402(self, client_auth):
        mock_sb = MagicMock()
        # atividade lookup retorna dados válidos (status=pendente)
        (
            mock_sb.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .single.return_value
            .execute.return_value
        ) = MagicMock(data={"id": "ativ-A", "status": "pendente"})

        fake_file = io.BytesIO(b"conteudo falso")
        fake_file.name = "prova.jpg"

        with patch("app.routers.correcao.get_supabase", return_value=mock_sb), \
             patch(
                 "app.routers.correcao.checar_limite_tokens",
                 new=AsyncMock(side_effect=HTTPException(status_code=402, detail="Cota esgotada.")),
             ):
            resp = client_auth.post(
                "/atividades/ativ-A/upload",
                files={"files": ("prova.jpg", fake_file, "image/jpeg")},
            )
        assert resp.status_code == 402

    def test_upload_dentro_da_cota_nao_retorna_402(self, client_auth):
        mock_sb = MagicMock()
        (
            mock_sb.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .single.return_value
            .execute.return_value
        ) = MagicMock(data={"id": "ativ-A", "status": "pendente"})

        fake_file = io.BytesIO(b"conteudo falso")

        with patch("app.routers.correcao.get_supabase", return_value=mock_sb), \
             patch("app.routers.correcao.checar_limite_tokens", new=AsyncMock()):
            resp = client_auth.post(
                "/atividades/ativ-A/upload",
                files={"files": ("prova.jpg", fake_file, "image/jpeg")},
            )
        # Quota passou; pode falhar em outro ponto (upload de storage), mas não em 402
        assert resp.status_code != 402
