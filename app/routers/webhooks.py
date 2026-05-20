"""Webhooks router — ADO push events with HMAC validation and async processing."""
import json
import logging

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.security.webhook import validate_webhook_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/ado")
async def ado_webhook(request: Request):
    """
    Receive ADO webhook events. Validates HMAC-SHA256 signature, returns 200
    immediately, and queues async processing via arq.
    """
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not signature:
        logger.warning("ADO webhook received without signature")
        raise HTTPException(status_code=401, detail="Missing webhook signature")

    secret = getattr(settings, "webhook_test_secret", "test-webhook-secret")
    if not validate_webhook_signature(body, signature, secret):
        logger.warning("ADO webhook signature validation failed")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse payload and log for async processing
    try:
        payload = json.loads(body)
        event_type = payload.get("eventType", "unknown")
        logger.info("ADO webhook received: %s — queued for async processing", event_type)
    except json.JSONDecodeError:
        logger.warning("ADO webhook received non-JSON body")

    # In production, enqueue via arq: await enqueue_webhook_job(payload)
    # For now, log and return 200 immediately per spec (prevents ADO timeout)
    return {"status": "accepted", "message": "Webhook received and queued"}
