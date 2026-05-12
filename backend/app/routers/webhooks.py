"""Webhook do Stripe — ativa/desativa planos conforme eventos de assinatura."""
import asyncio
import logging

import stripe
from fastapi import APIRouter, HTTPException, Request

from app.config import settings
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """Recebe eventos do Stripe, valida a assinatura e atualiza o plano do professor."""
    if not settings.stripe_secret_key or not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhooks não configurados.")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.SignatureVerificationError) as exc:
        logger.warning("Webhook Stripe com assinatura inválida: %s", exc)
        raise HTTPException(status_code=400, detail="Assinatura inválida.")

    event_type: str = event["type"]
    supabase = get_supabase()

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        professor_id = session.get("client_reference_id") or (session.get("metadata") or {}).get("professor_id")
        if professor_id:
            await asyncio.to_thread(
                supabase.table("professores").update({
                    "plano": "pago",
                    "plano_ativo_em": "now()",
                    "stripe_customer_id": session.get("customer"),
                    "stripe_subscription_id": session.get("subscription"),
                }).eq("id", professor_id).execute
            )
            logger.info(
                "Plano pago ativado para professor %s", professor_id,
                extra={"professor_id": professor_id, "event": event_type},
            )

    elif event_type == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        sub_id = subscription["id"]
        await asyncio.to_thread(
            supabase.table("professores").update({
                "plano": "free_trial",
                "stripe_subscription_id": None,
            }).eq("stripe_subscription_id", sub_id).execute
        )
        logger.info(
            "Assinatura cancelada: %s — professor voltou ao free_trial", sub_id,
            extra={"subscription_id": sub_id, "event": event_type},
        )

    elif event_type == "invoice.payment_failed":
        # Assinatura com pagamento em atraso: bloquear até regularização
        customer_id = event["data"]["object"].get("customer")
        if customer_id:
            await asyncio.to_thread(
                supabase.table("professores").update({
                    "plano": "bloqueado",
                }).eq("stripe_customer_id", customer_id).execute
            )
            logger.warning(
                "Pagamento falhou para customer %s — conta bloqueada", customer_id,
                extra={"customer_id": customer_id, "event": event_type},
            )

    return {"received": True}
