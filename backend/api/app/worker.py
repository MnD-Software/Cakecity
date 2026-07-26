import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from sqlalchemy import or_, select
from .database import SessionFactory
from .models import Notification, Order, OrderLine, OutboxEvent, PaymentEvent, PaymentIntent, Product, WebhookEvent
from .services.flutterwave import FlutterwaveClient, verified_flutterwave_payment
from .services.order_tracking import append_stage, stage_from_woo, woo_meta
from .services.synchronizer import upsert_product
from .services.notifications import dispatch_notification
from .services.woocommerce import WooCommerceClient
from .settings import settings


async def claim_event(db) -> OutboxEvent | None:
    now = datetime.now(timezone.utc)
    event = await db.scalar(
        select(OutboxEvent).where(
            or_(
                OutboxEvent.state.in_(("pending", "retry")),
                (OutboxEvent.state == "processing") & (OutboxEvent.available_at <= now),
            ),
            OutboxEvent.available_at <= now,
        ).order_by(OutboxEvent.created_at).with_for_update(skip_locked=True).limit(1)
    )
    if not event:
        return None
    event.state = "processing"
    event.attempts += 1
    event.available_at = now + timedelta(minutes=5)
    await db.commit()
    return event


async def claim_webhook(db) -> WebhookEvent | None:
    event = await db.scalar(select(WebhookEvent).where(
        WebhookEvent.state.in_(("received", "retry")),
    ).order_by(WebhookEvent.received_at).with_for_update(skip_locked=True).limit(1))
    if not event:
        return None
    event.state = "processing"
    event.attempts += 1
    await db.commit()
    return event


async def mark_payment_confirmed(db, intent: PaymentIntent, provider_payload: dict) -> None:
    if intent.state == "paid":
        return
    intent.state = "paid"
    intent.paid_at = datetime.now(timezone.utc)
    intent.provider_payload = {**intent.provider_payload, **provider_payload}
    order = await db.get(Order, intent.order_id)
    order.state = "paid"
    existing = await db.scalar(select(OutboxEvent.id).where(
        OutboxEvent.aggregate_id == order.id, OutboxEvent.topic == "order.payment_confirmed"
    ))
    if not existing:
        db.add(OutboxEvent(
            aggregate_type="order", aggregate_id=order.id, topic="order.payment_confirmed",
            payload={"order_id": str(order.id), "payment_intent_id": str(intent.id)},
        ))


async def verify_flutterwave(db, event: OutboxEvent) -> None:
    payment_event = await db.get(PaymentEvent, UUID(event.payload["event_id"]))
    data = payment_event.payload.get("data", {})
    transaction_id = str(data.get("id", ""))
    reference = str(data.get("tx_ref") or data.get("reference") or "")
    order = await db.scalar(select(Order).where(Order.reference == reference))
    if not transaction_id or not order:
        payment_event.state = "ignored"
        payment_event.processed_at = datetime.now(timezone.utc)
        return
    intent = await db.scalar(select(PaymentIntent).where(
        PaymentIntent.order_id == order.id, PaymentIntent.provider == "flutterwave"
    ))
    client = FlutterwaveClient(settings.flutterwave_base_url, settings.flutterwave_secret_key)
    verified = await client.verify_transaction(transaction_id)
    if not verified_flutterwave_payment(verified, order.reference, Decimal(intent.amount), intent.currency):
        intent.state = "review_required"
        intent.failure_code = "verification_mismatch"
        intent.failure_message = "Flutterwave verification did not match the expected payment"
    else:
        await mark_payment_confirmed(db, intent, {"transaction_id": transaction_id, "verification": verified})
    payment_event.state = "processed"
    payment_event.processed_at = datetime.now(timezone.utc)


