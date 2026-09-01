import sys
import os
import asyncio

from dotenv import load_dotenv
from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters

from Ai import build_team

load_dotenv()


# ─── Entry point ─────────────────────────────────────────────────────────────


async def main() -> None:
    jira_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "jira_mcp.server"],
        env={**os.environ},
    )
    notion_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "notion_mcp.server"],
        env={**os.environ},
    )

    async with MCPTools(
        server_params=jira_params,
        exclude_tools=["get_project_info"],
    ) as jira_tools:
        async with MCPTools(server_params=notion_params) as notion_tools:
            team = build_team(jira_tools, notion_tools)

            # ── Interactive mode ──────────────────────────────────────────────
            print("🤖 Bug Reporter Team (type 'exit' or Ctrl-C to quit)\n")
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

                if user_input.lower() in {"exit", "quit"}:
                    break

                await team.aprint_response(user_input, stream=True)
                print()


if __name__ == "__main__":
    asyncio.run(main())

