from pathlib import Path

from agno.agent import Agent
#from agno.models.huggingface import HuggingFace
from agno.models.openrouter import OpenRouter
from agno.db.base import BaseDb
from agno.tools.mcp import MCPTools

from ._base import resolve_db

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "docs.txt"
DOCS_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


def build_docs_agent(mcp_tools: MCPTools, db: BaseDb | None = None) -> Agent:
    db = resolve_db(db)

    return Agent(
        name="DocsAgent",
        role="Agente de documentação: Consulta e tira dúvidas sobre o Agenda Vix (Admin)",
        model=OpenRouter(id="x-ai/grok-4.3"),
        tools=[mcp_tools],
        tool_call_limit=6,
        instructions=DOCS_PROMPT,
        markdown=True,
        db=db,
        add_history_to_context=True,
        read_chat_history=True,
        num_history_messages=8,
        retries=3,
        delay_between_retries=5,
    )
