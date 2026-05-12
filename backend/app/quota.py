import asyncio

from fastapi import HTTPException


async def checar_limite_tokens(professor_id: str, supabase) -> None:
    """Bloqueia a operação se a conta está bloqueada ou se os tokens se esgotaram.

    Ordem de verificação:
    1. plano='bloqueado' → 402 sempre (cota já esgotada anteriormente)
    2. plano='pago'      → sem limite, passa direto
    3. plano='free_trial' → verifica input E output separadamente
    """
    prof = await asyncio.to_thread(
        supabase.table("professores")
        .select("plano, input_tokens_usados, output_tokens_usados, input_tokens_limite, output_tokens_limite")
        .eq("id", professor_id)
        .single()
        .execute
    )
    if not prof.data:
        raise HTTPException(status_code=404, detail="Professor não encontrado.")

    plano: str = prof.data.get("plano") or "free_trial"

    if plano == "bloqueado":
        raise HTTPException(
            status_code=402,
            detail="Conta bloqueada: cota do plano gratuito esgotada. Assine um plano para continuar.",
        )

    if plano == "pago":
        return

    # free_trial — checa limites de entrada e saída separadamente
    input_usados: int = prof.data.get("input_tokens_usados") or 0
    output_usados: int = prof.data.get("output_tokens_usados") or 0
    input_limite: int = prof.data.get("input_tokens_limite") or 0
    output_limite: int = prof.data.get("output_tokens_limite") or 0

    if input_limite > 0 and input_usados >= input_limite:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Cota de tokens de entrada esgotada "
                f"({input_usados:,}/{input_limite:,}). "
                "Assine um plano para continuar."
            ),
        )
    if output_limite > 0 and output_usados >= output_limite:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Cota de tokens de saída esgotada "
                f"({output_usados:,}/{output_limite:,}). "
                "Assine um plano para continuar."
            ),
        )
