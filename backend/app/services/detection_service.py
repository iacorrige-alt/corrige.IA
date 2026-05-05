"""
Copy / Plagiarism Detection Service.

After all students are graded, compare dissertation answers across students.
If SequenceMatcher similarity > 0.75, flag both as "copia".
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from difflib import SequenceMatcher
from itertools import combinations

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.75
# Jaccard threshold is intentionally loose — its job is only to skip obviously
# dissimilar pairs cheaply, not to flag copies on its own.
_JACCARD_PREFILTER = 0.40


def _jaccard_word_similarity(a: str, b: str) -> float:
    """Cheap O(|a|+|b|) word-level Jaccard similarity used as a pre-filter gate.

    Returns a value in [0, 1]. Two texts with no words in common return 0.0.
    """
    set_a = set(a.split())
    set_b = set(b.split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _calcular_flags(
    questao_map: dict[str, list[tuple[str, str, str]]],
) -> list[dict]:
    """CPU-bound: compare all answer pairs per question. Runs in a thread pool.

    Two-stage pipeline:
      1. Jaccard word overlap (O(n)) — skip pairs with < 40% overlap instantly.
      2. SequenceMatcher character ratio (O(n²)) — only on candidates that pass stage 1.

    This reduces SequenceMatcher calls by ~60–80% on typical classroom data.
    """
    flags: list[dict] = []
    for questao_id, entries in questao_map.items():
        if len(entries) < 2:
            continue
        for (_, resp_id_a, txt_a), (_, resp_id_b, txt_b) in combinations(entries, 2):
            a_norm = txt_a.lower()
            b_norm = txt_b.lower()

            # Stage 1: cheap pre-filter
            if _jaccard_word_similarity(a_norm, b_norm) < _JACCARD_PREFILTER:
                continue

            # Stage 2: precise character-level ratio
            ratio = SequenceMatcher(None, a_norm, b_norm).ratio()
            if ratio >= SIMILARITY_THRESHOLD:
                logger.info(
                    "Copia detectada questao %s | similaridade %.2f | %s <-> %s",
                    questao_id, ratio, resp_id_a, resp_id_b,
                )
                comentario = (
                    f"[ATENCAO] Similaridade de {ratio:.0%} detectada com outra resposta. "
                    "Possivel copia entre alunos."
                )
                for resp_id in (resp_id_a, resp_id_b):
                    flags.append({"id": resp_id, "comentario_ia": comentario})
    return flags


async def detectar_copias(atividade_id: str) -> None:
    """Compare all dissertation answers within an activity and flag copies."""
    supabase = get_supabase()

    resultados = await asyncio.to_thread(
        supabase.table("resultados")
        .select("id, aluno_id, respostas(*)")
        .eq("atividade_id", atividade_id)
        .execute
    )

    if not resultados.data or len(resultados.data) < 2:
        return

    # Preserva flags já atribuídas (ex: "ia") — não sobrescrever com "copia"
    resp_flags: dict[str, str | None] = {
        resp["id"]: resp.get("flag_tipo")
        for resultado in resultados.data
        for resp in (resultado.get("respostas") or [])
    }

    # questao_id → [(resultado_id, resposta_id, texto)]
    questao_map: dict[str, list[tuple[str, str, str]]] = {}

    for resultado in resultados.data:
        for resp in (resultado.get("respostas") or []):
            texto = resp.get("texto_resposta") or ""
            if not texto.strip():
                continue
            qid = resp["questao_id"]
            questao_map.setdefault(qid, []).append(
                (resultado["id"], resp["id"], texto)
            )

    flags_to_update = await asyncio.to_thread(_calcular_flags, questao_map)

    if not flags_to_update:
        return

    # Agrupar por comentário para minimizar roundtrips ao banco
    grupos: dict[str, list[str]] = defaultdict(list)
    for flag in flags_to_update:
        grupos[flag["comentario_ia"]].append(flag["id"])

    for comentario, ids in grupos.items():
        # Respostas sem flag: atribui "copia" + comentário
        ids_sem_flag = [i for i in ids if not resp_flags.get(i)]
        # Respostas com flag existente (ex: "ia"): preserva o flag, atualiza só o comentário
        ids_com_flag = [i for i in ids if resp_flags.get(i)]

        if ids_sem_flag:
            await asyncio.to_thread(
                supabase.table("respostas")
                .update({"flag_tipo": "copia", "comentario_ia": comentario})
                .in_("id", ids_sem_flag)
                .execute
            )
        if ids_com_flag:
            await asyncio.to_thread(
                supabase.table("respostas")
                .update({"comentario_ia": comentario})
                .in_("id", ids_com_flag)
                .execute
            )
