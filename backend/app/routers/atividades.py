import asyncio
import csv
import io
import logging
import re
import unicodedata
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Request
from fastapi import Response
from fastapi.responses import StreamingResponse

from app.models.schemas import (
    AtividadeCreate, AtividadeOut, AtividadeUpdate,
    QuestaoCreate, QuestaoOut, QuestaoUpdate,
    ResultadoOut, UploadOut, RespostaUpdate, UploadAlunoUpdate,
)
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
        .limit(200)
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
@limiter.limit("20/minute")
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


@router.get("/{atividade_id}/resultados/export")
async def exportar_resultados_csv(
    atividade_id: str,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    ativ = await asyncio.to_thread(
        supabase.table("atividades").select("id, nome, questoes(*)")
        .eq("id", atividade_id).eq("professor_id", current_user["id"]).single().execute
    )
    if not ativ.data:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")

    questoes = sorted(ativ.data.get("questoes") or [], key=lambda q: q["ordem"])

    resultados = await asyncio.to_thread(
        supabase.table("resultados")
        .select("nota_total, alunos(nome), respostas(questao_id, nota)")
        .eq("atividade_id", atividade_id)
        .execute
    )

    output = io.StringIO()
    writer = csv.writer(output)

    header = ["Aluno", "Nota Total"] + [f"Q{i+1} - {q['enunciado'][:40]}" for i, q in enumerate(questoes)]
    writer.writerow(header)

    for r in sorted(resultados.data, key=lambda x: (x.get("alunos") or {}).get("nome", "")):
        aluno_nome = (r.get("alunos") or {}).get("nome", "Desconhecido")
        nota_total = r.get("nota_total", "")
        respostas_map = {resp["questao_id"]: resp.get("nota", "") for resp in (r.get("respostas") or [])}
        notas_questoes = [respostas_map.get(q["id"], "") for q in questoes]
        writer.writerow([aluno_nome, nota_total] + notas_questoes)

    # utf-8-sig = UTF-8 com BOM — garante abertura correta no Excel
    csv_bytes = output.getvalue().encode("utf-8-sig")
    # Filename do header HTTP deve ser ASCII puro (latin-1 não suporta —, ê, etc.)
    nome_ascii = unicodedata.normalize("NFKD", ativ.data["nome"]).encode("ascii", "ignore").decode("ascii")
    nome_arquivo = re.sub(r"[^a-zA-Z0-9_\-]", "_", nome_ascii)[:50].strip("_")
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="resultados_{nome_arquivo}.csv"'},
    )


