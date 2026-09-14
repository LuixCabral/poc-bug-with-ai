"""
api/rate_limit.py
─────────────────
Módulo central de rate limiting usando slowapi + Redis.

- `limiter`: instância compartilhada do Limiter (chave = IP do cliente).
- `CHAT_RATE_LIMIT`: string de limite configurável via env (padrão: "10/minute").
- `rate_limit_exceeded_handler`: handler de exceção que mantém o contrato
  de streaming SSE em vez de retornar um HTTP 429 JSON padrão.
"""

import json
import logging
import os

from fastapi import Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

# ─── Configuração via variáveis de ambiente ───────────────────────────────────

REDIS_URL: str = os.getenv("REDIS_URL")
CHAT_RATE_LIMIT: str = os.getenv("RATE_LIMIT_CHAT")

# ─── Limiter ──────────────────────────────────────────────────────────────────

limiter = Limiter(
    key_func=lambda request: request.client.host,
    storage_uri=REDIS_URL,
    strategy="moving-window",   
)

# ─── Exception handler ────────────────────────────────────────────────────────


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> StreamingResponse:
    """
    Intercepta RateLimitExceeded e retorna um evento SSE de erro,
    mantendo o contrato text/event-stream do endpoint /api/chat.
    """
    logger.warning(
        "Rate limit excedido para o IP %s: %s",
        request.client.host,
        exc.detail,
    )

    detail = f"rate limit exceeded: {exc.detail}"

    async def sse_error():
        payload = json.dumps({"event": "error", "detail": detail})
        yield f"data: {payload}\n\n"

    return StreamingResponse(
        sse_error(),
        media_type="text/event-stream",
        status_code=429,
    )
