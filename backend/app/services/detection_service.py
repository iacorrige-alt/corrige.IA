"""
Copy / Plagiarism Detection Service.

Uses OpenAI text-embedding-3-small to detect semantic similarity between
student answers. Catches paraphrasing and synonym substitution that
character-level methods miss, at ~100x lower cost than LLM calls.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from itertools import combinations
from math import sqrt

from openai import AsyncOpenAI

from app.config import settings
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=settings.openai_api_key)

_EMBED_MODEL = "text-embedding-3-small"
SIMILARITY_THRESHOLD = 0.93  # cosine — acima disso indica cópia ou paráfrase clara
_MIN_TEXT_LEN = 20            # respostas muito curtas têm embedding pouco confiável


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(x * x for x in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


async def _embed(texts: list[str]) -> tuple[list[list[float]], int]:
    """Batch embed texts. Returns (vectors, total_tokens)."""
    resp = await _client.embeddings.create(
        model=_EMBED_MODEL,
        input=texts,
        encoding_format="float",
    )
    vecs = [item.embedding for item in sorted(resp.data, key=lambda x: x.index)]
    tokens = resp.usage.total_tokens if resp.usage else 0
    return vecs, tokens


async def _calcular_flags(
    questao_map: dict[str, list[tuple[str, str, str]]],
) -> tuple[list[dict], int]:
    """Embed answers per question and flag semantically similar pairs.

    Returns (flags, total_input_tokens).
    """
    flags: list[dict] = []
    total_tokens = 0

    for questao_id, entries in questao_map.items():
        valid = [
            (resp_id, txt)
            for _, resp_id, txt in entries
            if len(txt.strip()) >= _MIN_TEXT_LEN
        ]
        if len(valid) < 2:
            continue

        resp_ids = [v[0] for v in valid]
        texts = [v[1] for v in valid]

        try:
            vecs, tokens = await _embed(texts)
        except Exception as exc:
            logger.warning("Erro ao gerar embeddings para questao %s: %s — pulando", questao_id, exc)
            continue
        total_tokens += tokens

        for (i, vec_a), (j, vec_b) in combinations(enumerate(vecs), 2):
            sim = _cosine(vec_a, vec_b)
            if sim >= SIMILARITY_THRESHOLD:
                logger.info(
                    "Copia detectada questao %s | similaridade %.3f | %s <-> %s",
                    questao_id, sim, resp_ids[i], resp_ids[j],
                )
                comentario = (
                    f"[ATENCAO] Similaridade semantica de {sim:.0%} detectada com outra resposta. "
                    "Possivel copia ou parafrase entre alunos."
                )
                for resp_id in (resp_ids[i], resp_ids[j]):
                    flags.append({"id": resp_id, "comentario_ia": comentario})

    return flags, total_tokens


async def detectar_copias(atividade_id: str, professor_id: str | None = None) -> None:
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

    resp_flags: dict[str, str | None] = {
        resp["id"]: resp.get("flag_tipo")
        for resultado in resultados.data
        for resp in (resultado.get("respostas") or [])
    }

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

    flags_to_update, tokens_used = await _calcular_flags(questao_map)

    if professor_id and tokens_used:
        from app.services.ai_service import registrar_tokens  # lazy — evita import circular
        await registrar_tokens(professor_id, tokens_used, 0)

    if not flags_to_update:
        return

    grupos: dict[str, list[str]] = defaultdict(list)
    for flag in flags_to_update:
        grupos[flag["comentario_ia"]].append(flag["id"])

    for comentario, ids in grupos.items():
        ids_sem_flag = [i for i in ids if not resp_flags.get(i)]
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
