import asyncio
import logging
import random
import uuid

import httpx

from app.config import settings

logger = logging.getLogger(__name__)
BUCKET = "provas"

# Supabase Storage REST API — usado diretamente porque supabase-py 2.x
# não envia o header Authorization corretamente em chamadas de storage,
# causando violação de RLS mesmo com service_role key.
def _storage_url(path: str) -> str:
    return f"{settings.supabase_url}/storage/v1/object/{BUCKET}/{path}"

def _headers(content_type: str | None = None, upsert: bool = False) -> dict:
    h = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }
    if content_type:
        h["Content-Type"] = content_type
    if upsert:
        h["x-upsert"] = "true"
    return h


async def _storage_retry(fn, *, label: str, max_attempts: int = 3):
    for attempt in range(max_attempts):
        try:
            return await fn()
        except FileNotFoundError:
            raise  # 404 não é transitório — não retentar
        except Exception as exc:
            if attempt == max_attempts - 1:
                raise
            delay = random.uniform(0, 2 ** attempt)
            logger.warning(
                "Storage %s falhou (tentativa %d/%d) — retry em %.1fs: %s",
                label, attempt + 1, max_attempts, delay, exc,
                extra={"attempt": attempt + 1, "label": label},
            )
            await asyncio.sleep(delay)


async def upload_file(
    content: bytes,
    filename: str,
    content_type: str,
    atividade_id: str,
    custom_path: str | None = None,
) -> str:
    if custom_path:
        storage_path = custom_path
    else:
        raw_ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
        ext = raw_ext.strip(".") or "bin"
        storage_path = f"{atividade_id}/{uuid.uuid4()}.{ext}"

    upsert = bool(custom_path)

    async def _do_upload():
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                _storage_url(storage_path),
                content=content,
                headers=_headers(content_type=content_type, upsert=upsert),
            )
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"Storage upload falhou: {resp.status_code} {resp.text}")
        return storage_path

    await _storage_retry(_do_upload, label=f"upload/{storage_path}")
    return storage_path


async def create_signed_url(storage_path: str, expires_in: int = 3600) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{settings.supabase_url}/storage/v1/object/sign/{BUCKET}/{storage_path}",
            json={"expiresIn": expires_in},
            headers={
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "apikey": settings.supabase_service_role_key,
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Signed URL falhou: {resp.status_code} {resp.text}")
        data = resp.json()
        relative = data.get("signedURL") or data.get("signedUrl") or data.get("signed_url") or ""
        if not relative:
            raise RuntimeError(f"Supabase não retornou URL assinada para {storage_path}: {data}")
        return f"{settings.supabase_url}/storage/v1{relative}" if relative.startswith("/") else relative


async def download_file(storage_path: str) -> bytes:
    async def _do_download():
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(
                _storage_url(storage_path),
                headers=_headers(),
            )
            if resp.status_code == 404:
                raise FileNotFoundError(f"Arquivo não encontrado no storage: {storage_path}")
            if resp.status_code != 200:
                raise RuntimeError(f"Storage download falhou: {resp.status_code} {resp.text}")
            return resp.content

    return await _storage_retry(_do_download, label=f"download/{storage_path}")
