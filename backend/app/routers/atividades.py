import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from app.models.schemas import AtividadeCreate, AtividadeOut, AtividadeUpdate, ResultadoOut
from app.db.supabase_client import get_supabase
from app.dependencies import get_current_user
from app.limiter import limiter
from app.quota import checar_limite_tokens
from app.utils import ler_arquivo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/atividades", tags=["atividades"])


@router.get("", response_model=list[AtividadeOut])
async def listar_atividades(current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    result = await asyncio.to_thread(
        supabase.table("atividades")
        .select("*, questoes(count)")
        .eq("professor_id", current_user["id"])
        .order("data_criacao", desc=True)
        .execute
    )
    for a in result.data:
        count_data = a.get("questoes") or [{}]
        a["questoes"] = None
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


@router.patch("/{atividade_id}", response_model=AtividadeOut)
async def atualizar_atividade(
    atividade_id: str,
    body: AtividadeUpdate,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar.")

    result = await asyncio.to_thread(
        supabase.table("atividades")
        .update(updates)
        .eq("id", atividade_id)
        .eq("professor_id", current_user["id"])
        .execute
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")

    full = await asyncio.to_thread(
        supabase.table("atividades").select("*, questoes(*)").eq("id", atividade_id).single().execute
    )
    return full.data


@router.delete("/{atividade_id}", status_code=204)
async def deletar_atividade(
    atividade_id: str,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    ativ = await asyncio.to_thread(
        supabase.table("atividades")
        .select("id, gabarito_pdf_path, uploads(storage_path)")
        .eq("id", atividade_id)
        .eq("professor_id", current_user["id"])
        .single()
        .execute
    )
    if not ativ.data:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")

    # Coleta paths do storage antes de deletar do DB
    storage_paths = [u["storage_path"] for u in (ativ.data.get("uploads") or [])]
    if ativ.data.get("gabarito_pdf_path"):
        storage_paths.append(ativ.data["gabarito_pdf_path"])

    # Deleta do DB — FK CASCADE remove questoes, uploads, resultados, respostas
    await asyncio.to_thread(
        supabase.table("atividades").delete().eq("id", atividade_id).execute
    )

    # Remove arquivos do storage (best-effort)
    if storage_paths:
        try:
            await asyncio.to_thread(
                supabase.storage.from_("provas").remove, storage_paths
            )
        except Exception as exc:
            logger.warning("Nao foi possivel remover arquivos da atividade %s: %s", atividade_id, exc)


@router.post("/extrair-questoes-pdf")
@limiter.limit("3/minute")
async def extrair_questoes_do_pdf(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    from app.services.ai_service import extrair_questoes_pdf

    supabase = get_supabase()
    await checar_limite_tokens(current_user["id"], supabase)

    ALLOWED = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
    if file.content_type not in ALLOWED:
        raise HTTPException(400, f"Tipo não suportado: {file.content_type}")
    content = await ler_arquivo(file, 20 * 1024 * 1024)
    questoes = await extrair_questoes_pdf(content, file.content_type, professor_id=current_user["id"])
    return {"questoes": questoes}


@router.get("/{atividade_id}", response_model=AtividadeOut)
async def get_atividade(
    atividade_id: str,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    ativ = await asyncio.to_thread(
        supabase.table("atividades").select("*, questoes(*)")
        .eq("id", atividade_id)
        .eq("professor_id", current_user["id"])
        .single().execute
    )
    if not ativ.data:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")
    return ativ.data


@router.get("/{atividade_id}/resultados", response_model=list[ResultadoOut])
async def resultados_atividade(
    atividade_id: str,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    ativ = await asyncio.to_thread(
        supabase.table("atividades").select("id")
        .eq("id", atividade_id)
        .eq("professor_id", current_user["id"])
        .single().execute
    )
    if not ativ.data:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")

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
