import sys
import os

# Add backend root to path so `app.*` imports resolve without installation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Provide dummy env vars so app.config doesn't fail on import
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
