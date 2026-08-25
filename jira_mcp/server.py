import jira_mcp.config

from fastmcp import FastMCP

from jira_mcp.tools import register_tools

mcp = FastMCP("Jira MCP Server")
register_tools(mcp)

if __name__ == "__main__":
    mcp.run()
