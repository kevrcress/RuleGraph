"""GitHub repository connector — git clone with optional PAT auth."""
import asyncio
import fnmatch
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)

DEFAULT_EXTENSIONS = {
    ".cs", ".py", ".ts", ".tsx", ".js", ".jsx",
    ".java", ".go", ".rb", ".rs", ".kt", ".swift",
    ".php", ".scala", ".md", ".txt",
}

DEFAULT_EXCLUDE = [
    "**/node_modules/**", "**/obj/**", "**/bin/**",
    "**/.git/**", "**/.github/**", "**/__pycache__/**", "**/.mypy_cache/**",
    "**/dist/**", "**/build/**", "**/.next/**",
    "**/migrations/**", "**/Migrations/**",
    "**/*.lock", "**/package-lock.json",
    # Project meta-files — contain developer/project rules, not application business logic
    "**/README*", "**/CONTRIBUTING*", "**/CHANGELOG*", "**/CHANGES*",
    "**/CODE_OF_CONDUCT*", "**/SECURITY*", "**/SUPPORT*", "**/CODEOWNERS",
    "**/CLAUDE.md", "**/DECISIONS.md", "**/*.spec.md", "**/rulegraph-spec*",
]

MAX_FILE_BYTES = 200_000
MIN_FILE_LINES = 5  # skip barrel/re-export files (almost always ≤4 lines)


