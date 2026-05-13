"""Endpoints de pagamento via AbacatePay: recargas de tokens avulsas."""
import asyncio
import logging
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import PACOTES_TOKENS, PACOTES_PRECO_CENTAVOS, settings
from app.db.supabase_client import get_supabase
from app.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pagamento", tags=["pagamento"])

_ABACATE_URL = "https://api.abacatepay.com/v2"


class CheckoutRequest(BaseModel):
    pacote: Literal["starter", "regular", "pro"]


def _headers() -> dict:
    if not settings.abacatepay_api_key:
        raise HTTPException(status_code=503, detail="Pagamentos não configurados.")
    return {
        "Authorization": f"Bearer {settings.abacatepay_api_key}",
        "Content-Type": "application/json",
    }


@router.post("/checkout")
async def criar_checkout(
    body: CheckoutRequest,
    current_user: dict = Depends(get_current_user),
):
    """Cria um checkout no AbacatePay para o pacote de recarga escolhido."""
    supabase = get_supabase()
    prof = await asyncio.to_thread(
        supabase.table("professores")
        .select("nome, email")
        .eq("id", current_user["id"])
        .single()
        .execute
    )
    if not prof.data:
        raise HTTPException(status_code=404, detail="Professor não encontrado.")

    produto_id = settings.produto_id(body.pacote)
    # externalId codifica professor_id + pacote para o webhook identificar a recarga
    external_id = f"{current_user['id']}:{body.pacote}"

    headers = _headers()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{_ABACATE_URL}/checkouts/create",
            headers=headers,
            json={
                "items": [{"id": produto_id, "quantity": 1}],
                "returnUrl": f"{settings.frontend_url}/perfil?cancelado=true",
                "completionUrl": f"{settings.frontend_url}/perfil?sucesso=true",
                "externalId": external_id,
                "customer": {
                    "name": prof.data.get("nome", ""),
                    "email": prof.data.get("email", ""),
                },
            },
        )

    if resp.status_code not in (200, 201) or not resp.json().get("success"):
        logger.error("AbacatePay checkout error %d: %s", resp.status_code, resp.text)
        raise HTTPException(status_code=502, detail="Erro ao criar cobrança. Tente novamente.")

    payload = resp.json()
    url = (payload.get("data") or {}).get("url")
    if not url:
        logger.error("AbacatePay retornou sem URL: %s", payload)
        raise HTTPException(status_code=502, detail="URL de pagamento não retornada.")

    input_t, output_t = PACOTES_TOKENS[body.pacote]
    logger.info(
        "Checkout criado: professor=%s pacote=%s tokens=%dM+%dM",
        current_user["id"], body.pacote, input_t // 1_000_000, output_t // 1_000_000,
    )
    return {"url": url}
