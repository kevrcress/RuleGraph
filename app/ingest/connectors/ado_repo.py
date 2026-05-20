"""Azure DevOps repository connector — git clone + ADO REST API."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AdoRepoConnector:
    """
    Connects to an Azure DevOps git repository and yields file content.
    Uses git clone for bulk migration; ADO REST API for incremental sync.
    """

    def __init__(self, repo_url: str, pat: str, branch: str = "main",
                 paths: Optional[list[str]] = None,
                 exclude: Optional[list[str]] = None,
                 test_paths: Optional[list[str]] = None):
        self.repo_url = repo_url
        self.pat = pat
        self.branch = branch
        self.paths = paths or ["/"]
        self.exclude = exclude or []
        self.test_paths = test_paths or []

    async def list_files(self) -> list[dict]:
        """
        Return a list of {path, content} dicts for all files matching paths/exclude config.
        Phase 1: git clone implementation.
        """
        raise NotImplementedError("ADO repo connector not yet implemented — use /ingest/file for local files")

    async def get_file_content(self, path: str) -> str:
        """Fetch a single file's content from the ADO repo."""
        raise NotImplementedError("ADO repo connector not yet implemented")
