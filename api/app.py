import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agno.db.postgres import PostgresDb
from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters

from Ai import build_team
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
    notion_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "notion_mcp.server"],
        env={**os.environ},
    )

    logger.info("Iniciando MCPTools (jira_mcp.server)...")
    async with MCPTools(
        server_params=server_params,
        exclude_tools=["get_project_info"],
        timeout_seconds=30,
    ) as jira_tools:
        logger.info("Iniciando MCPTools (notion_mcp.server)...")
        async with MCPTools(server_params=notion_params, timeout_seconds=60) as notion_tools:
            logger.info("MCPTools inicializados. Construindo team...")
            app.state.team = build_team(jira_tools, notion_tools, db=db)
            logger.info("Team pronto. API disponível.")
            yield

    logger.info("MCPTools encerrados. Shutdown concluído.")


app = FastAPI(
    title="Bug Reporter Agent API",
    description=(
        "API HTTP para o agente N1 de abertura automática de chamados Jira. "
        "O histórico de cada sessão é persistido no PostgreSQL."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],)

app.include_router(chat.router, prefix="/api")
