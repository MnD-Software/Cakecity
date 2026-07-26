import hashlib
import json
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import session
from ..models import WebhookEvent
from ..schemas import WebhookReceipt
from ..security import delivery_key, verify_webhook_signature
from ..settings import settings

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


@router.post("/woocommerce", response_model=WebhookReceipt, status_code=status.HTTP_202_ACCEPTED)
async def woo_webhook(
    request: Request,
    signature: str | None = Header(None, alias="X-WC-Webhook-Signature"),
    webhook_id: str = Header(..., alias="X-WC-Webhook-ID"),
    topic: str = Header(..., alias="X-WC-Webhook-Topic"),
    resource: str = Header(..., alias="X-WC-Webhook-Resource"),
    db: AsyncSession = Depends(session),
):
    body = await request.body()
    if len(body) > 2_000_000:
        raise HTTPException(status_code=413, detail="Webhook payload too large")
    if not verify_webhook_signature(body, signature, settings.woocommerce_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc
    key = delivery_key(webhook_id, topic, body)
    if await db.scalar(select(WebhookEvent.id).where(WebhookEvent.delivery_key == key)):
        return WebhookReceipt(accepted=True, duplicate=True, delivery_key=key)
    db.add(WebhookEvent(
        webhook_id=webhook_id, delivery_key=key, topic=topic, resource=resource,
        payload=payload, payload_hash=hashlib.sha256(body).hexdigest(),
    ))
    await db.commit()
    # The durable event is committed before a worker notification is published.
    return WebhookReceipt(accepted=True, duplicate=False, delivery_key=key)
