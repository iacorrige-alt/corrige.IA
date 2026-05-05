import asyncio
from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import AtividadeCreate, AtividadeOut, ResultadoOut
from app.db.supabase_client import get_supabase
from app.dependencies import get_current_user

router = APIRouter(prefix="/atividades", tags=["atividades"])


@router.get("", response_model=list[AtividadeOut])
async def listar_atividades(current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    turmas = await asyncio.to_thread(
        supabase.table("turmas").select("id").eq("professor_id", current_user["id"]).execute
    )
    turma_ids = [t["id"] for t in turmas.data]
    if not turma_ids:
        return []

    result = await asyncio.to_thread(
        supabase.table("atividades")
        .select("*, questoes(count)")
        .in_("turma_id", turma_ids)
        .order("data_criacao", desc=True)
        .execute
    )
    # Normalize count response: [{"count": N}] → int on each row
    for a in result.data:
        count_data = a.get("questoes") or [{}]
        a["questoes"] = None  # list view doesn't need questao content
        a["total_questoes"] = count_data[0].get("count", 0) if count_data else 0
    return result.data


@router.post("", response_model=AtividadeOut, status_code=201)
async def criar_atividade(
    body: AtividadeCreate,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    turma = await asyncio.to_thread(
        supabase.table("turmas").select("id")
        .eq("id", body.turma_id).eq("professor_id", current_user["id"]).single().execute
    )
    if not turma.data:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")

    ativ_data = {
        "turma_id": body.turma_id,
        "nome": body.nome,
        "tipo": body.tipo,
        "modo_correcao": body.modo_correcao,
        "gabarito_texto": body.gabarito_texto,
        "status": "pendente",
    }
    ativ = await asyncio.to_thread(supabase.table("atividades").insert(ativ_data).execute)
    if not ativ.data:
        raise HTTPException(status_code=500, detail="Erro ao criar atividade.")
    ativ_id = ativ.data[0]["id"]

    questoes_data = [
        {
            "atividade_id": ativ_id,
            "enunciado": q.enunciado,
            "gabarito": q.gabarito,
            "tipo": q.tipo,
            "peso": q.peso,
            "ordem": q.ordem,
        }
        for q in body.questoes
    ]
    if questoes_data:
        await asyncio.to_thread(supabase.table("questoes").insert(questoes_data).execute)

    full = await asyncio.to_thread(
        supabase.table("atividades").select("*, questoes(*)").eq("id", ativ_id).single().execute
    )
    return full.data


@router.get("/{atividade_id}", response_model=AtividadeOut)
async def get_atividade(
    atividade_id: str,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    ativ = await asyncio.to_thread(
        supabase.table("atividades").select("*, questoes(*)")
        .eq("id", atividade_id).single().execute
    )
    if not ativ.data:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")

    turma = await asyncio.to_thread(
        supabase.table("turmas").select("id")
        .eq("id", ativ.data["turma_id"]).eq("professor_id", current_user["id"]).single().execute
    )
    if not turma.data:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    return ativ.data


@router.get("/{atividade_id}/resultados", response_model=list[ResultadoOut])
async def resultados_atividade(
    atividade_id: str,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    ativ = await asyncio.to_thread(
        supabase.table("atividades").select("id, turma_id").eq("id", atividade_id).single().execute
    )
    if not ativ.data:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")

    turma = await asyncio.to_thread(
        supabase.table("turmas").select("id")
        .eq("id", ativ.data["turma_id"]).eq("professor_id", current_user["id"]).single().execute
    )
    if not turma.data:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    resultados = await asyncio.to_thread(
        supabase.table("resultados")
        .select("*, alunos(nome, initials), respostas(*)")
        .eq("atividade_id", atividade_id)
        .execute
    )

    out = []
    for r in resultados.data:
        aluno = r.pop("alunos", {}) or {}
        respostas = r.pop("respostas", []) or []
        flags = list({resp["flag_tipo"] for resp in respostas if resp.get("flag_tipo")})
        out.append({
            **r,
            "aluno_nome": aluno.get("nome"),
            "aluno_initials": aluno.get("initials"),
            "respostas": respostas,
            "flags": flags,
        })
    return out
