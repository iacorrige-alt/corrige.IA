import asyncio
import logging

import httpx
from fastapi import APIRouter, HTTPException, Request, status, Depends
from supabase_auth.errors import AuthApiError

from app.config import settings
from app.db.supabase_client import get_supabase
from app.dependencies import get_current_user
from app.limiter import limiter
from app.models.schemas import (
    AuthResponse, ChangePasswordRequest, LoginRequest,
    ProfessorOut, ProfessorUpdate, RefreshRequest, RegisterRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _build_auth_response(session, user, nome: str) -> AuthResponse:
    """Monta AuthResponse a partir de uma sessão Supabase."""
    import time
    expires_at = session.expires_at or (int(time.time()) + (session.expires_in or 3600))
    return AuthResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_at=expires_at,
        user_id=str(user.id),
        email=user.email,
        nome=nome,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    """Create a new teacher account and return an active session immediately."""
    supabase = get_supabase()
    try:
        resp = await asyncio.to_thread(
            supabase.auth.sign_up,
            {
                "email": body.email,
                "password": body.password,
                "options": {"data": {"nome": body.nome}},
            },
        )
    except AuthApiError as exc:
        msg = str(exc).lower()
        if "already registered" in msg or "already exists" in msg or "email address has already been registered" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este e-mail já está cadastrado. Faça login.",
            )
        logger.error("Erro ao criar conta para %s: %s", body.email, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não foi possível criar a conta: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("Erro inesperado no registro: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de autenticação temporariamente indisponível.",
        ) from exc

    if resp.session is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirme seu e-mail antes de entrar. Verifique sua caixa de entrada.",
        )

    # Aguarda o trigger handle_new_user() inserir a linha em professores.
    nome = body.nome
    prof_data = None
    for delay in (0.1, 0.2, 0.4, 0.8):
        await asyncio.sleep(delay)
        prof = await asyncio.to_thread(
            supabase.table("professores").select("nome").eq("id", resp.user.id).single().execute
        )
        if prof.data:
            nome = prof.data["nome"]
            prof_data = prof.data
            break

    if not prof_data:
        # Trigger falhou — inserir manualmente para não deixar conta em estado quebrado.
        logger.error(
            "Trigger handle_new_user nao executou para user %s — inserindo professores manualmente",
            resp.user.id, extra={"user_id": str(resp.user.id)},
        )
        try:
            await asyncio.to_thread(
                supabase.table("professores").insert({
                    "id": str(resp.user.id),
                    "nome": body.nome,
                    "email": body.email,
                }).execute
            )
        except Exception as insert_exc:
            logger.error("Fallback insert em professores falhou: %s", insert_exc)

    logger.info(
        "Nova conta criada: %s (id=%s)",
        resp.user.email, resp.user.id,
        extra={"user_id": str(resp.user.id)},
    )
    return _build_auth_response(resp.session, resp.user, nome)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    supabase = get_supabase()
    try:
        resp = await asyncio.to_thread(
            supabase.auth.sign_in_with_password,
            {"email": body.email, "password": body.password},
        )
    except AuthApiError as exc:
        msg = str(exc).lower()
        if "email not confirmed" in msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="E-mail ainda não confirmado. Verifique sua caixa de entrada ou entre em contato com o suporte.",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas. Verifique e-mail e senha.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de autenticação temporariamente indisponível.",
        ) from exc

    if resp.session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas.")

    prof = await asyncio.to_thread(
        supabase.table("professores").select("nome").eq("id", resp.user.id).single().execute
    )
    nome = prof.data["nome"] if prof.data else resp.user.email.split("@")[0]

    return _build_auth_response(resp.session, resp.user, nome)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(body: RefreshRequest):
    """Renova a sessão usando o refresh_token. Retorna novo access_token e refresh_token."""
    supabase = get_supabase()
    try:
        resp = await asyncio.to_thread(supabase.auth.refresh_session, body.refresh_token)
    except AuthApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão expirada. Faça login novamente.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de autenticação temporariamente indisponível.",
        ) from exc

    if resp.session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida.")

    prof = await asyncio.to_thread(
        supabase.table("professores").select("nome").eq("id", resp.user.id).single().execute
    )
    nome = prof.data["nome"] if prof.data else resp.user.email.split("@")[0]

    return _build_auth_response(resp.session, resp.user, nome)


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    # JWTs são stateless; o cliente remove o token localmente.
    return {"message": "Logout realizado com sucesso."}


@router.get("/me", response_model=ProfessorOut)
async def me(current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    prof = await asyncio.to_thread(
        supabase.table("professores").select("*").eq("id", current_user["id"]).single().execute
    )
    if not prof.data:
        raise HTTPException(status_code=404, detail="Professor não encontrado.")
    return prof.data


@router.patch("/me", response_model=ProfessorOut)
async def atualizar_perfil(
    body: ProfessorUpdate,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    result = await asyncio.to_thread(
        supabase.table("professores")
        .update({"nome": body.nome})
        .eq("id", current_user["id"])
        .execute
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Professor não encontrado.")
    return result.data[0]


@router.post("/change-password")
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{settings.supabase_url}/auth/v1/token?grant_type=password",
            json={"email": current_user["email"], "password": body.senha_atual},
            headers={
                "apikey": settings.supabase_service_role_key,
                "Content-Type": "application/json",
            },
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Senha atual incorreta.")

    async with httpx.AsyncClient(timeout=15) as client:
        update_resp = await client.put(
            f"{settings.supabase_url}/auth/v1/admin/users/{current_user['id']}",
            json={"password": body.nova_senha},
            headers={
                "apikey": settings.supabase_service_role_key,
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "Content-Type": "application/json",
            },
        )
    if update_resp.status_code != 200:
        logger.error("Erro ao alterar senha para %s: %s %s", current_user["id"], update_resp.status_code, update_resp.text)
        raise HTTPException(status_code=500, detail="Erro ao alterar a senha.")

    return {"message": "Senha alterada com sucesso."}
