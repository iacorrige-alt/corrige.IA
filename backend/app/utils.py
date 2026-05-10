from fastapi import HTTPException, UploadFile


async def ler_arquivo(file: UploadFile, max_bytes: int) -> bytes:
    """Lê arquivo em chunks, rejeitando se ultrapassar max_bytes antes de alocar tudo em memória."""
    partes = []
    total = 0
    limite_mb = max_bytes // (1024 * 1024)
    while True:
        chunk = await file.read(65536)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"Arquivo '{file.filename}' excede o limite de {limite_mb} MB.",
            )
        partes.append(chunk)
    return b"".join(partes)
