import asyncio
from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import AlunoCreate, AlunoOut, DashboardAluno
from app.db.supabase_client import get_supabase
from app.dependencies import get_current_user

router = APIRouter(tags=["alunos"])


@router.get("/turmas/{turma_id}/alunos", response_model=list[AlunoOut])
async def listar_alunos(turma_id: str, current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    turma = await asyncio.to_thread(
        supabase.table("turmas").select("id")
        .eq("id", turma_id).eq("professor_id", current_user["id"]).single().execute
    )
    if not turma.data:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")

    result = await asyncio.to_thread(
        supabase.table("alunos").select("*").eq("turma_id", turma_id).order("nome").execute
    )
    return result.data


@router.post("/turmas/{turma_id}/alunos", response_model=AlunoOut, status_code=201)
async def criar_aluno(
    turma_id: str,
    body: AlunoCreate,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    turma = await asyncio.to_thread(
        supabase.table("turmas").select("id")
        .eq("id", turma_id).eq("professor_id", current_user["id"]).single().execute
    )
    if not turma.data:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")

    parts = body.nome.strip().split()
    if len(parts) >= 2:
        initials = (parts[0][0] + parts[-1][0]).upper()
    else:
        initials = parts[0][:2].upper()

    result = await asyncio.to_thread(
        supabase.table("alunos")
        .insert({"turma_id": turma_id, "nome": body.nome, "initials": initials})
        .execute
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Erro ao criar aluno.")
    return result.data[0]


@router.delete("/alunos/{aluno_id}", status_code=204)
async def deletar_aluno(aluno_id: str, current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    aluno = await asyncio.to_thread(
        supabase.table("alunos").select("id, turma_id").eq("id", aluno_id).single().execute
    )
    if not aluno.data:
        raise HTTPException(status_code=404, detail="Aluno não encontrado.")

    turma = await asyncio.to_thread(
        supabase.table("turmas").select("id")
        .eq("id", aluno.data["turma_id"]).eq("professor_id", current_user["id"]).single().execute
    )
    if not turma.data:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    await asyncio.to_thread(
        supabase.table("alunos").delete().eq("id", aluno_id).execute
    )


@router.get("/alunos/{aluno_id}/dashboard", response_model=DashboardAluno)
async def dashboard_aluno(aluno_id: str, current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()

    aluno = await asyncio.to_thread(
        supabase.table("alunos")
        .select("*, turmas(professor_id, disciplina)")
        .eq("id", aluno_id).single().execute
    )
    if not aluno.data:
        raise HTTPException(status_code=404, detail="Aluno não encontrado.")
    turma_rel = aluno.data.get("turmas") or {}
    if turma_rel.get("professor_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    resultados = await asyncio.to_thread(
        supabase.table("resultados")
        .select("*, atividades(nome, data_criacao, turmas(disciplina)), respostas(flag_tipo)")
        .eq("aluno_id", aluno_id).order("criado_em").execute
    )

    evolucao = []
    flags_detectadas = set()
    notas = []
    radar: dict[str, list[float]] = {}

    for r in resultados.data:
        if r["nota_total"] is not None:
            notas.append(r["nota_total"])
            atividade = r.get("atividades", {})
            evolucao.append({
                "atividade": atividade.get("nome", ""),
                "nota": r["nota_total"],
                "data": str(atividade.get("data_criacao", ""))[:10],
            })
            disciplina = (atividade.get("turmas") or {}).get("disciplina", "Geral")
            radar.setdefault(disciplina, []).append(r["nota_total"])
        for resp in (r.get("respostas") or []):
            if resp.get("flag_tipo"):
                flags_detectadas.add(resp["flag_tipo"])

    media_geral = round(sum(notas) / len(notas), 2) if notas else 0.0
    radar_out = [
        {"disciplina": d, "nota": round(sum(ns) / len(ns), 2)}
        for d, ns in radar.items()
    ]

    # Análise baseada em regras (sem chamada a LLM)
    if media_geral >= 8:
        analise = f"{aluno.data['nome']} demonstra excelente desempenho, com média {media_geral}. Continue incentivando!"
    elif media_geral >= 6:
        analise = f"{aluno.data['nome']} está com desempenho satisfatório (média {media_geral}). Há espaço para crescimento."
    else:
        analise = f"{aluno.data['nome']} precisa de atenção. Média atual {media_geral}. Recomenda-se intervenção pedagógica."

    return {
        "aluno": {
            "id": aluno.data["id"],
            "turma_id": aluno.data["turma_id"],
            "nome": aluno.data["nome"],
            "initials": aluno.data["initials"],
            "criado_em": aluno.data["criado_em"],
        },
        "media_geral": media_geral,
        "total_atividades": len(evolucao),
        "evolucao": evolucao,
        "radar": radar_out,
        "analise_ia": analise,
        "flags_detectadas": list(flags_detectadas),
    }
