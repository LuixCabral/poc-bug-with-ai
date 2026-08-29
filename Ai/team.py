from pathlib import Path

from agno.db.base import BaseDb
from agno.models.huggingface import HuggingFace
from agno.team import Team
from agno.tools.mcp import MCPTools

from .agents import build_atendimento_agent, build_docs_agent

# ─── Triage prompt ────────────────────────────────────────────────────────────

_TRIAGE_PROMPT_PATH = Path(__file__).parent / "prompts" / "triage.txt"
TRIAGE_PROMPT = _TRIAGE_PROMPT_PATH.read_text(encoding="utf-8")


# ─── Team factory ─────────────────────────────────────────────────────────────


def build_team(mcp_tools: MCPTools, db: BaseDb | None = None) -> Team:
    atendimento = build_atendimento_agent(mcp_tools, db)
    docs = build_docs_agent(db)

    return Team(
        name="TriageAgent",
        mode="coordinate",
        model=HuggingFace(id="Qwen/Qwen3-8B"),
        members=[
            atendimento,
            docs,
        ],
        instructions=TRIAGE_PROMPT,
        markdown=True,
        show_members_responses=True,
        add_team_history_to_members=True,
        num_team_history_runs=4,
    )
