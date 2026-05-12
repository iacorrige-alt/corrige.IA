"""Webhook do AbacatePay — ativa/desativa planos conforme eventos de pagamento."""
import asyncio
import base64
import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, HTTPException, Request

from app.config import settings
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verificar_assinatura(payload: bytes, sig_header: str) -> bool:
    """Valida o HMAC-SHA256 enviado pelo AbacatePay no header X-Webhook-Signature."""
    if not settings.abacatepay_api_key or not sig_header:
        return False
    expected = base64.b64encode(
        hmac.new(settings.abacatepay_api_key.encode(), payload, hashlib.sha256).digest()
    ).decode()
    return hmac.compare_digest(expected, sig_header)


@router.post("/abacatepay")
async def abacatepay_webhook(request: Request):
    """Recebe eventos do AbacatePay e atualiza o plano do professor.

    A URL registrada no dashboard deve incluir o webhook secret como query param:
    https://seu-backend/webhooks/abacatepay?webhookSecret=SEU_SECRET
    """
    if not settings.abacatepay_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhooks não configurados.")

    # Validação pelo query param webhookSecret
    webhook_secret = request.query_params.get("webhookSecret", "")
    if webhook_secret != settings.abacatepay_webhook_secret:
        logger.warning("Webhook AbacatePay com webhookSecret inválido")
        raise HTTPException(status_code=403, detail="Webhook secret inválido.")

    payload = await request.body()

    # Validação opcional pelo header HMAC (segunda camada de segurança)
    sig_header = request.headers.get("X-Webhook-Signature", "")
    if sig_header and not _verificar_assinatura(payload, sig_header):
        logger.warning("Webhook AbacatePay com assinatura HMAC inválida")
        raise HTTPException(status_code=400, detail="Assinatura inválida.")

    try:
        event_data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Payload inválido.")

    event: str = event_data.get("event", "")
    data: dict = event_data.get("data", {})
    supabase = get_supabase()

    logger.info("Webhook AbacatePay recebido: %s", event, extra={"event": event})

    # ── Pagamento de billing confirmado ───────────────────────────────────────
    if event in ("billing.completed", "checkout.completed"):
        billing = data.get("billing") or data.get("checkout") or {}
        professor_id = billing.get("externalId")
        customer = billing.get("customer") or {}
        customer_id = customer.get("id")
        subscription_id = billing.get("subscriptionId") or billing.get("subscription_id")

        if professor_id:
            await asyncio.to_thread(
                supabase.table("professores").update({
                    "plano": "pago",
                    "plano_ativo_em": "now()",
                    **({"abacatepay_customer_id": customer_id} if customer_id else {}),
                    **({"abacatepay_subscription_id": subscription_id} if subscription_id else {}),
                }).eq("id", professor_id).execute
            )
            logger.info(
                "Plano pago ativado para professor %s", professor_id,
                extra={"professor_id": professor_id, "event": event},
            )

    # ── Renovação mensal confirmada ───────────────────────────────────────────
    elif event == "subscription.renewed":
        subscription = data.get("subscription") or {}
        sub_id = subscription.get("id")
        if sub_id:
            # Garante que o plano continua ativo (caso tenha sido suspenso)
            await asyncio.to_thread(
                supabase.table("professores")
                .update({"plano": "pago"})
                .eq("abacatepay_subscription_id", sub_id)
                .execute
            )
            logger.info("Assinatura renovada: %s", sub_id, extra={"subscription_id": sub_id})

    # ── Assinatura cancelada ──────────────────────────────────────────────────
    elif event == "subscription.cancelled":
        subscription = data.get("subscription") or {}
        sub_id = subscription.get("id")
        if sub_id:
            await asyncio.to_thread(
                supabase.table("professores").update({
                    "plano": "free_trial",
                    "abacatepay_subscription_id": None,
                }).eq("abacatepay_subscription_id", sub_id).execute
            )
            logger.info(
                "Assinatura cancelada: %s", sub_id,
                extra={"subscription_id": sub_id, "event": event},
            )

    # ── Cobrança recusada (falha de pagamento) ────────────────────────────────
    elif event in ("billing.failed", "subscription.payment_failed"):
        subscription = data.get("subscription") or data.get("billing") or {}
        customer_id = (subscription.get("customer") or {}).get("id")
        if customer_id:
            await asyncio.to_thread(
                supabase.table("professores")
                .update({"plano": "bloqueado"})
                .eq("abacatepay_customer_id", customer_id)
                .execute
            )
            logger.warning(
                "Pagamento falhou para customer %s — conta bloqueada", customer_id,
                extra={"customer_id": customer_id, "event": event},
            )

    return {"received": True}
