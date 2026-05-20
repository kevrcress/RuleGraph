"""GitHub repository connector — git clone or GitHub API."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GitHubRepoConnector:
    """
    Connects to a GitHub repository and yields file content.
    Supports both public and private repos via PAT authentication.
    GitHub wikis are standard git repos and use the same connector.
    """

    def __init__(self, repo_url: str, pat: Optional[str] = None,
                 branch: str = "main",
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
        """Return a list of {path, content} dicts for all files matching paths/exclude config."""
        raise NotImplementedError("GitHub repo connector not yet implemented — use /ingest/file for local files")

    async def get_file_content(self, path: str) -> str:
        """Fetch a single file's content from the GitHub repo."""
        raise NotImplementedError("GitHub repo connector not yet implemented")
