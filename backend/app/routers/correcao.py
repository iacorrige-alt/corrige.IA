import asyncio
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Depends, BackgroundTasks
from app.db.supabase_client import get_supabase
from app.dependencies import get_current_user
from app.limiter import limiter
from app.models.schemas import UploadResponse, StatusResponse, GabaritoUploadResponse
from app.services.storage_service import upload_file
from app.services.ai_service import corrigir_atividade

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/atividades", tags=["correcao"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

# Atividade em "corrigindo" há mais de 15 min é considerada presa.
# BackgroundTask morre silenciosamente se o worker reiniciar.
STUCK_THRESHOLD = timedelta(minutes=15)


@router.post("/{atividade_id}/upload", response_model=UploadResponse)
@limiter.limit("5/minute")
async def upload_provas(
    request: Request,
    atividade_id: str,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()

    # Ownership check
    ativ = await asyncio.to_thread(
        supabase.table("atividades").select("id, turma_id, status")
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

    if ativ.data["status"] == "corrigindo":
        raise HTTPException(
            status_code=409,
            detail="Correção já em andamento. Aguarde a conclusão antes de enviar novos arquivos.",
        )

    # ── Fase 1: validar todos os arquivos antes de qualquer upload ──────────────
    file_contents: list[tuple] = []
    for file in files:
        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de arquivo não suportado: {file.content_type}",
            )
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Arquivo '{file.filename}' excede o limite de 20 MB.",
            )
        file_contents.append((file.filename, file.content_type, content))

    # ── Fase 2: fazer os uploads (todos válidos) ─────────────────────────────
    rows: list[dict] = []
    storage_paths: list[str] = []
    for filename, content_type, content in file_contents:
        tipo = "pdf" if content_type == "application/pdf" else "image"
        storage_path = await upload_file(
            content=content,
            filename=filename,
            content_type=content_type,
            atividade_id=atividade_id,
        )
        storage_paths.append(storage_path)
        rows.append({
            "atividade_id": atividade_id,
            "storage_path": storage_path,
            "tipo_arquivo": tipo,
            "content_type": content_type,
        })

    try:
        records = await asyncio.to_thread(supabase.table("uploads").insert(rows).execute)
    except Exception as exc:
        # DB insert falhou — remove arquivos já enviados ao storage para evitar órfãos
        for path in storage_paths:
            try:
                await asyncio.to_thread(
                    supabase.storage.from_("provas").remove, [path]
                )
            except Exception:
                pass
        raise HTTPException(status_code=500, detail="Erro ao registrar uploads.") from exc

    upload_ids = [r["id"] for r in records.data]

    # Atualiza status para "corrigindo" e registra o timestamp de início.
    # correcao_iniciada_em é usado pelo lazy recovery em GET /status.
    now_utc = datetime.now(timezone.utc).isoformat()
    await asyncio.to_thread(
        supabase.table("atividades")
        .update({"status": "corrigindo", "correcao_iniciada_em": now_utc})
        .eq("id", atividade_id)
        .execute
    )
    background_tasks.add_task(corrigir_atividade, atividade_id)

    return UploadResponse(
        message=f"{len(files)} arquivo(s) enviado(s). Correção iniciada.",
        upload_ids=upload_ids,
        atividade_id=atividade_id,
    )


