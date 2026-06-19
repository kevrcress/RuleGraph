"""Unit test for GitHubRepoConnector skip_paths (DEC-045 follow-up / IV-023).

On resume, already-done files are passed as skip_paths so the connector skips reading
their content into memory. Exercises _collect_files directly against a temp tree — no
network/clone needed.
"""
import tempfile
from pathlib import Path

from app.ingest.connectors.github_repo import GitHubRepoConnector


def _write(root: Path, rel: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    # ≥5 lines of business-ish logic so MIN_FILE_LINES doesn't filter it out.
    p.write_text(
        "def handler(order):\n"
        "    if order.total > 0:\n"
        "        return True\n"
        "    # business rule\n"
        "    return False\n",
        encoding="utf-8",
    )


def test_skip_paths_excludes_done_files_from_collection():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root, "src/a/one.py")
        _write(root, "src/b/two.py")
        _write(root, "src/c/three.py")

        # Skip the first file (simulating an already-done checkpoint on resume).
        connector = GitHubRepoConnector(
            repo_url="https://example.com/r.git",
            skip_paths={"src/a/one.py"},
        )
        collected = {f["path"] for f in connector._collect_files(root)}

        assert "src/a/one.py" not in collected, "skip_paths file must not be collected"
        assert collected == {"src/b/two.py", "src/c/three.py"}


def test_no_skip_paths_collects_everything():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root, "src/a/one.py")
        _write(root, "src/b/two.py")

        connector = GitHubRepoConnector(repo_url="https://example.com/r.git")
        collected = {f["path"] for f in connector._collect_files(root)}

        assert collected == {"src/a/one.py", "src/b/two.py"}
