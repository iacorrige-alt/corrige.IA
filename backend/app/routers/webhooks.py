"""Webhook do AbacatePay v2 — ativa/desativa planos conforme eventos de pagamento."""
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
    """Valida HMAC-SHA256 enviado pelo AbacatePay no header X-Webhook-Signature.

    O AbacatePay usa o 'secret' definido no cadastro do webhook como chave do HMAC.
    """
    if not settings.abacatepay_webhook_secret or not sig_header:
        return False
    expected = base64.b64encode(
        hmac.new(
            settings.abacatepay_webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).digest()
    ).decode()
    return hmac.compare_digest(expected, sig_header)


@router.post("/abacatepay")
async def abacatepay_webhook(request: Request):
    """Recebe eventos do AbacatePay v2 e atualiza o plano do professor.

    Eventos tratados:
      checkout.completed    → ativa plano pago
      subscription.completed → ativa plano pago (via assinatura)
      subscription.renewed  → mantém plano ativo
      subscription.cancelled → volta para free_trial
      checkout.lost         → bloqueia conta (pagamento perdido)
    """
    if not settings.abacatepay_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhooks não configurados.")

    payload = await request.body()

    sig_header = request.headers.get("X-Webhook-Signature", "")
    if not _verificar_assinatura(payload, sig_header):
        logger.warning(
            "Webhook AbacatePay com assinatura inválida (sig=%s…)", sig_header[:12]
        )
        raise HTTPException(status_code=403, detail="Assinatura inválida.")

    try:
        event_data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Payload inválido.")

    event: str = event_data.get("event", "")
    data: dict = event_data.get("data", {})
    supabase = get_supabase()

    logger.info("Webhook AbacatePay: %s", event, extra={"event": event})

    # ── Checkout pago ─────────────────────────────────────────────────────────
    if event == "checkout.completed":
        checkout = data.get("checkout") or data
        professor_id = checkout.get("externalId")
        customer_id = checkout.get("customerId")

        if professor_id:
            await asyncio.to_thread(
                supabase.table("professores").update({
                    "plano": "pago",
                    "plano_ativo_em": "now()",
                    **({"abacatepay_customer_id": customer_id} if customer_id else {}),
                }).eq("id", professor_id).execute
            )
            logger.info(
                "Plano pago ativado (checkout) para professor %s", professor_id,
                extra={"professor_id": professor_id},
            )

    # ── Assinatura ativada ────────────────────────────────────────────────────
    elif event == "subscription.completed":
        subscription = data.get("subscription") or data
        sub_id = subscription.get("id")
        customer_id = subscription.get("customerId")
        # O externalId pode vir do checkout original que gerou a assinatura
        professor_id = subscription.get("externalId")

        update = {"plano": "pago", "plano_ativo_em": "now()"}
        if sub_id:
            update["abacatepay_subscription_id"] = sub_id

        if professor_id:
            await asyncio.to_thread(
                supabase.table("professores").update(update)
                .eq("id", professor_id).execute
            )
        elif customer_id:
            await asyncio.to_thread(
                supabase.table("professores").update(update)
                .eq("abacatepay_customer_id", customer_id).execute
            )
        logger.info("Assinatura ativada: %s", sub_id, extra={"subscription_id": sub_id})

    # ── Renovação mensal ──────────────────────────────────────────────────────
    elif event == "subscription.renewed":
        subscription = data.get("subscription") or data
        sub_id = subscription.get("id")
        if sub_id:
            await asyncio.to_thread(
                supabase.table("professores")
                .update({"plano": "pago"})
                .eq("abacatepay_subscription_id", sub_id)
                .execute
            )
            logger.info("Assinatura renovada: %s", sub_id)

    # ── Assinatura cancelada ──────────────────────────────────────────────────
    elif event == "subscription.cancelled":
        subscription = data.get("subscription") or data
        sub_id = subscription.get("id")
        if sub_id:
            await asyncio.to_thread(
                supabase.table("professores").update({
                    "plano": "free_trial",
                    "abacatepay_subscription_id": None,
                }).eq("abacatepay_subscription_id", sub_id).execute
            )
            logger.info("Assinatura cancelada: %s", sub_id)

    # ── Pagamento perdido/expirado ────────────────────────────────────────────
    elif event == "checkout.lost":
        checkout = data.get("checkout") or data
        professor_id = checkout.get("externalId")
        if professor_id:
            await asyncio.to_thread(
                supabase.table("professores")
                .update({"plano": "bloqueado"})
                .eq("id", professor_id)
                .execute
            )
            logger.warning("Checkout perdido para professor %s", professor_id)

    return {"received": True}
