import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from agno.db.postgres import PostgresDb
from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters

from main import build_agent
from api.routers import chat

load_dotenv()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "Variável de ambiente DATABASE_URL não encontrada. "
            "Configure-a no .env antes de iniciar a API."
        )

    sync_url = database_url.replace("+psycopg_async", "+psycopg").replace(
        "+asyncpg", "+psycopg"
    )
    db = PostgresDb(db_url=sync_url)

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "jira_mcp.server"],
        env={**os.environ},
    )

    logger.info("Iniciando MCPTools (jira_mcp.server)...")
    async with MCPTools(
        server_params=server_params,
        exclude_tools=["get_project_info"],
    ) as mcp_tools:
        logger.info("MCPTools inicializado. Construindo agente...")
        app.state.agent = build_agent(mcp_tools, db=db)
        logger.info("Agente pronto. API disponível.")
        yield

    logger.info("MCPTools encerrado. Shutdown concluído.")


app = FastAPI(
    title="Bug Reporter Agent API",
    description=(
        "API HTTP para o agente N1 de abertura automática de chamados Jira. "
        "O histórico de cada sessão é persistido no PostgreSQL."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(chat.router, prefix="/api")
