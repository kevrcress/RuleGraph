"""Confluence connector — Confluence REST API."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ConfluenceConnector:
    """
    Connects to a Confluence space and yields page content.
    Supports migration-only mode.
    """

    def __init__(self, url: str, space: str, pat: str,
                 migrate_only: bool = True):
        self.url = url
        self.space = space
        self.pat = pat
        self.migrate_only = migrate_only

    async def list_pages(self) -> list[dict]:
        """Return a list of {path, content} dicts for all pages in the configured space."""
        raise NotImplementedError("Confluence connector not yet implemented")

    async def get_page_content(self, page_id: str) -> str:
        """Fetch a single Confluence page's content."""
        raise NotImplementedError("Confluence connector not yet implemented")