@router.post("/{atividade_id}/gabarito", response_model=GabaritoUploadResponse)
@limiter.limit("10/minute")
async def upload_gabarito(
    request: Request,
    atividade_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()

    ativ = await asyncio.to_thread(
        supabase.table("atividades").select("id, turma_id, gabarito_pdf_path")
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

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de arquivo não suportado: {file.content_type}",
        )
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Arquivo excede o limite de 20 MB.")

    # Deriva extensão do MIME type (ignorando nome do arquivo para evitar path traversal)
    _mime_to_ext = {
        "application/pdf": "pdf",
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }
    ext = _mime_to_ext.get(file.content_type, "pdf")
    storage_path = f"{atividade_id}/gabarito.{ext}"
    old_path = ativ.data.get("gabarito_pdf_path")

    # Upload novo arquivo primeiro — o arquivo antigo continua íntegro até o DB ser atualizado
    storage_path = await upload_file(
        content=content,
        filename=file.filename or f"gabarito.{ext}",
        content_type=file.content_type,
        atividade_id=atividade_id,
        custom_path=storage_path,
    )

    try:
        await asyncio.to_thread(
            supabase.table("atividades")
            .update({
                "gabarito_pdf_path": storage_path,
                "gabarito_pdf_content_type": file.content_type,
            })
            .eq("id", atividade_id)
            .execute
        )
    except Exception as exc:
        # DB update falhou após o upload — remove o arquivo para evitar órfão
        try:
            await asyncio.to_thread(
                supabase.storage.from_("provas").remove, [storage_path]
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Erro ao registrar gabarito.") from exc

    # Remove arquivo antigo após DB confirmado (best-effort)
    # Se o path é igual (mesma extensão), o upsert já sobrescreveu — não deletar
    if old_path and old_path != storage_path:
        try:
            await asyncio.to_thread(
                supabase.storage.from_("provas").remove, [old_path]
            )
        except Exception as exc:
            logger.warning("Nao foi possivel remover gabarito anterior %s: %s", old_path, exc)

    return GabaritoUploadResponse(
        message="Gabarito enviado com sucesso.",
        atividade_id=atividade_id,
        gabarito_pdf_path=storage_path,
    )


@router.delete("/{atividade_id}/gabarito", status_code=204)
@limiter.limit("10/minute")
async def delete_gabarito(
    request: Request,
    atividade_id: str,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()

    ativ = await asyncio.to_thread(
        supabase.table("atividades").select("id, turma_id, gabarito_pdf_path")
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

    path = ativ.data.get("gabarito_pdf_path")
    if path:
        try:
            await asyncio.to_thread(
                supabase.storage.from_("provas").remove, [path]
            )
        except Exception:
            pass

    await asyncio.to_thread(
        supabase.table("atividades")
        .update({"gabarito_pdf_path": None, "gabarito_pdf_content_type": None})
        .eq("id", atividade_id)
        .execute
    )


@router.get("/{atividade_id}/status", response_model=StatusResponse)
async def status_correcao(
    atividade_id: str,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()

    ativ = await asyncio.to_thread(
        supabase.table("atividades")
        .select("id, status, turma_id, correcao_iniciada_em, uploads_com_erro")
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

    # ── Lazy Recovery ────────────────────────────────────────────────────────────
    # BackgroundTask morre silenciosamente se o container reiniciar (Railway deploy,
    # OOM kill, etc.). Ao invés de um cron externo, aproveitamos o polling que o
    # frontend já faz a cada 5s para detectar e recuperar atividades presas.
    #
    # Optimistic locking: o .eq("status", "corrigindo") garante que apenas um
    # worker atualiza — sem race condition se dois polls chegarem simultaneamente.
    if ativ.data["status"] == "corrigindo":
        iniciada_em_raw = ativ.data.get("correcao_iniciada_em")
        if iniciada_em_raw:
            iniciada_em = datetime.fromisoformat(
                iniciada_em_raw.replace("Z", "+00:00")
            )
            if datetime.now(timezone.utc) - iniciada_em > STUCK_THRESHOLD:
                await asyncio.to_thread(
                    supabase.table("atividades")
                    .update({"status": "erro"})
                    .eq("id", atividade_id)
                    .eq("status", "corrigindo")  # optimistic lock
                    .execute
                )
                # Reflete o novo status na resposta atual sem round-trip extra
                ativ.data["status"] = "erro"

    status_map = {
        "pendente":   (0,   "Aguardando upload de arquivos"),
        "corrigindo": (50,  "Correção em andamento..."),
        "concluida":  (100, "Correção concluída"),
        "erro":       (0,   "Correção falhou. Verifique os arquivos e tente novamente."),
    }
    st = ativ.data["status"]
    progresso, mensagem = status_map.get(st, (0, "Status desconhecido"))

    return StatusResponse(
        atividade_id=atividade_id,
        status=st,
        progresso=progresso,
        mensagem=mensagem,
        uploads_com_erro=ativ.data.get("uploads_com_erro", 0),
    )