class GitHubRepoConnector:
    """
    Clones a GitHub repo (shallow) and yields file content for ingest.
    Supports public repos and private repos via PAT.

    On the first ingest (last_commit_sha=None) all matching files are returned.
    On subsequent ingests, only files changed since last_commit_sha are returned
    by fetching that commit and running git diff. Falls back to full ingest if
    the base SHA is no longer fetchable.
    """

    def __init__(
        self,
        repo_url: str,
        pat: Optional[str] = None,
        branch: str = "main",
        paths: Optional[list[str]] = None,
        exclude: Optional[list[str]] = None,
        test_paths: Optional[list[str]] = None,
        last_commit_sha: Optional[str] = None,
    ):
        self.repo_url = repo_url
        self.pat = pat
        self.branch = branch
        self.paths = paths or []
        self.exclude = exclude or []
        self.test_paths = test_paths or []
        self.last_commit_sha = last_commit_sha

    def _auth_url(self) -> str:
        url = self.repo_url
        if "://" not in url:
            url = f"https://{url}"
        if not self.pat:
            return url
        parsed = urlparse(url)
        authed = parsed._replace(netloc=f"{self.pat}@{parsed.netloc}")
        return urlunparse(authed)

    def _is_excluded(self, rel: str, filename: str) -> bool:
        all_patterns = DEFAULT_EXCLUDE + self.exclude
        for pat in all_patterns:
            if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(filename, pat):
                return True
        return False

    def _in_configured_paths(self, rel: str) -> bool:
        if not self.paths:
            return True
        return any(rel.startswith(p.lstrip("/")) for p in self.paths)

    def _is_test_file(self, rel: str) -> bool:
        if not self.test_paths:
            return False
        return any(rel.startswith(tp.lstrip("/")) for tp in self.test_paths)

    def _clone(self, clone_url: str, dest: str) -> None:
        result = subprocess.run(
            ["git", "clone", "--depth=1", "--single-branch",
             "--branch", self.branch, clone_url, dest],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            # Scrub auth URL from stderr before surfacing — it contains the PAT
            safe_err = result.stderr.replace(clone_url, self.repo_url)
            raise RuntimeError(f"git clone failed: {safe_err.strip()}")

    def _get_head_sha(self, repo_dir: str) -> str:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir, capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git rev-parse HEAD failed: {result.stderr.strip()}")
        return result.stdout.strip()

    def _get_changed_paths(self, repo_dir: str, clone_url: str, base_sha: str) -> Optional[list[str]]:
        """
        Fetch base_sha and return the list of paths that differ from it to HEAD.
        Returns None if the fetch fails (caller should fall back to full ingest).
        Only added/modified files are returned — deleted files are skipped since
        removing their extracted rules is not implemented.
        """
        fetch = subprocess.run(
            ["git", "fetch", "--depth=1", clone_url, base_sha],
            cwd=repo_dir, capture_output=True, text=True,
        )
        if fetch.returncode != 0:
            logger.warning(
                "Could not fetch base SHA %s for incremental diff (%s) — falling back to full ingest",
                base_sha[:8], fetch.stderr.strip(),
            )
            return None

        diff = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=AM", "FETCH_HEAD", "HEAD"],
            cwd=repo_dir, capture_output=True, text=True,
        )
        if diff.returncode != 0:
            logger.warning("git diff failed (%s) — falling back to full ingest", diff.stderr.strip())
            return None

        paths = [p.strip() for p in diff.stdout.splitlines() if p.strip()]
        logger.info("Incremental diff: %d file(s) changed since %s", len(paths), base_sha[:8])
        return paths

    def _collect_files(self, root: Path, allowed_paths: Optional[set[str]] = None) -> list[dict]:
        """
        Walk root and return [{path, content, is_test}] for matching files.
        If allowed_paths is given, only files whose relative path is in that set
        are returned (used for incremental ingest).
        """
        files = []
        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in DEFAULT_EXTENSIONS:
                continue

            rel = str(file_path.relative_to(root))

            if allowed_paths is not None and rel not in allowed_paths:
                continue
            if self._is_excluded(rel, file_path.name):
                continue
            if not self._in_configured_paths(rel):
                continue
            if file_path.stat().st_size > MAX_FILE_BYTES:
                logger.debug("Skipping %s — too large (%dKB)", rel, file_path.stat().st_size // 1024)
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                logger.warning("Could not read %s: %s", rel, e)
                continue

            if len(content.splitlines()) < MIN_FILE_LINES:
                logger.debug("Skipping %s — too few lines (%d)", rel, len(content.splitlines()))
                continue

            files.append({
                "path": rel,
                "content": content,
                "is_test": self._is_test_file(rel),
            })

        return files

    async def list_files(self) -> tuple[list[dict], str]:
        """
        Clone the repo and return (files, head_sha).

        files — [{path, content, is_test}] for all files to process.
                 Empty list means nothing changed since last ingest.
        head_sha — the current HEAD SHA; callers should persist this.
        """
        temp_dir = tempfile.mkdtemp(prefix="rulegraph_clone_")
        clone_url = self._auth_url()
        repo_dir = str(Path(temp_dir) / "repo")

        try:
            logger.info("Cloning %s branch=%s …", self.repo_url, self.branch)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._clone, clone_url, repo_dir)

            head_sha = await loop.run_in_executor(None, self._get_head_sha, repo_dir)
            logger.info("Clone complete — HEAD %s", head_sha[:8])

            # Incremental: try to limit to files changed since last ingest
            allowed_paths: Optional[set[str]] = None
            if self.last_commit_sha and self.last_commit_sha != head_sha:
                changed = await loop.run_in_executor(
                    None, self._get_changed_paths, repo_dir, clone_url, self.last_commit_sha
                )
                if changed is not None:
                    if not changed:
                        # No files changed — skip processing entirely
                        return [], head_sha
                    allowed_paths = set(changed)
            elif self.last_commit_sha == head_sha:
                logger.info("HEAD unchanged since last ingest (%s) — nothing to do", head_sha[:8])
                return [], head_sha

            root = Path(repo_dir)
            files = await loop.run_in_executor(
                None, self._collect_files, root, allowed_paths
            )

            mode = "incremental" if allowed_paths is not None else "full"
            logger.info("Found %d file(s) to process (%s)", len(files), mode)
            return files, head_sha

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def get_file_content(self, path: str) -> str:
        raise NotImplementedError("Use list_files() for bulk ingest")
