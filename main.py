import sys
import os
import asyncio

from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.huggingface import HuggingFace
from agno.db.json import JsonDb
from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters

load_dotenv()

# ─── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a QA automation assistant. Your job is to help QA engineers report bugs
as Jira tickets as quickly and accurately as possible.

When a QA engineer describes a bug, follow these steps IN ORDER:

1. Call `search_issues` ONCE with key terms from the description to check for
   duplicate tickets. Report any matches you find.

2. If no duplicates exist (or the engineer confirms it's a new ticket), call
   `create_issue` EXACTLY ONCE with a well-structured bug report written in
   Portuguese:
   - **summary**: A concise, action-oriented title.
   - **description**: A structured report in PLAIN TEXT (no markdown, no **, no #,
     no bullet symbols). Use line breaks and capitalized section titles to organize.
     Sections:
       * Passo a passo para reproduzir
       * Comportamento esperado
       * Comportamento atual
       * Ambiente / Plataforma (if mentioned)

3. As soon as `create_issue` returns successfully, reply IMMEDIATELY with:
   ✅ Ticket criado: <KEY>
   🔗 <URL>
   Then STOP — do not call any more tools.

STRICT RULES:
- NEVER call `create_issue` more than once per user message.
- NEVER retry `create_issue` with different parameters if the first call succeeds.
- NEVER call `search_issues` again after successfully creating a ticket.
- If `create_issue` returns a key and URL, the ticket is done — respond and stop.
- If the description lacks critical details, ask ONE focused follow-up question
  before creating the ticket.
"""

# ─── Agent factory ────────────────────────────────────────────────────────────


def build_agent(mcp_tools: MCPTools) -> Agent:
    return Agent(
        model=HuggingFace(id="Qwen/Qwen2.5-72B-Instruct"),
        tools=[mcp_tools],
        tool_call_limit=4,
        instructions=SYSTEM_PROMPT,
        markdown=True,
        db=JsonDb(db_path="tmp/agent_db"),
        add_history_to_context=True,
        read_chat_history=True,
        num_history_messages=8,
        retries=3,
        delay_between_retries=5,
    )


# ─── Entry point ─────────────────────────────────────────────────────────────


async def main() -> None:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["jira_mcp_server.py"],
        env={**os.environ},
    )

    async with MCPTools(
        server_params=server_params,
        exclude_tools=["get_project_info"],   # agent already knows to use "Bug"
    ) as mcp_tools:
        agent = build_agent(mcp_tools)

        # ── Interactive mode ──────────────────────────────────────────────────
        print("🤖 Bug Reporter Agent (type 'exit' or Ctrl-C to quit)\n")
        loop = asyncio.get_event_loop()
        while True:
            try:
                user_input = (
                    await loop.run_in_executor(None, lambda: input("You: "))
                ).strip()
            except (KeyboardInterrupt, EOFError):
                print("\nBye!")
                break

            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit", "q"}:
                print("Bye!")
                break

            await agent.aprint_response(user_input, stream=True, show_tool_calls=True)
            print()


if __name__ == "__main__":
    asyncio.run(main())
