from supabase import create_client, Client
from app.config import settings

_client: Client | None = None


def get_supabase() -> Client:
    """Return a Supabase client using the service role key (backend only)."""
    global _client
    if _client is None:
        _client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _client


