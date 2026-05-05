"""
Utilitário para confirmar manualmente o e-mail de um usuário no Supabase.
Uso (com o venv ativado):

  cd backend
  python scripts/confirm_user.py

Ou passando o e-mail direto:
  python scripts/confirm_user.py professor@escola.com
"""
import os
import sys

from dotenv import load_dotenv
from supabase import create_client

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("❌ SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY não encontrados no .env")
    sys.exit(1)

supabase = create_client(url, key)

email = sys.argv[1] if len(sys.argv) > 1 else input("E-mail do usuário para confirmar: ").strip()

users_resp = supabase.auth.admin.list_users()
users = users_resp if isinstance(users_resp, list) else getattr(users_resp, "users", [])

for user in users:
    if user.email == email:
        supabase.auth.admin.update_user_by_id(user.id, {"email_confirm": True})
        print(f"[OK] Usuario '{email}' confirmado com sucesso.")
        sys.exit(0)

print(f"[ERRO] Usuario '{email}' nao encontrado.")
sys.exit(1)
