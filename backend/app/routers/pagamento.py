"""Endpoints de pagamento via Stripe: checkout e portal do cliente."""
import asyncio
import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.db.supabase_client import get_supabase
from app.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pagamento", tags=["pagamento"])


def _stripe():
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Pagamentos não configurados.")
    stripe.api_key = settings.stripe_secret_key
    return stripe


@router.post("/checkout")
async def criar_checkout(current_user: dict = Depends(get_current_user)):
    """Cria uma Stripe Checkout Session e retorna a URL de redirecionamento."""
    s = _stripe()
    supabase = get_supabase()

    prof = await asyncio.to_thread(
        supabase.table("professores")
        .select("stripe_customer_id, email, nome, plano")
        .eq("id", current_user["id"])
        .single()
        .execute
    )
    if not prof.data:
        raise HTTPException(status_code=404, detail="Professor não encontrado.")

    if prof.data.get("plano") == "pago":
        raise HTTPException(status_code=400, detail="Conta já possui plano ativo.")

    customer_id = prof.data.get("stripe_customer_id")
    if not customer_id:
        customer = await asyncio.to_thread(
            s.Customer.create,
            email=prof.data["email"],
            name=prof.data.get("nome"),
            metadata={"professor_id": current_user["id"]},
        )
        customer_id = customer.id
        await asyncio.to_thread(
            supabase.table("professores")
            .update({"stripe_customer_id": customer_id})
            .eq("id", current_user["id"])
            .execute
        )

    session = await asyncio.to_thread(
        s.checkout.Session.create,
        mode="subscription",
        payment_method_types=["card"],
        customer=customer_id,
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        success_url=f"{settings.frontend_url}/perfil?sucesso=true",
        cancel_url=f"{settings.frontend_url}/perfil",
        client_reference_id=current_user["id"],
        metadata={"professor_id": current_user["id"]},
    )
    return {"url": session.url}


@router.get("/portal")
async def abrir_portal(current_user: dict = Depends(get_current_user)):
    """Cria uma Stripe Billing Portal Session para o cliente gerenciar a assinatura."""
    s = _stripe()
    supabase = get_supabase()

    prof = await asyncio.to_thread(
        supabase.table("professores")
        .select("stripe_customer_id")
        .eq("id", current_user["id"])
        .single()
        .execute
    )
    customer_id = (prof.data or {}).get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="Nenhuma assinatura encontrada.")

    session = await asyncio.to_thread(
        s.billing_portal.Session.create,
        customer=customer_id,
        return_url=f"{settings.frontend_url}/perfil",
    )
    return {"url": session.url}
