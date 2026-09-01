import notion_mcp.config  # noqa: F401 — validates env vars at startup

from fastmcp import FastMCP

from notion_mcp.tools import register_tools

mcp = FastMCP("Notion MCP Server")
register_tools(mcp)

if __name__ == "__main__":
    mcp.run()
