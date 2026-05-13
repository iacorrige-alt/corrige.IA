import asyncio
import json
import logging
import logging.config
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.limiter import limiter
from app.routers import auth, turmas, alunos, atividades, correcao, pagamento, webhooks, agente


# Snapshot of standard LogRecord instance keys — used to detect extra={} keys reliably.
# logging.LogRecord.__dict__ is the *class* dict (methods/class vars), not instance attrs,
# so we instantiate a sentinel record to get the real instance attribute names.
_LOG_RECORD_BUILTIN_KEYS: frozenset[str] = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | {"message", "asctime"}


class _JSONFormatter(logging.Formatter):
    """Single-line JSON log records — structured, grep-friendly, Railway-compatible."""

    def format(self, record: logging.LogRecord) -> str:
        obj: dict = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Merge any extra keys passed via extra={} in logger calls
        for key, val in record.__dict__.items():
            if key not in _LOG_RECORD_BUILTIN_KEYS and not key.startswith("_"):
                obj[key] = val
        if record.exc_info:
            obj["exc"] = self.formatException(record.exc_info)
        return json.dumps(obj, ensure_ascii=False, default=str)


logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": _JSONFormatter}},
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "json",
        }
    },
    "root": {"level": "INFO", "handlers": ["stdout"]},
    # Silence noisy third-party loggers
    "loggers": {
        "uvicorn.access": {"level": "WARNING"},
        "httpx": {"level": "WARNING"},
    },
})

app = FastAPI(
    title="CorrigeAI API",
    description="API de correção automática de provas com IA",
    version="1.0.0",
)


@app.on_event("startup")
async def _configure_thread_pool():
    # Padrão do asyncio: min(32, cpu_count+4) — no Railway 1vCPU = apenas 5 threads.
    # Com correções concorrentes (muitas chamadas asyncio.to_thread ao Supabase),
    # 5 threads esgotam rápido. 40 threads acomodam ~10 usuários simultâneos.
    loop = asyncio.get_running_loop()
    loop.set_default_executor(ThreadPoolExecutor(max_workers=40))

_access_logger = logging.getLogger("corrigeai.access")


@app.middleware("http")
async def _log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    _access_logger.info(
        "%s %s %d",
        request.method, request.url.path, response.status_code,
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response

# Rate limiter — deve ser registrado antes dos outros middlewares
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS — origens controladas por variável de ambiente
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Routers
app.include_router(auth.router)
app.include_router(turmas.router)
app.include_router(alunos.router)
app.include_router(atividades.router)
app.include_router(correcao.router)
app.include_router(pagamento.router)
app.include_router(webhooks.router)
app.include_router(agente.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "CorrigeAI API"}
