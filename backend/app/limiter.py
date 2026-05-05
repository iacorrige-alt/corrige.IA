"""
Rate limiter global da aplicação.

Railway (e qualquer proxy reverso) encaminha o IP real do cliente no header
X-Forwarded-For. O helper padrão do slowapi usa request.client.host, que
retorna o IP do proxy — o que bloquearia TODOS os usuários simultaneamente
ao primeiro limite atingido.

get_real_ip extrai o primeiro hop de X-Forwarded-For (o IP do cliente real).
"""
from slowapi import Limiter
from starlette.requests import Request


def get_real_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # "client, proxy1, proxy2" — o primeiro é sempre o cliente real
        return forwarded_for.split(",")[0].strip()
    # Fallback para desenvolvimento local (sem proxy)
    return request.client.host if request.client else "127.0.0.1"


limiter = Limiter(key_func=get_real_ip)
