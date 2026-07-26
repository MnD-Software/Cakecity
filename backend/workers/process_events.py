"""Durable webhook event processor.

Run under Celery in production. The processing body is intentionally framework-neutral
so redeliveries can be tested and the database remains the source of processing state.
"""
from datetime import datetime, timezone
from sqlalchemy import select
from backend.api.app.models import WebhookEvent
from backend.api.app.services.synchronizer import upsert_product


async def process_next_product_event(db) -> bool:
    event = await db.scalar(
        select(WebhookEvent)
        .where(WebhookEvent.state.in_(("received", "retry")), WebhookEvent.resource == "product")
        .order_by(WebhookEvent.received_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if not event:
        return False
    event.state = "processing"
    event.attempts += 1
    try:
        if event.topic.endswith(".deleted"):
            # Deletions are soft: unavailable products disappear from browsing without losing order history.
            from sqlalchemy import update
            from backend.api.app.models import Product
            await db.execute(update(Product).where(Product.woo_id == int(event.payload["id"])).values(status="trash", in_stock=False))
        else:
            await upsert_product(db, event.payload)
        event.state = "processed"
        event.processed_at = datetime.now(timezone.utc)
        event.error = None
    except Exception as exc:
        event.state = "dead" if event.attempts >= 8 else "retry"
        event.error = str(exc)[:2000]
    await db.commit()
    return True
