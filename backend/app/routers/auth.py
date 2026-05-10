import asyncio
import logging

from fastapi import APIRouter, HTTPException, status, Depends
from supabase_auth.errors import AuthApiError

from app.db.supabase_client import get_supabase
from app.dependencies import get_current_user
from app.models.schemas import AuthResponse, LoginRequest, ProfessorOut, RefreshRequest, RegisterRequest

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
    for delay in (0.1, 0.2, 0.4, 0.8):
        await asyncio.sleep(delay)
        prof = await asyncio.to_thread(
            supabase.table("professores").select("nome").eq("id", resp.user.id).single().execute
        )
        if prof.data:
            nome = prof.data["nome"]
            break

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
