import asyncio

from fastapi import HTTPException


async def checar_limite_tokens(professor_id: str, supabase) -> None:
    """Levanta 402 se o professor esgotou sua cota de tokens.

    limite_tokens = 0 significa sem limite (útil para contas administrativas).
    """
    prof = await asyncio.to_thread(
        supabase.table("professores")
        .select("tokens_usados, limite_tokens")
        .eq("id", professor_id)
        .single()
        .execute
    )
    if not prof.data:
        raise HTTPException(status_code=404, detail="Professor não encontrado.")
    usados: int = prof.data.get("tokens_usados") or 0
    limite: int = prof.data.get("limite_tokens") or 0
    if limite > 0 and usados >= limite:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Cota de {limite:,} tokens atingida ({usados:,} usados). "
                "Entre em contato com o suporte para ampliar seu limite."
            ),
        )
