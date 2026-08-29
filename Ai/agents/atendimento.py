import os
from pathlib import Path

from agno.agent import Agent
from agno.models.huggingface import HuggingFace
from agno.db.base import BaseDb
from agno.db.postgres import PostgresDb
from agno.tools.mcp import MCPTools

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "atendimento.txt"
ATENDIMENTO_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


def build_atendimento_agent(mcp_tools: MCPTools, db: BaseDb | None = None) -> Agent:
    if db is None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "Variável de ambiente DATABASE_URL não encontrada. "
                "Configure-a no .env antes de iniciar o agente."
            )
        sync_url = database_url.replace("+psycopg_async", "+psycopg").replace(
            "+asyncpg", "+psycopg"
        )
        db = PostgresDb(db_url=sync_url)

    return Agent(
        name="AtendimentoAgent",
        role="Agente de atendimento N1: abre, consulta, enriquece e lista chamados no Jira.",
        model=HuggingFace(id="Qwen/Qwen3-8B"),
        tools=[mcp_tools],
        tool_call_limit=6,
        instructions=ATENDIMENTO_PROMPT,
        markdown=True,
        db=db,
        add_history_to_context=True,
        read_chat_history=True,
        num_history_messages=8,
        retries=3,
        delay_between_retries=5,
    )
