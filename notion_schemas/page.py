from pydantic import BaseModel


# ─── Responses: search_pages / list_child_pages ───────────────────────────────


class PageItem(BaseModel):
    """Lightweight page reference returned by search and list operations."""

    page_id: str
    title: str
    url: str
    last_edited: str  # ISO date string (YYYY-MM-DD)


# ─── Response: get_page_content ───────────────────────────────────────────────


class PageContentResponse(BaseModel):
    """Full readable content of a single Notion page."""

    page_id: str
    title: str
    url: str
    last_edited: str  # ISO date string (YYYY-MM-DD)
    content: str      # Plain-text flattened block content
