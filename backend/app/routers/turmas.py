import asyncio
from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import (
    TurmaCreate, TurmaOut, TurmaUpdate,
    DashboardTurma, DistribuicaoNota, EvolucaoTurma, RankingAluno, AnaliseIATurma,
)
from app.db.supabase_client import get_supabase
from app.dependencies import get_current_user
from app.services.ai_service import analisar_turma

router = APIRouter(prefix="/turmas", tags=["turmas"])


def _extract_counts(t: dict) -> dict:
    t["total_alunos"] = t.pop("alunos", [{}])[0].get("count", 0) if t.get("alunos") else 0
    t["total_atividades"] = t.pop("atividades", [{}])[0].get("count", 0) if t.get("atividades") else 0
    return t


@router.get("", response_model=list[TurmaOut])
async def listar_turmas(current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    result = await asyncio.to_thread(
        supabase.table("turmas")
        .select("*, alunos(count), atividades(count)")
        .eq("professor_id", current_user["id"])
        .order("criado_em", desc=True)
        .execute
    )
    return [_extract_counts(t) for t in result.data]


@router.post("", response_model=TurmaOut, status_code=201)
async def criar_turma(body: TurmaCreate, current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    data = body.model_dump()
    data["professor_id"] = current_user["id"]
    result = await asyncio.to_thread(supabase.table("turmas").insert(data).execute)
    if not result.data:
        raise HTTPException(status_code=500, detail="Erro ao criar turma.")
    row = result.data[0]
    row["total_alunos"] = 0
    row["total_atividades"] = 0
    return row


@router.get("/{turma_id}", response_model=TurmaOut)
async def detalhe_turma(turma_id: str, current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    result = await asyncio.to_thread(
        supabase.table("turmas")
        .select("*, alunos(count), atividades(count)")
        .eq("id", turma_id)
        .eq("professor_id", current_user["id"])
        .single()
        .execute
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")
    return _extract_counts(result.data)


@router.get("/{turma_id}/dashboard", response_model=DashboardTurma)
async def dashboard_turma(turma_id: str, current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()

    turma_resp = await asyncio.to_thread(
        supabase.table("turmas")
        .select("id, nome, disciplina")
        .eq("id", turma_id)
        .eq("professor_id", current_user["id"])
        .single()
        .execute
    )
    if not turma_resp.data:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")
    turma = turma_resp.data

    _empty = DashboardTurma(
        turma_id=turma_id,
        turma_nome=turma["nome"],
        disciplina=turma["disciplina"],
        media_geral=0.0,
        taxa_aprovacao=0.0,
        total_alunos_avaliados=0,
        total_atividades=0,
        total_flags=0,
        distribuicao=[],
        evolucao=[],
        ranking=[],
        analise_ia=AnaliseIATurma(
            resumo="Nenhuma atividade concluída ainda.",
            pontos_de_atencao=[],
            sugestoes_pedagogicas=[],
            sugestoes_metodologicas=[],
        ),
    )

    ativs_resp = await asyncio.to_thread(
        supabase.table("atividades")
        .select("id, nome, data_criacao")
        .eq("turma_id", turma_id)
        .eq("status", "concluida")
        .order("data_criacao")
        .execute
    )
    atividades = ativs_resp.data
    if not atividades:
        return _empty

    ativ_ids = [a["id"] for a in atividades]
    resultados_resp = await asyncio.to_thread(
        supabase.table("resultados")
        .select("id, atividade_id, aluno_id, nota_total, alunos(nome, initials), respostas(flag_tipo)")
        .in_("atividade_id", ativ_ids)
        .execute
    )
    resultados = resultados_resp.data
    if not resultados:
        return _empty

    # ── Métricas agregadas ────────────────────────────────────────────────────
    notas = [r["nota_total"] for r in resultados if r["nota_total"] is not None]
    media_geral = round(sum(notas) / len(notas), 2) if notas else 0.0
    taxa_aprovacao = round(sum(1 for n in notas if n >= 6.0) / len(notas), 3) if notas else 0.0

    buckets: dict[str, int] = {"0–2": 0, "2–4": 0, "4–6": 0, "6–8": 0, "8–10": 0}
    for n in notas:
        if n < 2:   buckets["0–2"] += 1
        elif n < 4: buckets["2–4"] += 1
        elif n < 6: buckets["4–6"] += 1
        elif n < 8: buckets["6–8"] += 1
        else:       buckets["8–10"] += 1
    distribuicao = [DistribuicaoNota(faixa=k, count=v) for k, v in buckets.items()]

    # ── Evolução por atividade ────────────────────────────────────────────────
    ativ_map = {a["id"]: a for a in atividades}
    ativ_notas: dict[str, list[float]] = {}
    for r in resultados:
        if r["nota_total"] is not None:
            ativ_notas.setdefault(r["atividade_id"], []).append(r["nota_total"])

    evolucao = sorted(
        [
            EvolucaoTurma(
                atividade=ativ_map[aid]["nome"],
                data=str(ativ_map[aid]["data_criacao"])[:10],
                media=round(sum(ns) / len(ns), 2),
                total_alunos=len(ns),
            )
            for aid, ns in ativ_notas.items() if aid in ativ_map
        ],
        key=lambda x: x.data,
    )

    # ── Ranking por aluno ─────────────────────────────────────────────────────
    aluno_acc: dict[str, dict] = {}
    for r in resultados:
        aid = r["aluno_id"]
        aluno = r.get("alunos") or {}
        if aid not in aluno_acc:
            aluno_acc[aid] = {
                "aluno_id": aid,
                "nome": aluno.get("nome", ""),
                "initials": aluno.get("initials", ""),
                "notas": [],
                "flags": set(),
            }
        if r["nota_total"] is not None:
            aluno_acc[aid]["notas"].append(r["nota_total"])
        for resp in (r.get("respostas") or []):
            if resp.get("flag_tipo"):
                aluno_acc[aid]["flags"].add(resp["flag_tipo"])

    ranking = sorted(
        [
            RankingAluno(
                aluno_id=d["aluno_id"],
                nome=d["nome"],
                initials=d["initials"],
                media=round(sum(d["notas"]) / len(d["notas"]), 2) if d["notas"] else 0.0,
                total_atividades=len(d["notas"]),
                flags=list(d["flags"]),
            )
            for d in aluno_acc.values()
        ],
        key=lambda x: x.media,
        reverse=True,
    )

    total_flags = sum(
        1
        for r in resultados
        for resp in (r.get("respostas") or [])
        if resp.get("flag_tipo")
    )
    total_alunos_avaliados = len(aluno_acc)

    # ── Análise IA ────────────────────────────────────────────────────────────
    analise_raw = await analisar_turma(
        turma["nome"],
        turma["disciplina"],
        {
            "media_geral": media_geral,
            "taxa_aprovacao": taxa_aprovacao,
            "total_alunos_avaliados": total_alunos_avaliados,
            "total_atividades": len(atividades),
            "total_flags": total_flags,
            "distribuicao": [{"faixa": d.faixa, "count": d.count} for d in distribuicao],
        },
        professor_id=current_user["id"],
    )
    analise_ia = AnaliseIATurma(
        resumo=analise_raw.get("resumo", ""),
        pontos_de_atencao=analise_raw.get("pontos_de_atencao", []),
        sugestoes_pedagogicas=analise_raw.get("sugestoes_pedagogicas", []),
        sugestoes_metodologicas=analise_raw.get("sugestoes_metodologicas", []),
    )

    return DashboardTurma(
        turma_id=turma_id,
        turma_nome=turma["nome"],
        disciplina=turma["disciplina"],
        media_geral=media_geral,
        taxa_aprovacao=taxa_aprovacao,
        total_alunos_avaliados=total_alunos_avaliados,
        total_atividades=len(atividades),
        total_flags=total_flags,
        distribuicao=distribuicao,
        evolucao=evolucao,
        ranking=ranking,
        analise_ia=analise_ia,
    )


@router.patch("/{turma_id}", response_model=TurmaOut)
async def atualizar_turma(
    turma_id: str,
    body: TurmaUpdate,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar.")

    result = await asyncio.to_thread(
        supabase.table("turmas")
        .update(updates)
        .eq("id", turma_id)
        .eq("professor_id", current_user["id"])
        .execute
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")

    row = result.data[0]
    counts = await asyncio.to_thread(
        supabase.table("turmas")
        .select("alunos(count), atividades(count)")
        .eq("id", turma_id)
        .single()
        .execute
    )
    row["total_alunos"] = (counts.data.get("alunos") or [{}])[0].get("count", 0)
    row["total_atividades"] = (counts.data.get("atividades") or [{}])[0].get("count", 0)
    return row


@router.delete("/{turma_id}", status_code=204)
async def deletar_turma(turma_id: str, current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    result = await asyncio.to_thread(
        supabase.table("turmas")
        .delete()
        .eq("id", turma_id)
        .eq("professor_id", current_user["id"])
        .execute
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")
