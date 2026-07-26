import asyncio
import json
from datetime import datetime, timezone
import httpx
from pywebpush import WebPushException, webpush
from sqlalchemy import select
from ..models import Customer, Notification, NotificationPreference, PushSubscription
from ..settings import settings


async def send_email(customer: Customer, notification: Notification) -> None:
    if not settings.brevo_api_key or not settings.brevo_sender_email:
        return
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": settings.brevo_api_key, "Content-Type": "application/json"},
            json={
                "sender": {"email": settings.brevo_sender_email, "name": settings.brevo_sender_name},
                "to": [{"email": customer.email, "name": f"{customer.first_name} {customer.last_name}".strip()}],
                "subject": notification.title,
                "htmlContent": f"<h1>{notification.title}</h1><p>{notification.body}</p>",
            },
        )
        response.raise_for_status()


async def send_push(subscription: PushSubscription, notification: Notification) -> bool:
    if not settings.vapid_private_key or not settings.vapid_subject:
        return True
    payload = json.dumps({
        "title": notification.title, "body": notification.body,
        "url": notification.data.get("url", "/account/notifications"),
        "tag": f"cakecity-{notification.order_id or notification.id}",
    })
    try:
        await asyncio.to_thread(
            webpush,
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=payload,
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
            ttl=86400,
        )
        return True
    except WebPushException as exc:
        if getattr(exc.response, "status_code", None) in (404, 410):
            return False
        raise


async def dispatch_notification(db, notification: Notification) -> None:
    customer = await db.get(Customer, notification.customer_id)
    prefs = await db.get(NotificationPreference, notification.customer_id)
    email_enabled = prefs.email if prefs else True
    push_enabled = prefs.push if prefs else False
    if email_enabled:
        await send_email(customer, notification)
    if push_enabled:
        subscriptions = (await db.scalars(select(PushSubscription).where(
            PushSubscription.customer_id == notification.customer_id,
            PushSubscription.revoked_at.is_(None),
        ))).all()
        for subscription in subscriptions:
            if not await send_push(subscription, notification):
                subscription.revoked_at = datetime.now(timezone.utc)
