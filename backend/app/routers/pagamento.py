"""Endpoints de pagamento via AbacatePay: checkout e cancelamento."""
import asyncio
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.db.supabase_client import get_supabase
from app.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pagamento", tags=["pagamento"])

_ABACATE_URL = "https://api.abacatepay.com/v2"


def _headers() -> dict:
    if not settings.abacatepay_api_key:
        raise HTTPException(status_code=503, detail="Pagamentos não configurados.")
    return {
        "Authorization": f"Bearer {settings.abacatepay_api_key}",
        "Content-Type": "application/json",
    }


@router.post("/checkout")
async def criar_checkout(current_user: dict = Depends(get_current_user)):
    """Cria um billing no AbacatePay e retorna a URL de pagamento."""
    supabase = get_supabase()
    prof = await asyncio.to_thread(
        supabase.table("professores")
        .select("nome, email, plano")
        .eq("id", current_user["id"])
        .single()
        .execute
    )
    if not prof.data:
        raise HTTPException(status_code=404, detail="Professor não encontrado.")
    if prof.data.get("plano") == "pago":
        raise HTTPException(status_code=400, detail="Conta já possui plano ativo.")

    headers = _headers()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{_ABACATE_URL}/checkouts/create",
            headers=headers,
            json={
                "items": [{"id": settings.abacatepay_product_id, "quantity": 1}],
                "returnUrl": f"{settings.frontend_url}/perfil?cancelado=true",
                "completionUrl": f"{settings.frontend_url}/perfil?sucesso=true",
                "externalId": current_user["id"],
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

    return {"url": url}


@router.post("/cancelar")
async def cancelar_assinatura(current_user: dict = Depends(get_current_user)):
    """Cancela a assinatura ativa do professor no AbacatePay."""
    supabase = get_supabase()
    prof = await asyncio.to_thread(
        supabase.table("professores")
        .select("plano, abacatepay_subscription_id")
        .eq("id", current_user["id"])
        .single()
        .execute
    )
    if not prof.data:
        raise HTTPException(status_code=404, detail="Professor não encontrado.")
    if prof.data.get("plano") != "pago":
        raise HTTPException(status_code=400, detail="Nenhuma assinatura ativa para cancelar.")

    sub_id = prof.data.get("abacatepay_subscription_id")
    if sub_id:
        headers = _headers()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{_ABACATE_URL}/subscriptions/cancel",
                headers=headers,
                params={"id": sub_id},
            )
        if resp.status_code not in (200, 201, 204):
            logger.warning(
                "AbacatePay cancel error %d para sub %s: %s",
                resp.status_code, sub_id, resp.text,
            )

    # Atualiza o plano localmente independente do resultado da API
    await asyncio.to_thread(
        supabase.table("professores").update({
            "plano": "free_trial",
            "abacatepay_subscription_id": None,
        }).eq("id", current_user["id"]).execute
    )
    logger.info("Assinatura cancelada pelo professor %s", current_user["id"])
    return {"message": "Assinatura cancelada com sucesso."}
