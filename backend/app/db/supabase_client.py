import threading
from supabase import create_client, Client
from app.config import settings

_local = threading.local()


def get_supabase() -> Client:
    """Return a thread-local Supabase client using the service role key.

    Each thread (asyncio.to_thread worker) gets its own client instance,
    eliminating contention on the shared httpx connection pool when multiple
    corrections run concurrently.
    """
    if not hasattr(_local, "client"):
        _local.client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _local.client