@router.post("/{atividade_id}/reprocessar", status_code=202)
async def reprocessar_atividade(
    atividade_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    from app.services.ai_service import corrigir_atividade

    supabase = get_supabase()
    ativ = await asyncio.to_thread(
        supabase.table("atividades").select("id, status")
        .eq("id", atividade_id).eq("professor_id", current_user["id"]).single().execute
    )
    if not ativ.data:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")
    if ativ.data["status"] == "corrigindo":
        raise HTTPException(status_code=409, detail="Correção já em andamento.")
    if ativ.data["status"] != "erro":
        raise HTTPException(status_code=409, detail="Reprocessamento só é permitido quando a correção está com erro.")

    uploads = await asyncio.to_thread(
        supabase.table("uploads").select("id").eq("atividade_id", atividade_id).execute
    )
    if not uploads.data:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado para reprocessar.")

    # Atualiza status ANTES de deletar resultados — se o update falhar, dados ficam íntegros.
    now_utc = datetime.now(timezone.utc).isoformat()
    await asyncio.to_thread(
        supabase.table("atividades")
        .update({"status": "corrigindo", "correcao_iniciada_em": now_utc, "uploads_com_erro": 0})
        .eq("id", atividade_id).execute
    )
    await asyncio.to_thread(
        supabase.table("resultados").delete().eq("atividade_id", atividade_id).execute
    )
    background_tasks.add_task(corrigir_atividade, atividade_id, current_user["id"])
    return {"message": "Reprocessamento iniciado.", "atividade_id": atividade_id}


@router.post("/{atividade_id}/questoes", response_model=QuestaoOut, status_code=201)
async def adicionar_questao(
    atividade_id: str,
    body: QuestaoCreate,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    ativ = await asyncio.to_thread(
        supabase.table("atividades").select("id, status")
        .eq("id", atividade_id).eq("professor_id", current_user["id"]).single().execute
    )
    if not ativ.data:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")
    if ativ.data["status"] in ("corrigindo", "concluida", "erro"):
        raise HTTPException(status_code=409, detail="Não é possível alterar questões de uma atividade já concluída, em correção ou com erro.")

    result = await asyncio.to_thread(
        supabase.table("questoes").insert({
            "atividade_id": atividade_id,
            "enunciado": body.enunciado,
            "gabarito": body.gabarito,
            "tipo": body.tipo,
            "peso": body.peso,
            "ordem": body.ordem,
        }).execute
    )
    return result.data[0]


@router.patch("/{atividade_id}/questoes/{questao_id}", response_model=QuestaoOut)
async def atualizar_questao(
    atividade_id: str,
    questao_id: str,
    body: QuestaoUpdate,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    ativ = await asyncio.to_thread(
        supabase.table("atividades").select("id")
        .eq("id", atividade_id).eq("professor_id", current_user["id"]).single().execute
    )
    if not ativ.data:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar.")

    result = await asyncio.to_thread(
        supabase.table("questoes").update(updates)
        .eq("id", questao_id).eq("atividade_id", atividade_id).execute
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Questão não encontrada.")
    return result.data[0]


@router.delete("/{atividade_id}/questoes/{questao_id}", status_code=204)
async def deletar_questao(
    atividade_id: str,
    questao_id: str,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    ativ = await asyncio.to_thread(
        supabase.table("atividades").select("id")
        .eq("id", atividade_id).eq("professor_id", current_user["id"]).single().execute
    )
    if not ativ.data:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")

    result = await asyncio.to_thread(
        supabase.table("questoes").delete()
        .eq("id", questao_id).eq("atividade_id", atividade_id).execute
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Questão não encontrada.")


@router.get("/{atividade_id}/uploads", response_model=list[UploadOut])
async def listar_uploads(
    atividade_id: str,
    current_user: dict = Depends(get_current_user),
):
    from app.services.storage_service import create_signed_url

    supabase = get_supabase()
    ativ = await asyncio.to_thread(
        supabase.table("atividades").select("id")
        .eq("id", atividade_id).eq("professor_id", current_user["id"]).single().execute
    )
    if not ativ.data:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")

    uploads = await asyncio.to_thread(
        supabase.table("uploads")
        .select("*, alunos(nome)")
        .eq("atividade_id", atividade_id)
        .execute
    )

    async def _sign_upload(u: dict) -> dict:
        aluno = u.pop("alunos", None) or {}
        try:
            signed_url = await create_signed_url(u["storage_path"])
        except Exception:
            signed_url = None
        return {**u, "aluno_nome": aluno.get("nome"), "signed_url": signed_url}

    return list(await asyncio.gather(*[_sign_upload(u) for u in uploads.data]))


@router.get("/{atividade_id}/resultados", response_model=list[ResultadoOut])
async def resultados_atividade(
    atividade_id: str,
    current_user: dict = Depends(get_current_user),
):
    from app.services.storage_service import create_signed_url

    supabase = get_supabase()
    ativ = await asyncio.to_thread(
        supabase.table("atividades").select("id")
        .eq("id", atividade_id)
        .eq("professor_id", current_user["id"])
        .single().execute
    )
    if not ativ.data:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")

    resultados, uploads_resp = await asyncio.gather(
        asyncio.to_thread(
            supabase.table("resultados")
            .select("*, alunos(nome, initials), respostas(*)")
            .eq("atividade_id", atividade_id)
            .execute
        ),
        asyncio.to_thread(
            supabase.table("uploads")
            .select("id, aluno_id, storage_path, tipo_arquivo")
            .eq("atividade_id", atividade_id)
            .execute
        ),
    )

    # Generate signed URLs for all uploads in parallel
    raw_uploads = uploads_resp.data or []
    async def _sign(u):
        try:
            url = await create_signed_url(u["storage_path"])
        except Exception:
            url = None
        return {**u, "signed_url": url}

    signed = await asyncio.gather(*[_sign(u) for u in raw_uploads])

    uploads_by_aluno: dict[str, list] = {}
    for u in signed:
        uploads_by_aluno.setdefault(u["aluno_id"], []).append(u)

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
            "provas": uploads_by_aluno.get(r["aluno_id"], []),
        })
    return out


@router.patch("/{atividade_id}/respostas/{resposta_id}")
async def editar_resposta(
    atividade_id: str,
    resposta_id: str,
    body: RespostaUpdate,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()

    ativ = await asyncio.to_thread(
        supabase.table("atividades").select("id")
        .eq("id", atividade_id).eq("professor_id", current_user["id"]).single().execute
    )
    if not ativ.data:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")

    # Fix: join via resultados para garantir que a resposta pertence a esta atividade (IDOR)
    resposta_resp = await asyncio.to_thread(
        supabase.table("respostas")
        .select("id, resultado_id, questao_id, questoes(peso), resultados(atividade_id)")
        .eq("id", resposta_id).single().execute
    )
    if not resposta_resp.data:
        raise HTTPException(status_code=404, detail="Resposta não encontrada.")
    if (resposta_resp.data.get("resultados") or {}).get("atividade_id") != atividade_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    resposta = resposta_resp.data
    peso = float((resposta.get("questoes") or {}).get("peso") or 1)
    nova_nota = round(max(0.0, min(body.nota, peso)), 2)

    if nova_nota >= peso:
        novo_status = "correto"
    elif nova_nota <= 0:
        novo_status = "errado"
    else:
        novo_status = "parcial"

    resultado_id = resposta["resultado_id"]

    await asyncio.to_thread(
        supabase.table("respostas")
        .update({"nota": nova_nota, "status": novo_status})
        .eq("id", resposta_id).execute
    )

    # Trigger _recalcular_nota_total já atualizou nota_total; basta ler de volta.
    resultado_resp = await asyncio.to_thread(
        supabase.table("resultados").select("nota_total").eq("id", resultado_id).single().execute
    )
    nota_total = round((resultado_resp.data or {}).get("nota_total") or 0, 2)

    return {"nota": nova_nota, "status": novo_status, "nota_total": nota_total}


@router.patch("/{atividade_id}/uploads/{upload_id}")
async def atualizar_upload_aluno(
    atividade_id: str,
    upload_id: str,
    body: UploadAlunoUpdate,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()

    ativ = await asyncio.to_thread(
        supabase.table("atividades").select("id, status")
        .eq("id", atividade_id).eq("professor_id", current_user["id"]).single().execute
    )
    if not ativ.data:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")
    if ativ.data["status"] == "corrigindo":
        raise HTTPException(status_code=409, detail="Não é possível alterar uploads durante a correção.")

    upload_resp = await asyncio.to_thread(
        supabase.table("uploads").select("id, aluno_id")
        .eq("id", upload_id).eq("atividade_id", atividade_id).single().execute
    )
    if not upload_resp.data:
        raise HTTPException(status_code=404, detail="Upload não encontrado.")

    old_aluno_id = upload_resp.data.get("aluno_id")
    new_aluno_id = body.aluno_id

    # Verificar conflito ANTES de atualizar o upload para manter estado consistente.
    if old_aluno_id and old_aluno_id != new_aluno_id and new_aluno_id:
        conflito = await asyncio.to_thread(
            supabase.table("resultados").select("id")
            .eq("atividade_id", atividade_id).eq("aluno_id", new_aluno_id).execute
        )
        if conflito.data:
            raise HTTPException(
                status_code=409,
                detail="O aluno selecionado já possui resultado para esta atividade.",
            )

    await asyncio.to_thread(
        supabase.table("uploads").update({"aluno_id": new_aluno_id}).eq("id", upload_id).execute
    )

    # Move o resultado do aluno anterior para o novo (caso de erro de identificação pela IA).
    # O UNIQUE(atividade_id, aluno_id) em resultados captura race conditions concorrentes.
    if old_aluno_id and old_aluno_id != new_aluno_id and new_aluno_id:
        try:
            await asyncio.to_thread(
                supabase.table("resultados")
                .update({"aluno_id": new_aluno_id})
                .eq("atividade_id", atividade_id)
                .eq("aluno_id", old_aluno_id)
                .execute
            )
        except Exception as exc:
            err = str(exc).lower()
            if "23505" in err or "unique" in err or "duplicate" in err:
                raise HTTPException(
                    status_code=409,
                    detail="O aluno selecionado já possui resultado para esta atividade.",
                )
            raise

    return {"upload_id": upload_id, "aluno_id": new_aluno_id}


@router.post("/{atividade_id}/uploads/{upload_id}/corrigir", status_code=202)
async def corrigir_upload_individual(
    atividade_id: str,
    upload_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    from app.services.ai_service import corrigir_upload as _corrigir_upload

    supabase = get_supabase()

    ativ = await asyncio.to_thread(
        supabase.table("atividades").select("id")
        .eq("id", atividade_id).eq("professor_id", current_user["id"]).single().execute
    )
    if not ativ.data:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")

    upload_resp = await asyncio.to_thread(
        supabase.table("uploads").select("id, aluno_id")
        .eq("id", upload_id).eq("atividade_id", atividade_id).single().execute
    )
    if not upload_resp.data:
        raise HTTPException(status_code=404, detail="Upload não encontrado.")
    if not upload_resp.data.get("aluno_id"):
        raise HTTPException(status_code=400, detail="Associe um aluno ao arquivo antes de corrigir.")

    background_tasks.add_task(_corrigir_upload, upload_id, atividade_id, current_user["id"])
    return {"message": "Correção iniciada.", "upload_id": upload_id}


@router.delete("/{atividade_id}/uploads/{upload_id}", status_code=204)
async def deletar_upload(
    atividade_id: str,
    upload_id: str,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()

    ativ = await asyncio.to_thread(
        supabase.table("atividades").select("id, status")
        .eq("id", atividade_id).eq("professor_id", current_user["id"]).single().execute
    )
    if not ativ.data:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")
    if ativ.data["status"] == "corrigindo":
        raise HTTPException(status_code=409, detail="Não é possível remover arquivos durante a correção.")

    upload_resp = await asyncio.to_thread(
        supabase.table("uploads").select("id, storage_path")
        .eq("id", upload_id).eq("atividade_id", atividade_id).single().execute
    )
    if not upload_resp.data:
        raise HTTPException(status_code=404, detail="Upload não encontrado.")

    storage_path = upload_resp.data["storage_path"]

    await asyncio.to_thread(
        supabase.table("uploads").delete().eq("id", upload_id).execute
    )

    try:
        await asyncio.to_thread(supabase.storage.from_("provas").remove, [storage_path])
    except Exception as exc:
        logger.warning("Nao foi possivel remover upload %s do storage: %s", upload_id, exc)
