"""
Tools:
  - get_project_info   : Returns issue types and components for a project.
  - search_issues      : Searches for existing issues via JQL (duplicate check).
  - create_issue       : Creates a new bug in Jira.

Environment variables (loaded from .env):
  JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY
"""

import os

from dotenv import load_dotenv
from fastmcp import FastMCP
from jira import JIRA

load_dotenv()

mcp = FastMCP("Jira MCP Server")

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _client() -> JIRA:
    """Return an authenticated Jira client."""
    return JIRA(
        server=os.environ["JIRA_URL"],
        basic_auth=(os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"]),
    )


def _default_project() -> str:
    return os.environ["JIRA_PROJECT_KEY"]


# ─── Tools ────────────────────────────────────────────────────────────────────


@mcp.tool(title="Get Project Info")
def get_project_info(project_key: str = "") -> dict:
    key = project_key or _default_project()
    jira = _client()

    project = jira.project(key)
    issue_types = [it.name for it in jira.issue_types_for_project(key)]
    components = [c.name for c in jira.project_components(key)]

    return {
        "project_key": project.key,
        "project_name": project.name,
        "issue_types": issue_types,
        "components": components,
    }


@mcp.tool(title="Search Issues")
def search_issues(query: str, max_results: int = 5) -> list[dict]:

    key = _default_project()
    jira = _client()

    if "=" not in query and "ORDER BY" not in query.upper():
        jql = f'project = "{key}" AND text ~ "{query}" ORDER BY created DESC'
    else:
        jql = query

    issues = jira.search_issues(jql, maxResults=max_results)

    return [
        {
            "key": issue.key,
            "summary": issue.fields.summary,
            "status": issue.fields.status.name,
            "url": f"{os.environ['JIRA_URL']}/browse/{issue.key}",
        }
        for issue in issues
    ]


@mcp.tool(title="Create Jira Issue")
def create_issue(
    summary: str,
    description: str,
    priority: str = "Medium",
) -> dict:
    
    key = _default_project()
    jira = _client()

    issue_dict = {
        "project": {"key": key},
        "summary": summary,
        "description": description,
        "issuetype": {"name": "Task"},
        "priority": {"name": priority},
    }

    new_issue = jira.create_issue(fields=issue_dict)

    return {
        "key": new_issue.key,
        "summary": new_issue.fields.summary,
        "url": f"{os.environ['JIRA_URL']}/browse/{new_issue.key}",
    }


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
