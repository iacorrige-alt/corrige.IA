"""
Testes para checar_limite_tokens com o novo sistema de planos.

Cobre:
- Professor não encontrado → 404
- Plano 'bloqueado' → 402 imediato
- Plano 'pago' → sem restrição de tokens
- Plano 'free_trial': abaixo do limite → passa; no limite → 402; acima → 402
- Limite zero → tratado como sem limite
- Valores None tratados como 0
"""
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.quota import checar_limite_tokens


def _mock(
    plano: str = "free_trial",
    input_usados: int = 0,
    output_usados: int = 0,
    input_limite: int = 5_000_000,
    output_limite: int = 5_000_000,
    found: bool = True,
):
    sb = MagicMock()
    data = {
        "plano": plano,
        "input_tokens_usados": input_usados,
        "output_tokens_usados": output_usados,
        "input_tokens_limite": input_limite,
        "output_tokens_limite": output_limite,
    } if found else None
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
        sb = _mock(found=False)
        with pytest.raises(HTTPException) as exc:
            await checar_limite_tokens("prof-1", sb)
        assert exc.value.status_code == 404

    async def test_plano_bloqueado_levanta_402(self):
        sb = _mock(plano="bloqueado", input_usados=0, output_usados=0)
        with pytest.raises(HTTPException) as exc:
            await checar_limite_tokens("prof-1", sb)
        assert exc.value.status_code == 402

    async def test_plano_pago_sem_limite(self):
        # conta paga nunca é bloqueada independente do uso
        sb = _mock(plano="pago", input_usados=99_999_999, output_usados=99_999_999)
        await checar_limite_tokens("prof-1", sb)  # não deve levantar

    async def test_free_trial_abaixo_do_limite_passa(self):
        sb = _mock(plano="free_trial", input_usados=1_000_000, output_usados=500_000)
        await checar_limite_tokens("prof-1", sb)  # não deve levantar

    async def test_free_trial_input_no_limite_levanta_402(self):
        sb = _mock(plano="free_trial", input_usados=5_000_000, output_usados=0)
        with pytest.raises(HTTPException) as exc:
            await checar_limite_tokens("prof-1", sb)
        assert exc.value.status_code == 402

    async def test_free_trial_output_no_limite_levanta_402(self):
        sb = _mock(plano="free_trial", input_usados=0, output_usados=5_000_000)
        with pytest.raises(HTTPException) as exc:
            await checar_limite_tokens("prof-1", sb)
        assert exc.value.status_code == 402

    async def test_free_trial_acima_do_limite_levanta_402(self):
        sb = _mock(plano="free_trial", input_usados=6_000_000, output_usados=0)
        with pytest.raises(HTTPException) as exc:
            await checar_limite_tokens("prof-1", sb)
        assert exc.value.status_code == 402

    async def test_limite_zero_tratado_como_sem_limite(self):
        # limite=0 significa conta sem restrição (contas administrativas)
        sb = _mock(plano="free_trial", input_usados=999_999, input_limite=0, output_limite=0)
        await checar_limite_tokens("prof-1", sb)  # não deve levantar

    async def test_tokens_none_tratados_como_zero(self):
        sb = _mock(plano="free_trial", input_usados=None, output_usados=None)
        await checar_limite_tokens("prof-1", sb)  # não deve levantar
