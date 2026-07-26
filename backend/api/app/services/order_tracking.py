from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Notification, Order, OrderTimelineEvent, OutboxEvent

STAGES = (
    "received", "confirmed", "baking", "decorating", "quality_check",
    "packaging", "driver_assigned", "out_for_delivery", "delivered",
)

STAGE_COPY = {
    "received": ("Order received", "Payment is confirmed and your celebration is in our care."),
    "confirmed": ("Kitchen confirmed", "The Cake City kitchen has accepted your order."),
    "baking": ("Freshly baking", "Your cake is now being baked by our pastry team."),
    "decorating": ("Finishing the details", "Our decorators are bringing your design to life."),
    "quality_check": ("Quality check", "We are checking every finish, detail and instruction."),
    "packaging": ("Carefully packaged", "Your cake is being secured for collection or delivery."),
    "driver_assigned": ("Courier assigned", "A delivery partner has been assigned to your order."),
    "out_for_delivery": ("On its way", "Your celebration has left Cake City."),
    "delivered": ("Delivered", "Your order has arrived. We hope the moment is wonderful."),
}

WOO_STATUS_STAGE = {
    "pending": "received", "on-hold": "received", "processing": "confirmed",
    "cakecity-baking": "baking", "cakecity-decorating": "decorating",
    "cakecity-quality": "quality_check", "cakecity-packaging": "packaging",
    "cakecity-driver": "driver_assigned", "cakecity-out": "out_for_delivery",
    "completed": "delivered",
}


def woo_meta(payload: dict, key: str) -> str | None:
    for item in payload.get("meta_data", []):
        if item.get("key") == key:
            return str(item.get("value") or "") or None
    return None


def stage_from_woo(payload: dict) -> str | None:
    explicit = woo_meta(payload, "_cakecity_stage")
    return explicit if explicit in STAGES else WOO_STATUS_STAGE.get(str(payload.get("status", "")))


async def append_stage(
    db: AsyncSession, order: Order, stage: str, source_event_key: str,
    source: str = "platform", detail: str | None = None, metadata: dict | None = None,
) -> bool:
    if stage not in STAGES:
        return False
    if order.state in STAGES and STAGES.index(stage) < STAGES.index(order.state):
        return False
    if await db.scalar(select(OrderTimelineEvent.id).where(
        OrderTimelineEvent.order_id == order.id,
        OrderTimelineEvent.source_event_key == source_event_key,
    )):
        return False
    title, default_detail = STAGE_COPY[stage]
    db.add(OrderTimelineEvent(
        order_id=order.id, stage=stage, title=title, detail=detail or default_detail,
        source=source, source_event_key=source_event_key, event_metadata=metadata or {},
    ))
    order.state = stage
    if order.customer_id:
        notification = Notification(
            customer_id=order.customer_id, order_id=order.id, kind="order_update",
            title=title, body=detail or default_detail,
            data={"reference": order.reference, "stage": stage, "url": f"/account/orders/{order.reference}"},
        )
        db.add(notification)
        await db.flush()
        db.add(OutboxEvent(
            aggregate_type="notification", aggregate_id=notification.id,
            topic="notification.dispatch",
            payload={"notification_id": str(notification.id)},
        ))
    return True