def build_woo_order_payload(order: Order, lines: list[OrderLine], intent: PaymentIntent) -> dict:
    address = order.delivery_address or {}
    transaction_id = str(
        intent.provider_payload.get("callback", {}).get("receipt")
        or intent.provider_payload.get("transaction_id") or intent.provider_reference
    )
    return {
        "status": "processing", "set_paid": True,
        "payment_method": intent.method,
        "payment_method_title": "M-Pesa" if intent.method == "mpesa" else "Card",
        "transaction_id": transaction_id,
        "billing": {
            "first_name": order.customer_name, "email": order.customer_email,
            "phone": order.customer_phone, "address_1": address.get("line1", ""),
            "city": address.get("city", "Nairobi"),
        },
        "shipping": {
            "first_name": order.customer_name, "address_1": address.get("line1", ""),
            "city": address.get("city", "Nairobi"),
        },
        "line_items": [{
            "product_id": line.woo_product_id, "quantity": line.quantity,
            "total": str(line.line_total),
            "meta_data": [{"key": key, "value": value} for key, value in line.configuration.items()],
        } for line in lines],
        "shipping_lines": ([{
            "method_id": "cakecity_delivery", "method_title": "Scheduled delivery",
            "total": str(order.delivery_fee),
        }] if order.fulfilment == "delivery" else []),
        "customer_note": f"Delivery slot: {order.delivery_slot or 'not selected'}",
        "meta_data": [
            {"key": "_cakecity_reference", "value": order.reference},
            {"key": "_cakecity_fulfilment", "value": order.fulfilment},
            {"key": "_cakecity_delivery_slot", "value": order.delivery_slot or ""},
        ],
    }


async def create_woocommerce_order(db, event: OutboxEvent) -> None:
    order = await db.get(Order, UUID(event.payload["order_id"]))
    if order.woo_id:
        return
    lines = list((await db.scalars(select(OrderLine).where(OrderLine.order_id == order.id))).all())
    intent = await db.scalar(select(PaymentIntent).where(
        PaymentIntent.order_id == order.id, PaymentIntent.state == "paid"
    ))
    client = WooCommerceClient(
        settings.woocommerce_url, settings.woocommerce_consumer_key, settings.woocommerce_consumer_secret
    )
    woo = await client.create_paid_order({
        "reference": order.reference,
        "order": build_woo_order_payload(order, lines, intent),
    })
    order.woo_id = int(woo["id"])
    await append_stage(db, order, "received", f"payment:{intent.id}", "payment")
    await append_stage(db, order, "confirmed", f"woo-created:{order.woo_id}", "woocommerce")


async def process_woo_webhook(event: WebhookEvent) -> None:
    async with SessionFactory() as db:
        attached = await db.get(WebhookEvent, event.id)
        try:
            resource = attached.resource.lower()
            topic = attached.topic.lower()
            if resource == "product":
                if topic.endswith(".deleted"):
                    product = await db.scalar(select(Product).where(Product.woo_id == int(attached.payload["id"])))
                    if product:
                        product.status = "deleted"
                        product.in_stock = False
                else:
                    await upsert_product(db, attached.payload)
            elif resource == "order":
                reference = woo_meta(attached.payload, "_cakecity_reference")
                order = await db.scalar(select(Order).where(
                    or_(
                        Order.woo_id == int(attached.payload.get("id", 0)),
                        Order.reference == reference if reference else False,
                    )
                ))
                stage = stage_from_woo(attached.payload)
                if order and stage:
                    order.woo_id = order.woo_id or int(attached.payload["id"])
                    await append_stage(
                        db, order, stage, f"woo-webhook:{attached.delivery_key}",
                        "woocommerce", metadata={"woo_status": attached.payload.get("status")},
                    )
            attached.state = "processed"
            attached.processed_at = datetime.now(timezone.utc)
            attached.error = None
        except Exception as exc:
            attached.state = "dead" if attached.attempts >= 8 else "retry"
            attached.error = str(exc)[:2000]
        await db.commit()


async def process(event: OutboxEvent) -> None:
    async with SessionFactory() as db:
        attached = await db.get(OutboxEvent, event.id)
        try:
            if attached.topic == "payment.verify_flutterwave":
                await verify_flutterwave(db, attached)
            elif attached.topic == "order.payment_confirmed":
                await create_woocommerce_order(db, attached)
            elif attached.topic == "notification.dispatch":
                notification = await db.get(Notification, UUID(attached.payload["notification_id"]))
                if notification:
                    await dispatch_notification(db, notification)
            attached.state = "processed"
            attached.processed_at = datetime.now(timezone.utc)
            attached.last_error = None
        except Exception as exc:
            attached.state = "dead" if attached.attempts >= 8 else "retry"
            attached.last_error = str(exc)[:2000]
            attached.available_at = datetime.now(timezone.utc) + timedelta(seconds=min(3600, 2 ** attached.attempts * 15))
        await db.commit()


async def run() -> None:
    while True:
        async with SessionFactory() as db:
            event = await claim_event(db)
            webhook = None if event else await claim_webhook(db)
        if event:
            await process(event)
        elif webhook:
            await process_woo_webhook(webhook)
        else:
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(run())
