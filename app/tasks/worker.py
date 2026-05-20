"""arq task worker — async job processing for webhook events and background tasks."""
import logging

logger = logging.getLogger(__name__)


async def process_ado_webhook(ctx, payload: dict) -> None:
    """Process an ADO webhook event asynchronously."""
    event_type = payload.get("eventType", "unknown")
    resource = payload.get("resource", {})
    logger.info("Processing ADO webhook event: %s", event_type)

    if event_type == "git.push":
        repo = resource.get("repository", {}).get("name", "unknown")
        logger.info("ADO push to repo: %s — triggering ingest", repo)
        # TODO: trigger targeted ingest for the affected repo


class WorkerSettings:
    """arq worker configuration."""
    functions = [process_ado_webhook]
    queue_name = "rulegraph:tasks"
    max_jobs = 10
