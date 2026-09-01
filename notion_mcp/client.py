import os

from notion_client import Client

_notion_client: Client | None = None


def get_client() -> Client:
    """Returns the authenticated Notion client (lazy singleton)."""
    global _notion_client
    if _notion_client is None:
        _notion_client = Client(auth=os.environ["NOTION_API_TOKEN"])
    return _notion_client


def get_root_page_id() -> str | None:
    """Returns the optional root page ID defined in the .env."""
    return os.environ.get("NOTION_ROOT_PAGE_ID") or None


def page_url(page_id: str) -> str:
    """Returns the Notion browser URL for a page (dashes stripped)."""
    clean_id = page_id.replace("-", "")
    return f"https://www.notion.so/{clean_id}"
