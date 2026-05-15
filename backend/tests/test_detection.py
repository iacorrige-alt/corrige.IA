"""
Testes para o serviço de detecção de cópias por embeddings.

Cobre _cosine e _calcular_flags com mocks da API de embeddings.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.detection_service import _cosine, _calcular_flags, SIMILARITY_THRESHOLD


# ─── Vetores auxiliares ────────────────────────────────────────────────────────

_VEC_A = [1.0, 0.0, 0.0]  # idêntico a si mesmo → sim=1.0
_VEC_B = [1.0, 0.0, 0.0]  # cópia exata
_VEC_C = [0.0, 1.0, 0.0]  # ortogonal → sim=0.0


def _make_embed_mock(*vecs):
    """Retorna um AsyncMock que simula _embed retornando os vetores fornecidos."""
    async def _fake_embed(texts):
        return list(vecs[:len(texts)]), len(texts) * 10
    return _fake_embed


# ─── Testes de _cosine ─────────────────────────────────────────────────────────

class TestCosine:
    def test_vetores_identicos(self):
        assert abs(_cosine(_VEC_A, _VEC_B) - 1.0) < 1e-9

    def test_vetores_ortogonais(self):
        assert abs(_cosine(_VEC_A, _VEC_C)) < 1e-9

    def test_vetor_zero_retorna_zero(self):
        assert _cosine([0.0, 0.0], [1.0, 0.0]) == 0.0

    def test_simetria(self):
        v1 = [0.6, 0.8, 0.0]
        v2 = [0.8, 0.6, 0.0]
        assert abs(_cosine(v1, v2) - _cosine(v2, v1)) < 1e-9

    def test_similaridade_parcial(self):
        v1 = [1.0, 1.0, 0.0]
        v2 = [1.0, 0.0, 1.0]
        sim = _cosine(v1, v2)
        assert 0.0 < sim < 1.0


# ─── Testes de _calcular_flags ─────────────────────────────────────────────────

class TestCalcularFlags:
    def _entrada(self, questao_id, pares):
        return {questao_id: pares}

    @pytest.mark.asyncio
    async def test_textos_identicos_sao_flagados(self):
        qmap = self._entrada("q1", [
            ("res1", "resp1", "A velocidade da luz é aproximadamente 300000 km/s no vácuo"),
            ("res2", "resp2", "A velocidade da luz é aproximadamente 300000 km/s no vácuo"),
        ])
        with patch("app.services.detection_service._embed", _make_embed_mock(_VEC_A, _VEC_B)):
            flags, _ = await _calcular_flags(qmap)
        assert len(flags) == 2
        assert {f["id"] for f in flags} == {"resp1", "resp2"}

    @pytest.mark.asyncio
    async def test_textos_dissimilares_nao_sao_flagados(self):
        qmap = self._entrada("q1", [
            ("res1", "resp1", "A resposta correta é a alternativa A"),
            ("res2", "resp2", "Não tenho certeza desta resposta de jeito nenhum"),
        ])
        with patch("app.services.detection_service._embed", _make_embed_mock(_VEC_A, _VEC_C)):
            flags, _ = await _calcular_flags(qmap)
        assert flags == []

    @pytest.mark.asyncio
    async def test_um_unico_aluno_nao_compara(self):
        qmap = self._entrada("q1", [("res1", "resp1", "Qualquer resposta aqui válida")])
        flags, tokens = await _calcular_flags(qmap)
        assert flags == []
        assert tokens == 0

    @pytest.mark.asyncio
    async def test_questao_vazia_nao_compara(self):
        flags, tokens = await _calcular_flags({"q1": []})
        assert flags == []
        assert tokens == 0

    @pytest.mark.asyncio
    async def test_texto_curto_ignorado(self):
        # Textos com menos de _MIN_TEXT_LEN chars são filtrados antes do embed
        qmap = self._entrada("q1", [
            ("res1", "resp1", "curto"),
            ("res2", "resp2", "curto"),
        ])
        flags, tokens = await _calcular_flags(qmap)
        assert flags == []
        assert tokens == 0

    @pytest.mark.asyncio
    async def test_tres_alunos_com_respostas_iguais_flagam_todos(self):
        texto = "A fórmula de Bhaskara resolve equações do segundo grau com delta"
        qmap = self._entrada("q1", [
            ("res1", "resp1", texto),
            ("res2", "resp2", texto),
            ("res3", "resp3", texto),
        ])
        with patch("app.services.detection_service._embed", _make_embed_mock(_VEC_A, _VEC_B, _VEC_A)):
            flags, _ = await _calcular_flags(qmap)
        flagged_ids = {f["id"] for f in flags}
        assert {"resp1", "resp2", "resp3"} == flagged_ids

    @pytest.mark.asyncio
    async def test_multiplas_questoes_independentes(self):
        texto_longo = "esta é uma resposta longa o suficiente para ser embeddada corretamente"
        qmap = {
            "q1": [
                ("r1", "resp1", texto_longo),
                ("r2", "resp2", texto_longo),
            ],
            "q2": [
                ("r1", "resp3", texto_longo),
                ("r2", "resp4", texto_longo),
            ],
        }

        call_count = 0

        async def _embed_alternado(texts):
            nonlocal call_count
            call_count += 1
            # q1: vetores iguais (cópia), q2: vetores ortogonais (sem cópia)
            if call_count == 1:
                return [_VEC_A] * len(texts), len(texts) * 10
            return [_VEC_A, _VEC_C], len(texts) * 10

        with patch("app.services.detection_service._embed", _embed_alternado):
            flags, _ = await _calcular_flags(qmap)

        flagged_ids = {f["id"] for f in flags}
        assert "resp1" in flagged_ids
        assert "resp2" in flagged_ids
        assert "resp3" not in flagged_ids
        assert "resp4" not in flagged_ids

    @pytest.mark.asyncio
    async def test_erro_no_embed_pula_questao(self):
        qmap = self._entrada("q1", [
            ("res1", "resp1", "resposta suficientemente longa para embeddar"),
            ("res2", "resp2", "outra resposta suficientemente longa também"),
        ])

        async def _embed_falha(texts):
            raise RuntimeError("API indisponível")

        with patch("app.services.detection_service._embed", _embed_falha):
            flags, tokens = await _calcular_flags(qmap)

        assert flags == []
        assert tokens == 0

    @pytest.mark.asyncio
    async def test_tokens_sao_acumulados(self):
        qmap = {
            "q1": [("r1", "resp1", "resposta longa o suficiente para o embed funcionar aqui"),
                   ("r2", "resp2", "outra resposta longa o suficiente para o embed funcionar")],
            "q2": [("r1", "resp3", "mais uma resposta longa o suficiente para embeddar"),
                   ("r2", "resp4", "e outra resposta longa o suficiente para embeddar também")],
        }

        async def _embed_com_tokens(texts):
            return [_VEC_C] * len(texts), 50  # 50 tokens por chamada

        with patch("app.services.detection_service._embed", _embed_com_tokens):
            _, total_tokens = await _calcular_flags(qmap)

        assert total_tokens == 100  # 2 questões × 50 tokens
