import asyncio
import logging

from fastapi import APIRouter, HTTPException, status, Depends
from gotrue.errors import AuthApiError

from app.db.supabase_client import get_supabase
from app.dependencies import get_current_user
from app.models.schemas import AuthResponse, LoginRequest, ProfessorOut, RegisterRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    """Create a new teacher account and return an active session immediately."""
    supabase = get_supabase()
    try:
        # Admin API: creates user with email pre-confirmed so teachers log in right away
        created = await asyncio.to_thread(
            supabase.auth.admin.create_user,
            {
                "email": body.email,
                "password": body.password,
                "user_metadata": {"nome": body.nome},
                "email_confirm": True,
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

    # Sign in immediately to get an active JWT session
    try:
        session_resp = await asyncio.to_thread(
            supabase.auth.sign_in_with_password,
            {"email": body.email, "password": body.password},
        )
    except Exception as exc:
        logger.error("Conta criada mas login automático falhou para %s: %s", body.email, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Conta criada, mas o login automático falhou. Tente entrar manualmente.",
        ) from exc

    # The trigger handle_new_user() runs synchronously on INSERT in auth.users,
    # so the professores row already exists by the time we reach here.
    prof = await asyncio.to_thread(
        supabase.table("professores").select("nome").eq("id", created.user.id).single().execute
    )
    nome = prof.data["nome"] if prof.data else body.nome

    logger.info(
        "Nova conta criada: %s (id=%s)",
        created.user.email, created.user.id,
        extra={"user_id": str(created.user.id)},
    )
    return AuthResponse(
        access_token=session_resp.session.access_token,
        user_id=str(created.user.id),
        email=created.user.email,
        nome=nome,
    )


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

    # Fetch professor name
    prof = await asyncio.to_thread(
        supabase.table("professores").select("nome").eq("id", resp.user.id).single().execute
    )
    nome = prof.data["nome"] if prof.data else resp.user.email.split("@")[0]

    return AuthResponse(
        access_token=resp.session.access_token,
        user_id=str(resp.user.id),
        email=resp.user.email,
        nome=nome,
    )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    # JWTs são stateless; o cliente remove o token localmente.
    # Não chamamos supabase.auth.sign_out() pois o cliente usa service role
    # compartilhado — sign_out() sem JWT afetaria o singleton global.
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
