"""
Rate limiter global da aplicação.

Railway usa um único proxy reverso que ANEXA o IP real do cliente como o
último (mais à direita) hop em X-Forwarded-For. Usar o primeiro hop é
inseguro: o cliente pode enviar "X-Forwarded-For: fake_ip" e o Railway
não sobrescreve — apenas acrescenta o IP real no final.

get_real_ip extrai o último hop de X-Forwarded-For (adicionado pelo proxy
Railway, não controlado pelo cliente).
"""
from slowapi import Limiter
from starlette.requests import Request


def get_real_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # O Railway adiciona o IP real como último hop; os anteriores podem ser
        # forjados pelo cliente — nunca confiar no primeiro.
        hops = [h.strip() for h in forwarded_for.split(",")]
        return hops[-1]
    # Fallback para desenvolvimento local (sem proxy)
    return request.client.host if request.client else "127.0.0.1"


limiter = Limiter(key_func=get_real_ip)
