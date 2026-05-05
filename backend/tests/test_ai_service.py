"""
Unit tests for ai_service critical functions.

Run with: pytest backend/tests/test_ai_service.py -v
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─── Fixtures ────────────────────────────────────────────────────────────────

ALUNOS = [
    {"id": "uuid-1", "nome": "João Silva"},
    {"id": "uuid-2", "nome": "Maria Santos"},
    {"id": "uuid-3", "nome": "Pedro Oliveira"},
]

QUESTOES = [
    {"id": "q-1", "ordem": 1, "enunciado": "Q1", "gabarito": "A", "peso": 2.0},
    {"id": "q-2", "ordem": 2, "enunciado": "Q2", "gabarito": None, "peso": 3.0},
]

ATIV = {
    "id": "ativ-1",
    "nome": "Prova Bimestral",
    "modo_correcao": "automatico",
    "gabarito_texto": None,
}


# ─── _identificar_aluno ───────────────────────────────────────────────────────

class TestIdentificarAluno:
    """Tests for student identification via GPT + fuzzy match."""

    def _mock_gpt_response(self, content: str):
        resp = MagicMock()
        resp.choices[0].message.content = content
        return resp

    @pytest.mark.asyncio
    async def test_exact_match(self):
        """GPT returns exact name → matched by direct dict lookup."""
        from app.services.ai_service import _identificar_aluno

        with patch("app.services.ai_service._openai_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = self._mock_gpt_response("João Silva")
            result = await _identificar_aluno("Nome: João Silva\nResposta: ...", ALUNOS)

        assert result == "uuid-1"

    @pytest.mark.asyncio
    async def test_fuzzy_match_accent(self):
        """GPT returns name without accent → matched by get_close_matches."""
        from app.services.ai_service import _identificar_aluno

        with patch("app.services.ai_service._openai_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = self._mock_gpt_response("Joao Silva")
            result = await _identificar_aluno("Nome: Joao Silva\nResposta: ...", ALUNOS)

        assert result == "uuid-1"

    @pytest.mark.asyncio
    async def test_no_match_returns_none(self):
        """GPT returns 'desconhecido' or unknown name → returns None."""
        from app.services.ai_service import _identificar_aluno

        with patch("app.services.ai_service._openai_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = self._mock_gpt_response("desconhecido")
            result = await _identificar_aluno("Nome ilegível\n...", ALUNOS)

        assert result is None

    @pytest.mark.asyncio
    async def test_empty_roster_returns_none(self):
        """Empty class list → immediately returns None without calling GPT."""
        from app.services.ai_service import _identificar_aluno

        with patch("app.services.ai_service._openai_call", new_callable=AsyncMock) as mock_call:
            result = await _identificar_aluno("Nome: Qualquer\n...", [])

        mock_call.assert_not_called()
        assert result is None


# ─── _corrigir_com_ia ────────────────────────────────────────────────────────

class TestCorrigirComIa:
    """Tests for GPT grading pipeline."""

    def _mock_gpt_json(self, payload: dict):
        resp = MagicMock()
        resp.choices[0].message.content = json.dumps(payload)
        return resp

    @pytest.mark.asyncio
    async def test_valid_json_returns_respostas(self):
        """Valid GPT JSON → returns list of respostas."""
        from app.services.ai_service import _corrigir_com_ia

        payload = {
            "respostas": [
                {"questao_id": "q-1", "status": "correto", "nota": 2.0, "comentario": "Certo!", "flag": None},
                {"questao_id": "q-2", "status": "parcial", "nota": 1.5, "comentario": "Incompleto.", "flag": None},
            ]
        }
        with patch("app.services.ai_service._openai_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = self._mock_gpt_json(payload)
            result = await _corrigir_com_ia("Resposta do aluno...", ATIV, QUESTOES)

        assert len(result) == 2
        assert result[0]["questao_id"] == "q-1"
        assert result[0]["nota"] == 2.0

    @pytest.mark.asyncio
    async def test_invalid_json_raises_runtime_error(self):
        """Invalid JSON from GPT → raises RuntimeError (not silent empty list)."""
        from app.services.ai_service import _corrigir_com_ia

        resp = MagicMock()
        resp.choices[0].message.content = "Desculpe, não consigo corrigir agora."  # plain text

        with patch("app.services.ai_service._openai_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = resp
            with pytest.raises(RuntimeError, match="JSON inválido"):
                await _corrigir_com_ia("Resposta do aluno...", ATIV, QUESTOES)

    @pytest.mark.asyncio
    async def test_missing_respostas_key_raises_runtime_error(self):
        """JSON without 'respostas' key → raises RuntimeError (not empty list)."""
        from app.services.ai_service import _corrigir_com_ia

        with patch("app.services.ai_service._openai_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = self._mock_gpt_json({"resultado": "ok"})
            with pytest.raises(RuntimeError, match="formato inesperado"):
                await _corrigir_com_ia("Resposta do aluno...", ATIV, QUESTOES)


# ─── _calcular_flags (detection service) ─────────────────────────────────────

class TestDetectarCopias:
    """Tests for the Jaccard pre-filter + SequenceMatcher pipeline."""

    def test_jaccard_gate_skips_dissimilar_pairs(self):
        """Pairs with low word overlap never reach SequenceMatcher."""
        from app.services.detection_service import _calcular_flags, _jaccard_word_similarity

        # Two completely different answers — Jaccard should gate them out
        txt_a = "A fotossíntese é o processo pelo qual as plantas produzem energia."
        txt_b = "A revolução francesa ocorreu em 1789 com queda da bastilha."

        jaccard = _jaccard_word_similarity(txt_a.lower(), txt_b.lower())
        assert jaccard < 0.40, f"Jaccard esperado < 0.40, obtido {jaccard:.2f}"

    def test_similar_answers_flagged_as_copia(self):
        """Highly similar answers exceed threshold → both flagged."""
        from app.services.detection_service import _calcular_flags

        txt = "A fotossíntese converte luz solar em energia química nas plantas verdes."
        # Slight variation — same sentence with one word changed
        txt_similar = "A fotossíntese converte luz solar em energia química nas plantas verdes presentes."

        questao_map = {
            "q-1": [
                ("res-1", "resp-id-1", txt),
                ("res-2", "resp-id-2", txt_similar),
            ]
        }
        flags = _calcular_flags(questao_map)
        flagged_ids = {f["id"] for f in flags}

        assert "resp-id-1" in flagged_ids
        assert "resp-id-2" in flagged_ids

    def test_single_student_no_comparison(self):
        """Only one student per question → nothing to compare → no flags."""
        from app.services.detection_service import _calcular_flags

        questao_map = {"q-1": [("res-1", "resp-id-1", "resposta única")]}
        flags = _calcular_flags(questao_map)

        assert flags == []
