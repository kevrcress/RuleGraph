#!/usr/bin/env python3
"""
Ingest a local or remote git repository into RuleGraph.

Usage:
    # From a local clone
    python scripts/ingest_repo.py \
        --path /path/to/your/repo \
        --source my-service \
        --token <admin-jwt>

    # Clone then ingest (public repo)
    python scripts/ingest_repo.py \
        --clone https://github.com/org/repo \
        --source my-service \
        --token <admin-jwt>

    # Clone private repo with PAT
    python scripts/ingest_repo.py \
        --clone https://github.com/org/repo \
        --git-token ghp_xxx \
        --source my-service \
        --token <admin-jwt>

Get your admin JWT:
    curl -s -X POST http://localhost:8000/auth/login \\
      -H "Content-Type: application/json" \\
      -d '{"email":"admin@test.com","password":"Test1234!"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])"
"""

import argparse
import fnmatch
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_EXTENSIONS = {
    ".cs", ".py", ".ts", ".tsx", ".js", ".jsx",
    ".java", ".go", ".rb", ".rs", ".kt", ".swift",
    ".php", ".scala", ".clj", ".ex", ".exs",
    ".md", ".txt",
}

DEFAULT_EXCLUDE = [
    # Build artifacts / deps
    "**/node_modules/**", "**/obj/**", "**/bin/**",
    "**/.git/**", "**/__pycache__/**", "**/.mypy_cache/**",
    "**/dist/**", "**/build/**", "**/.next/**",
    # Migrations (schema, not business logic)
    "**/migrations/**", "**/Migrations/**",
    # Lock / config files
    "**/*.lock", "**/package-lock.json",
    # Test files (we want to ingest these separately for coverage mapping)
    # — not excluded here so RuleGraph can map test coverage
]

# Files above this size (bytes) are skipped — avoids feeding massive generated files
MAX_FILE_BYTES = 200_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_excluded(path: Path, root: Path, patterns: list[str]) -> bool:
    rel = str(path.relative_to(root))
    for pat in patterns:
        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(path.name, pat):
            return True
    return False


def collect_files(root: Path, extensions: set[str], exclude: list[str]) -> list[Path]:
    files = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in extensions:
            continue
        if is_excluded(p, root, exclude):
            continue
        if p.stat().st_size > MAX_FILE_BYTES:
            print(f"  skip (too large, {p.stat().st_size // 1024}KB): {p.relative_to(root)}")
            continue
        files.append(p)
    return sorted(files)


def login(api: str, email: str, password: str) -> str:
    r = httpx.post(f"{api}/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def ingest_file(api: str, token: str, path: Path, source_name: str) -> dict:
    with open(path, "rb") as f:
        content = f.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1", errors="replace")

    r = httpx.post(
        f"{api}/ingest/file",
        params={"source_name": source_name},
        files={"file": (path.name, text.encode("utf-8"), "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )
    return r.json() if r.status_code == 200 else {"error": r.text, "status": r.status_code}


def clone_repo(url: str, git_token: str | None, dest: Path) -> None:
    if git_token:
        # Inject token into URL for private repos
        # https://github.com/org/repo → https://token@github.com/org/repo
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        authed = parsed._replace(netloc=f"{git_token}@{parsed.netloc}")
        clone_url = urlunparse(authed)
    else:
        clone_url = url

    print(f"Cloning {url} …")
    result = subprocess.run(
        ["git", "clone", "--depth=1", clone_url, str(dest)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"git clone failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(f"Cloned to {dest}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a git repo into RuleGraph")

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--path", metavar="DIR",
                               help="Path to an already-cloned local repo")
    source_group.add_argument("--clone", metavar="URL",
                               help="Git URL to clone (creates a temp dir)")

    parser.add_argument("--git-token", metavar="PAT",
                         help="GitHub/ADO PAT for private repo clone")
    parser.add_argument("--source", required=True,
                         help="Service name to tag rules with (e.g. 'ordering-service')")
    parser.add_argument("--api", default="http://localhost:8000",
                         help="RuleGraph API base URL (default: http://localhost:8000)")

    auth_group = parser.add_mutually_exclusive_group(required=True)
    auth_group.add_argument("--token", metavar="JWT",
                             help="Admin JWT access token")
    auth_group.add_argument("--login", nargs=2, metavar=("EMAIL", "PASSWORD"),
                             help="Email + password to get a token automatically")

    parser.add_argument("--ext", nargs="+", metavar="EXT",
                         help=f"File extensions to include (default: {' '.join(sorted(DEFAULT_EXTENSIONS))})")
    parser.add_argument("--exclude", nargs="+", metavar="GLOB",
                         help="Additional glob patterns to exclude")
    parser.add_argument("--dry-run", action="store_true",
                         help="List files that would be ingested without sending them")
    parser.add_argument("--delay", type=float, default=0.5,
                         help="Seconds between requests (default: 0.5)")

    args = parser.parse_args()

    # --- Auth ---
    if args.token:
        token = args.token
    else:
        email, password = args.login
        print(f"Logging in as {email} …")
        try:
            token = login(args.api, email, password)
            print("Login OK")
        except Exception as e:
            print(f"Login failed: {e}", file=sys.stderr)
            sys.exit(1)

    # --- Source path ---
    temp_dir = None
    if args.clone:
        temp_dir = tempfile.mkdtemp(prefix="rulegraph_clone_")
        repo_path = Path(temp_dir) / "repo"
        try:
            clone_repo(args.clone, args.git_token, repo_path)
        except SystemExit:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise
    else:
        repo_path = Path(args.path).expanduser().resolve()
        if not repo_path.is_dir():
            print(f"Path not found: {repo_path}", file=sys.stderr)
            sys.exit(1)

    try:
        extensions = {e if e.startswith(".") else f".{e}" for e in (args.ext or DEFAULT_EXTENSIONS)}
        exclude = DEFAULT_EXCLUDE + (args.exclude or [])

        print(f"\nScanning {repo_path} …")
        files = collect_files(repo_path, extensions, exclude)
        print(f"Found {len(files)} file(s) to ingest\n")

        if args.dry_run:
            for f in files:
                print(f"  {f.relative_to(repo_path)}")
            print(f"\nDry run — {len(files)} file(s) would be sent to {args.api}")
            return

        total_rules = 0
        errors = 0

        for i, fpath in enumerate(files, 1):
            rel = fpath.relative_to(repo_path)
            print(f"[{i}/{len(files)}] {rel} … ", end="", flush=True)

            result = ingest_file(args.api, token, fpath, args.source)

            if "error" in result:
                print(f"ERROR ({result.get('status', '?')}): {result['error'][:120]}")
                errors += 1
            else:
                n = result.get("rules_extracted", 0)
                total_rules += n
                print(f"{n} rule(s) extracted")

            if i < len(files) and args.delay > 0:
                time.sleep(args.delay)

        print(f"\n{'='*60}")
        print(f"Done.")
        print(f"  Files processed : {len(files)}")
        print(f"  Rules extracted : {total_rules}")
        print(f"  Errors          : {errors}")
        print(f"  Source label    : {args.source}")
        print(f"\nView results at {args.api.replace('8000', '5173')}/rules")

    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
