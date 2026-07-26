from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import current_customer
from ..database import session
from ..models import Customer, Notification, NotificationPreference, PushSubscription
from ..settings import settings

router = APIRouter(prefix="/v1/account/notifications", tags=["notifications"])


class PreferenceInput(BaseModel):
    in_app: bool = True
    email: bool = True
    push: bool = False
    sms: bool = False
    whatsapp: bool = False


class SubscriptionInput(BaseModel):
    endpoint: str = Field(min_length=20, max_length=5000)
    keys: dict[str, str]


async def preference(db: AsyncSession, customer_id: UUID) -> NotificationPreference:
    item = await db.get(NotificationPreference, customer_id)
    if not item:
        item = NotificationPreference(customer_id=customer_id)
        db.add(item)
        await db.flush()
    return item


@router.get("")
async def list_notifications(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    items = (await db.scalars(select(Notification).where(
        Notification.customer_id == customer.id,
    ).order_by(Notification.created_at.desc()).limit(100))).all()
    return [{
        "id": str(item.id), "kind": item.kind, "title": item.title, "body": item.body,
        "data": item.data, "read_at": item.read_at, "created_at": item.created_at,
    } for item in items]


@router.post("/{notification_id}/read", status_code=204)
async def mark_read(notification_id: UUID, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    item = await db.scalar(select(Notification).where(
        Notification.id == notification_id, Notification.customer_id == customer.id,
    ))
    if not item:
        raise HTTPException(status_code=404, detail="Notification not found")
    item.read_at = datetime.now(timezone.utc)
    await db.commit()


@router.get("/preferences")
async def get_preferences(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    item = await preference(db, customer.id)
    await db.commit()
    return {key: getattr(item, key) for key in PreferenceInput.model_fields}


@router.put("/preferences")
async def update_preferences(payload: PreferenceInput, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    item = await preference(db, customer.id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    await db.commit()
    return payload


@router.get("/push/config")
async def push_config():
    return {"enabled": bool(settings.vapid_public_key), "public_key": settings.vapid_public_key}


@router.post("/push/subscriptions", status_code=201)
async def subscribe(payload: SubscriptionInput, request: Request, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    p256dh, auth = payload.keys.get("p256dh"), payload.keys.get("auth")
    if not p256dh or not auth:
        raise HTTPException(status_code=422, detail="Push subscription keys are required")
    item = await db.scalar(select(PushSubscription).where(PushSubscription.endpoint == payload.endpoint))
    if item:
        item.customer_id, item.p256dh, item.auth, item.revoked_at = customer.id, p256dh, auth, None
    else:
        db.add(PushSubscription(
            customer_id=customer.id, endpoint=payload.endpoint, p256dh=p256dh, auth=auth,
            user_agent=request.headers.get("user-agent"),
        ))
    prefs = await preference(db, customer.id)
    prefs.push = True
    await db.commit()
    return {"subscribed": True}


@router.delete("/push/subscriptions", status_code=204)
async def unsubscribe(payload: SubscriptionInput, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    item = await db.scalar(select(PushSubscription).where(
        PushSubscription.endpoint == payload.endpoint, PushSubscription.customer_id == customer.id,
    ))
    if item:
        item.revoked_at = datetime.now(timezone.utc)
        await db.commit()
