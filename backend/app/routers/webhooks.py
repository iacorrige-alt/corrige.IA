"""Webhook do AbacatePay v2 — adiciona tokens de recarga ao completar checkout."""
import asyncio
import base64
import hashlib
import hmac
import json
import logging
import uuid as _uuid

from fastapi import APIRouter, HTTPException, Request

from app.config import PACOTES_TOKENS, settings
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verificar_assinatura(payload: bytes, sig_header: str) -> bool:
    """Valida HMAC-SHA256 enviado pelo AbacatePay no header X-Webhook-Signature."""
    if not settings.abacatepay_webhook_secret or not sig_header:
        return False
    expected = base64.b64encode(
        hmac.new(
            settings.abacatepay_webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).digest()
    ).decode()
    return hmac.compare_digest(expected, sig_header.strip())


def _parse_professor_id(external_id: str) -> tuple[str | None, str | None]:
    """Extrai e valida (professor_id, pacote) do externalId '{uuid}:{pacote}'."""
    parts = external_id.split(":", 1)
    professor_id_str = parts[0] if parts else None
    pacote = parts[1] if len(parts) > 1 else None

    if not professor_id_str:
        return None, None
    try:
        _uuid.UUID(professor_id_str)  # valida formato UUID
    except ValueError:
        return None, None

    return professor_id_str, pacote


@router.post("/abacatepay")
async def abacatepay_webhook(request: Request):
    """Recebe eventos do AbacatePay v2.

    checkout.completed → adiciona tokens de recarga (idempotente via webhook_events)
    checkout.lost      → log apenas (PIX expirado — usuário pode tentar novamente)
    """
    if not settings.abacatepay_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhooks não configurados.")

    payload = await request.body()
    sig_header = request.headers.get("X-Webhook-Signature", "")
    if not _verificar_assinatura(payload, sig_header):
        logger.warning("Webhook com assinatura inválida (sig=%s…)", sig_header[:12])
        raise HTTPException(status_code=403, detail="Assinatura inválida.")

    try:
        event_data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Payload inválido.")

    event: str = event_data.get("event", "")
    data: dict = event_data.get("data", {})
    supabase = get_supabase()

    logger.info("Webhook AbacatePay: %s", event)

    if event == "checkout.completed":
        checkout = data.get("checkout") or data
        checkout_id = checkout.get("id")
        external_id: str = checkout.get("externalId", "")

        professor_id, pacote = _parse_professor_id(external_id)
        if not professor_id or pacote not in PACOTES_TOKENS:
            logger.error("checkout.completed com externalId inválido: %s", external_id)
            return {"received": True}

        # Idempotência: registra o evento — falha silenciosa = já processado
        if checkout_id:
            try:
                await asyncio.to_thread(
                    supabase.table("webhook_events").insert({
                        "id": checkout_id,
                        "evento": event,
                    }).execute
                )
            except Exception as exc:
                err_str = str(exc).lower()
                if any(kw in err_str for kw in ("23505", "unique", "duplicate")):
                    logger.info("Checkout %s já processado (idempotência)", checkout_id)
                    return {"received": True}
                logger.error("Erro ao registrar webhook_event %s: %s", checkout_id, exc)
                raise HTTPException(status_code=500, detail="Erro interno ao processar evento.") from exc

        input_t, output_t = PACOTES_TOKENS[pacote]
        await asyncio.to_thread(
            supabase.rpc("adicionar_tokens_recarga", {
                "p_professor_id": professor_id,
                "p_input_tokens": input_t,
                "p_output_tokens": output_t,
            }).execute
        )
        logger.info(
            "Recarga %s aplicada: professor=%s +%dM input +%dM output",
            pacote, professor_id, input_t // 1_000_000, output_t // 1_000_000,
        )

    elif event == "checkout.lost":
        checkout = data.get("checkout") or data
        logger.warning("Checkout expirado/perdido: externalId=%s", checkout.get("externalId"))

    return {"received": True}
