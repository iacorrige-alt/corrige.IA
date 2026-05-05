import asyncio

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from gotrue.errors import AuthApiError
from app.db.supabase_client import get_supabase

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Validate the JWT token with Supabase and return the user payload."""
    token = credentials.credentials
    supabase = get_supabase()
    try:
        response = await asyncio.to_thread(supabase.auth.get_user, token)
    except AuthApiError as exc:
        # Auth-specific errors (invalid token, expired, revoked)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nao autorizado.",
        ) from exc
    except Exception as exc:
        # Network errors, Supabase unavailable, etc. — not a 401
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servico de autenticacao temporariamente indisponivel.",
        ) from exc

    # Check outside try/except so HTTPException(401) is never swallowed by
    # the broad `except Exception` clause above.
    if response.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido ou expirado.",
        )
    return {"id": response.user.id, "email": response.user.email}
