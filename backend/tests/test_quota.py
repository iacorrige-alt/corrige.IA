import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.quota import checar_limite_tokens


def _supabase_mock(tokens_usados: int, limite_tokens: int, found: bool = True):
    """Retorna um mock de Supabase que simula a query de quota."""
    sb = MagicMock()
    data = {"tokens_usados": tokens_usados, "limite_tokens": limite_tokens} if found else None
    (
        sb.table.return_value
        .select.return_value
        .eq.return_value
        .single.return_value
        .execute.return_value
    ) = MagicMock(data=data)
    return sb


class TestChecarLimiteTokens:
    async def test_professor_nao_encontrado_levanta_404(self):
        sb = _supabase_mock(0, 0, found=False)
        with pytest.raises(HTTPException) as exc:
            await checar_limite_tokens("prof-1", sb)
        assert exc.value.status_code == 404

    async def test_sem_limite_nao_bloqueia(self):
        # limite_tokens = 0 → sem limite (conta administrativa)
        sb = _supabase_mock(tokens_usados=999_999, limite_tokens=0)
        await checar_limite_tokens("prof-1", sb)  # não deve levantar

    async def test_abaixo_do_limite_passa(self):
        sb = _supabase_mock(tokens_usados=500, limite_tokens=1000)
        await checar_limite_tokens("prof-1", sb)  # não deve levantar

    async def test_exatamente_no_limite_levanta_402(self):
        sb = _supabase_mock(tokens_usados=1000, limite_tokens=1000)
        with pytest.raises(HTTPException) as exc:
            await checar_limite_tokens("prof-1", sb)
        assert exc.value.status_code == 402

    async def test_acima_do_limite_levanta_402(self):
        sb = _supabase_mock(tokens_usados=1500, limite_tokens=1000)
        with pytest.raises(HTTPException) as exc:
            await checar_limite_tokens("prof-1", sb)
        assert exc.value.status_code == 402

    async def test_mensagem_de_erro_menciona_limite(self):
        sb = _supabase_mock(tokens_usados=1000, limite_tokens=1000)
        with pytest.raises(HTTPException) as exc:
            await checar_limite_tokens("prof-1", sb)
        assert "1,000" in exc.value.detail or "1000" in exc.value.detail

    async def test_tokens_usados_none_tratado_como_zero(self):
        # DB pode retornar None antes do primeiro uso
        sb = _supabase_mock(tokens_usados=None, limite_tokens=100)
        await checar_limite_tokens("prof-1", sb)  # 0 < 100, não deve levantar
