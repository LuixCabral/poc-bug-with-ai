"""
MCP tools exposed to the DocsAgent.
Registered via register_tools(mcp) to keep the server decoupled from the tools.

Each tool is a thin MCP adapter: it receives parameters from the LLM, delegates
execution to NotionService, and normalises errors into consistent dict responses.
All business logic lives exclusively in `notion_mcp.service`.

Tools:
  - search_pages      : Full-text search across the Notion workspace.
  - get_page_content  : Fetches and flattens all blocks of a page into plain text.
  - list_child_pages  : Lists direct child pages of a given page (or root).
"""

from fastmcp import FastMCP
from notion_client.errors import APIResponseError

from notion_mcp.service import NotionService, NotionServiceError, PageNotFoundError
from notion_schemas.page import PageContentResponse, PageItem


def register_tools(mcp: FastMCP, service: NotionService | None = None) -> None:
    """
    Registers all tools on the provided FastMCP server instance.

    Args:
        mcp:     FastMCP server instance.
        service: Optional NotionService. If not provided, a default instance
                 (configured via environment variables) will be created.
                 Useful for dependency injection in tests.
    """
    _service = service or NotionService()

    @mcp.tool(title="Search Notion Pages")
    def search_pages(
        query: str, max_results: int = 5
    ) -> list[PageItem] | list[dict]:
        """
        Full-text search across the Notion workspace.

        Use this as the FIRST step when the user asks a documentation question.
        Returns a ranked list of matching pages with their IDs, titles, and URLs.
        Follow up with get_page_content to read the actual content of a page.

        Args:
            query:       The search terms (plain text).
            max_results: Maximum number of pages to return (default 5).
        """
        try:
            return _service.search_pages(query, max_results)
        except APIResponseError as e:
            return [{"error": f"Notion API error [{e.status}]: {e.code}"}]
        except Exception as e:
            return [{"error": f"Unexpected error: {str(e)}"}]

    @mcp.tool(title="Get Page Content")
    def get_page_content(page_id: str) -> PageContentResponse | dict:
        """
        Fetches the full content of a Notion page as plain text.

        Use the page_id returned by search_pages or list_child_pages.
        Content is fetched recursively up to 3 levels of nesting.

        Args:
            page_id: The Notion page ID (e.g. '1a2b3c4d-...').
        """
        try:
            return _service.get_page_content(page_id)
        except PageNotFoundError as e:
            return {"error": str(e)}
        except APIResponseError as e:
            return {"error": f"Notion API error [{e.status}]: {e.code}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    @mcp.tool(title="List Child Pages")
    def list_child_pages(
        page_id: str = "", max_results: int = 20
    ) -> list[PageItem] | list[dict]:
        """
        Lists the direct child pages under a given Notion page.

        Use this to browse the documentation tree when you need to discover
        what sections exist before diving into a specific page.
        Omit page_id to start from the root documentation page (NOTION_ROOT_PAGE_ID).

        Args:
            page_id:     Parent page ID. Leave empty to use the root page.
            max_results: Maximum number of child pages to return (default 20).
        """
        try:
            return _service.list_child_pages(page_id or None, max_results)
        except NotionServiceError as e:
            return [{"error": str(e)}]
        except APIResponseError as e:
            return [{"error": f"Notion API error [{e.status}]: {e.code}"}]
        except Exception as e:
            return [{"error": f"Unexpected error: {str(e)}"}]
