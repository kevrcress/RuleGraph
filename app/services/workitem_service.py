"""Work item creation via ADO REST API and GitHub Issues API per Section 17."""
import logging
import uuid
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


async def create_ado_work_item(
    org: str,
    project: str,
    pat: str,
    title: str,
    description: str,
    rule_url: str,
) -> tuple[str, str]:
    """Create an ADO story. Returns (work_item_id, work_item_url)."""
    url = f"https://dev.azure.com/{org}/{project}/_apis/wit/workitems/$Story?api-version=7.1"
    headers = {
        "Content-Type": "application/json-patch+json",
    }
    body = [
        {"op": "add", "path": "/fields/System.Title", "value": title},
        {"op": "add", "path": "/fields/System.Description", "value": f"{description}\n\nRule: {rule_url}"},
    ]
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=body, headers=headers, auth=("", pat), timeout=10.0)
        r.raise_for_status()
        data = r.json()
        item_id = str(data["id"])
        item_url = data["_links"]["html"]["href"]
        return item_id, item_url


async def create_github_issue(
    owner: str,
    repo: str,
    token: str,
    title: str,
    body: str,
    rule_url: str,
) -> tuple[str, str]:
    """Create a GitHub issue. Returns (issue_number_str, issue_url)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {"title": title, "body": f"{body}\n\nRule: {rule_url}"}
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload, headers=headers, timeout=10.0)
        r.raise_for_status()
        data = r.json()
        issue_id = str(data["number"])
        issue_url = data["html_url"]
        return issue_id, issue_url


async def create_work_item(
    rule_id: uuid.UUID,
    title: str,
    body: str,
    repo: Optional[str],
    project: Optional[str],
    connected_accounts: list,
    base_url: str = "https://rulegraph.company.com",
) -> tuple[str, str]:
    """
    Attempt to create a work item using the TL's connected accounts.
    Falls back to a placeholder ID/URL if no connected accounts are available.
    """
    rule_url = f"{base_url}/rules/{rule_id}"

    for account in connected_accounts:
        try:
            if account.provider == "ado" and account.org and repo and project:
                from app.security.encryption import decrypt_secret
                pat = decrypt_secret(account.pat_encrypted)
                return await create_ado_work_item(account.org, project, pat, title, body, rule_url)
            elif account.provider == "github" and account.org and repo:
                from app.security.encryption import decrypt_secret
                token = decrypt_secret(account.pat_encrypted)
                return await create_github_issue(account.org, repo, token, title, body, rule_url)
        except Exception as exc:
            logger.warning("Work item creation failed via %s: %s", account.provider, exc)

    # No connected accounts or all failed — return a placeholder
    placeholder_id = f"local-{rule_id!s:.8}"
    placeholder_url = rule_url
    logger.warning("No connected accounts available; using placeholder work item ID %s", placeholder_id)
    return placeholder_id, placeholder_url
