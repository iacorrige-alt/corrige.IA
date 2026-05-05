"""Define a senha de um usuario diretamente via admin API."""
import os, sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
supabase = create_client(url, key)

email = sys.argv[1] if len(sys.argv) > 1 else input("Email: ").strip()
password = sys.argv[2] if len(sys.argv) > 2 else input("Nova senha: ").strip()

users_resp = supabase.auth.admin.list_users()
users = users_resp if isinstance(users_resp, list) else getattr(users_resp, "users", [])

for user in users:
    if user.email == email:
        supabase.auth.admin.update_user_by_id(user.id, {"password": password})
        print(f"[OK] Senha de '{email}' alterada com sucesso.")
        sys.exit(0)

print(f"[ERRO] Usuario '{email}' nao encontrado.")
sys.exit(1)
