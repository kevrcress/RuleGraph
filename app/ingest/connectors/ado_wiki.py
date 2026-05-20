"""Azure DevOps wiki connector — ADO Wiki REST API."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AdoWikiConnector:
    """
    Connects to an Azure DevOps wiki and yields page content.

    ADO Wiki API:
      GET https://dev.azure.com/{org}/{project}/_apis/wiki/wikis
      GET https://dev.azure.com/{org}/{project}/_apis/wiki/wikis/{wikiId}/pages?recursionLevel=full
    Auth: PAT via Authorization header (base64 encoded).
    """

    def __init__(self, org: str, project: str, pat: str,
                 migrate_only: bool = True,
                 sync_on_webhook: bool = False,
                 treat_as_authoritative: bool = False):
        self.org = org
        self.project = project
        self.pat = pat
        self.migrate_only = migrate_only
        self.sync_on_webhook = sync_on_webhook
        self.treat_as_authoritative = treat_as_authoritative

    async def list_pages(self) -> list[dict]:
        """Return a list of {path, content} dicts for all wiki pages."""
        raise NotImplementedError("ADO wiki connector not yet implemented")

    async def get_page_content(self, page_id: str) -> str:
        """Fetch a single wiki page's markdown content."""
        raise NotImplementedError("ADO wiki connector not yet implemented")
