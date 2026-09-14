# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

# Instala uv (gerenciador de pacotes rápido)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copia manifesto de dependências primeiro (aproveita cache do Docker)
COPY pyproject.toml uv.lock ./

# Instala dependências no ambiente virtual embutido
RUN uv sync --frozen --no-dev

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.13-slim

WORKDIR /app

# Copia o venv gerado no builder
COPY --from=builder /app/.venv /app/.venv

# Copia o código-fonte
COPY . .

# Garante que o venv seja usado
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
