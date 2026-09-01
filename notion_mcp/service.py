from __future__ import annotations

from notion_client import Client
from notion_client.errors import APIResponseError

from notion_mcp.client import get_client, get_root_page_id, page_url
from notion_schemas.page import PageContentResponse, PageItem


# ─── Custom Exceptions ────────────────────────────────────────────────────────


class NotionServiceError(Exception):
    pass


class PageNotFoundError(NotionServiceError):
    pass


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _extract_title(page: dict) -> str:
    """Extracts the plain-text title from a Notion page object."""
    props = page.get("properties", {})
    # Pages have a "title" property; databases use "Name" or a title-type property.
    for prop in props.values():
        if prop.get("type") == "title":
            rich = prop["title"]
            return "".join(t.get("plain_text", "") for t in rich).strip()
    return "Untitled"


def _extract_date(page: dict) -> str:
    """Returns the last_edited_time truncated to YYYY-MM-DD."""
    return page.get("last_edited_time", "")[:10]


def _block_to_text(block: dict) -> str:
    """Converts a single Notion block to a plain-text line."""
    btype = block.get("type", "")
    data = block.get(btype, {})

    rich_text: list = data.get("rich_text", [])
    text = "".join(t.get("plain_text", "") for t in rich_text)

    prefixes = {
        "heading_1": "# ",
        "heading_2": "## ",
        "heading_3": "### ",
        "bulleted_list_item": "• ",
        "numbered_list_item": "1. ",
        "to_do": "☐ " if not data.get("checked") else "☑ ",
        "toggle": "▶ ",
        "quote": "> ",
        "callout": "💡 ",
        "code": f"[{data.get('language', 'code')}] ",
        "divider": "---",
        "table_of_contents": "[Table of Contents]",
    }

    prefix = prefixes.get(btype, "")
    if btype == "divider":
        return "---"
    if btype == "table_of_contents":
        return "[Table of Contents]"
    return f"{prefix}{text}" if text or prefix else ""


# ─── Service ─────────────────────────────────────────────────────────────────


class NotionService:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = get_client()
        return self._client

    # ── search_pages ──────────────────────────────────────────────────────────

    def search_pages(self, query: str, max_results: int = 5) -> list[PageItem]:
        """Full-text search across the Notion workspace."""
        response = self.client.search(
            query=query,
            filter={"value": "page", "property": "object"},
            sort={"direction": "descending", "timestamp": "last_edited_time"},
            page_size=max_results,
        )
        results = []
        for page in response.get("results", []):
            results.append(
                PageItem(
                    page_id=page["id"],
                    title=_extract_title(page),
                    url=page_url(page["id"]),
                    last_edited=_extract_date(page),
                )
            )
        return results

    # ── get_page_content ──────────────────────────────────────────────────────

    def get_page_content(self, page_id: str) -> PageContentResponse:
        """Fetches page metadata and flattens all child blocks into plain text."""
        try:
            page = self.client.pages.retrieve(page_id=page_id)
        except APIResponseError as e:
            if e.status == 404:
                raise PageNotFoundError(f"Page not found: {page_id}") from e
            raise

        title = _extract_title(page)
        last_edited = _extract_date(page)
        url = page_url(page_id)

        content_lines = self._fetch_blocks_recursive(page_id, depth=0)
        content = "\n".join(line for line in content_lines if line)

        return PageContentResponse(
            page_id=page_id,
            title=title,
            url=url,
            last_edited=last_edited,
            content=content,
        )

    def get_page_content_shallow(self, page_id: str) -> PageContentResponse:
        """Fetches page content with only 1 level of block depth (fast, for pre-loading)."""
        try:
            page = self.client.pages.retrieve(page_id=page_id)
        except APIResponseError as e:
            if e.status == 404:
                raise PageNotFoundError(f"Page not found: {page_id}") from e
            raise

        title = _extract_title(page)
        last_edited = _extract_date(page)
        url = page_url(page_id)

        # max_depth=0 → only top-level blocks, no recursion
        content_lines = self._fetch_blocks_recursive(page_id, depth=0, max_depth=0)
        content = "\n".join(line for line in content_lines if line)

        return PageContentResponse(
            page_id=page_id,
            title=title,
            url=url,
            last_edited=last_edited,
            content=content,
        )

    def _fetch_blocks_recursive(
        self, block_id: str, depth: int, max_depth: int = 3
    ) -> list[str]:
        """Recursively fetches block content up to max_depth levels deep."""
        lines: list[str] = []
        indent = "  " * depth

        cursor = None
        while True:
            kwargs: dict = {"block_id": block_id, "page_size": 100}
            if cursor:
                kwargs["start_cursor"] = cursor

            response = self.client.blocks.children.list(**kwargs)
            for block in response.get("results", []):
                line = _block_to_text(block)
                if line:
                    lines.append(f"{indent}{line}")

                # Recurse into children if allowed
                if block.get("has_children") and depth < max_depth:
                    child_lines = self._fetch_blocks_recursive(
                        block["id"], depth + 1, max_depth
                    )
                    lines.extend(child_lines)

            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")

        return lines

    # ── list_child_pages ──────────────────────────────────────────────────────

    def list_child_pages(
        self, page_id: str | None = None, max_results: int = 50
    ) -> list[PageItem]:
        """Lists child pages or all accessible documentation pages."""
        parent_id = page_id or get_root_page_id()

        # If a specific page_id is requested, try recursive block traversal first
        if page_id:
            results: list[PageItem] = []
            self._collect_child_pages_recursive(parent_id, results, max_results, depth=0)
            if results:
                return results

        # Fallback / General listing: list all accessible pages via search
        response = self.client.search(
            filter={"value": "page", "property": "object"},
            sort={"direction": "descending", "timestamp": "last_edited_time"},
            page_size=min(100, max_results),
        )
        pages = []
        for page in response.get("results", []):
            pages.append(
                PageItem(
                    page_id=page["id"],
                    title=_extract_title(page),
                    url=page_url(page["id"]),
                    last_edited=_extract_date(page),
                )
            )
        return pages[:max_results]

    def _collect_child_pages_recursive(
        self, block_id: str, results: list[PageItem], max_results: int, depth: int, max_depth: int = 4
    ) -> None:
        """Helper to recursively scan blocks looking for child_page or link_to_page."""
        if depth > max_depth or len(results) >= max_results:
            return

        cursor = None
        while True:
            kwargs: dict = {"block_id": block_id, "page_size": 100}
            if cursor:
                kwargs["start_cursor"] = cursor

            try:
                response = self.client.blocks.children.list(**kwargs)
            except Exception:
                break

            for block in response.get("results", []):
                btype = block.get("type")
                if btype == "child_page":
                    child_id = block["id"]
                    child_title = block.get("child_page", {}).get("title", "Untitled")
                    results.append(
                        PageItem(
                            page_id=child_id,
                            title=child_title,
                            url=page_url(child_id),
                            last_edited=_extract_date(block),
                        )
                    )
                    if len(results) >= max_results:
                        return
                elif block.get("has_children") and depth < max_depth:
                    self._collect_child_pages_recursive(
                        block["id"], results, max_results, depth + 1, max_depth
                    )
                    if len(results) >= max_results:
                        return

            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")

