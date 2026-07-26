import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import optional_customer
from ..database import session
from ..models import Customer, Order, OrderLine, OutboxEvent, PaymentEvent, PaymentIntent
from ..settings import settings
from ..services.flutterwave import FlutterwaveClient, verify_flutterwave_signature
from ..services.mpesa import MpesaClient, normalize_kenyan_phone, parse_stk_callback
from .checkout import CheckoutQuoteInput, price_checkout

router = APIRouter(prefix="/v1/payments", tags=["payments"])


class PaymentCustomer(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    phone: str = Field(min_length=9, max_length=32)
    name: str = Field(min_length=2, max_length=240)


class DeliveryAddress(BaseModel):
    line1: str = Field(min_length=3, max_length=260)
    area: str = Field(min_length=2, max_length=160)
    city: str = Field(default="Nairobi", max_length=120)
    notes: str | None = Field(default=None, max_length=500)


class PaymentIntentInput(BaseModel):
    method: Literal["mpesa", "card"]
    checkout: CheckoutQuoteInput
    customer: PaymentCustomer
    delivery_address: DeliveryAddress | None = None


class PaymentAction(BaseModel):
    type: Literal["await_mpesa", "redirect", "none"]
    redirect_url: str | None = None
    message: str | None = None


class PaymentIntentRead(BaseModel):
    id: UUID
    order_reference: str
    state: str
    method: str
    amount: Decimal
    currency: str
    client_secret: str
    action: PaymentAction


class PaymentStatusRead(BaseModel):
    id: UUID
    order_reference: str
    state: str
    amount: Decimal
    currency: str
    failure_message: str | None


def intent_secret(idempotency_key: str) -> str:
    return hmac.new(settings.jwt_secret.encode(), f"payment:{idempotency_key}".encode(), hashlib.sha256).hexdigest()


def action_for(intent: PaymentIntent) -> PaymentAction:
    if intent.method == "card" and intent.provider_payload.get("redirect_url"):
        return PaymentAction(type="redirect", redirect_url=intent.provider_payload["redirect_url"])
    if intent.method == "mpesa" and intent.state in {"created", "pending"}:
        return PaymentAction(type="await_mpesa", message="Check your phone and enter your M-Pesa PIN.")
    return PaymentAction(type="none")


async def response_for(intent: PaymentIntent, order: Order) -> PaymentIntentRead:
    secret = intent_secret(intent.idempotency_key)
    return PaymentIntentRead(
        id=intent.id, order_reference=order.reference, state=intent.state,
        method=intent.method, amount=intent.amount, currency=intent.currency,
        client_secret=secret, action=action_for(intent),
    )


@router.post("/intents", response_model=PaymentIntentRead, status_code=201)
async def create_payment_intent(
    payload: PaymentIntentInput,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=16, max_length=180),
    customer: Customer | None = Depends(optional_customer),
    db: AsyncSession = Depends(session),
):
    existing = await db.scalar(select(PaymentIntent).where(PaymentIntent.idempotency_key == idempotency_key))
    if existing:
        order = await db.get(Order, existing.order_id)
        return await response_for(existing, order)
    if payload.method == "mpesa" and not all((
        settings.mpesa_consumer_key, settings.mpesa_consumer_secret, settings.mpesa_shortcode,
        settings.mpesa_passkey, settings.mpesa_callback_secret,
    )):
        raise HTTPException(status_code=503, detail="M-Pesa is not configured")
    if payload.method == "card" and not all((
        settings.flutterwave_secret_key, settings.flutterwave_webhook_secret,
    )):
        raise HTTPException(status_code=503, detail="Card payments are not configured")
    if payload.checkout.fulfilment == "delivery" and not payload.delivery_address:
        raise HTTPException(status_code=422, detail="Delivery address is required")

    quote, priced = await price_checkout(payload.checkout, db)
    reference = f"CC-{uuid4().hex[:12].upper()}"
    order = Order(
        reference=reference, customer_id=customer.id if customer else None,
        customer_email=payload.customer.email.strip().lower(),
        customer_phone=payload.customer.phone, customer_name=payload.customer.name.strip(),
        subtotal=quote.subtotal, delivery_fee=quote.delivery_fee, discount=quote.discount,
        total=quote.total, fulfilment=quote.fulfilment,
        delivery_slot=payload.checkout.delivery_slot,
        delivery_address=payload.delivery_address.model_dump() if payload.delivery_address else {},
    )
    db.add(order)
    await db.flush()
    for item in priced:
        db.add(OrderLine(
            order_id=order.id, product_id=item.product.id, woo_product_id=item.product.woo_id,
            product_name=item.product.name, quantity=item.requested.quantity,
            unit_price=item.unit_price, line_total=item.line_total,
            configuration={
                "size": item.requested.size, "message": item.requested.message,
                "add_ons": item.requested.add_ons,
            },
        ))
    secret = intent_secret(idempotency_key)
    intent = PaymentIntent(
        order_id=order.id, idempotency_key=idempotency_key,
        client_secret_hash=hashlib.sha256(secret.encode()).hexdigest(),
        method=payload.method, provider="safaricom" if payload.method == "mpesa" else "flutterwave",
        amount=quote.total, currency=quote.currency,
    )
    db.add(intent)
    await db.commit()

    try:
        if payload.method == "mpesa":
            phone = normalize_kenyan_phone(payload.customer.phone)
            client = MpesaClient(
                settings.mpesa_base_url, settings.mpesa_consumer_key, settings.mpesa_consumer_secret,
                settings.mpesa_shortcode, settings.mpesa_passkey,
            )
            callback = f"{settings.public_api_url.rstrip('/')}/v1/payments/callbacks/mpesa/{settings.mpesa_callback_secret}"
            provider = await client.stk_push(quote.total, phone, reference, callback)
            intent.provider_reference = provider["CheckoutRequestID"]
            intent.merchant_request_id = provider.get("MerchantRequestID")
            intent.provider_payload = {"customer_message": provider.get("CustomerMessage", "")}
        else:
            client = FlutterwaveClient(settings.flutterwave_base_url, settings.flutterwave_secret_key)
            redirect = f"{settings.storefront_url.rstrip('/')}/checkout/payment-return"
            link = await client.create_checkout(
                reference, quote.total, payload.customer.email, payload.customer.phone,
                payload.customer.name, redirect,
            )
            intent.provider_reference = reference
            intent.provider_payload = {"redirect_url": link}
        intent.state = "pending"
        await db.commit()
    except (ValueError, RuntimeError, httpx.HTTPError) as exc:
        intent.state = "failed"
        intent.failure_code = "provider_unavailable"
        intent.failure_message = str(exc)[:500]
        await db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return await response_for(intent, order)


@router.get("/intents/{intent_id}", response_model=PaymentStatusRead)
async def payment_status(
    intent_id: UUID,
    client_secret: str = Header(..., alias="X-Payment-Secret"),
    db: AsyncSession = Depends(session),
):
    intent = await db.get(PaymentIntent, intent_id)
    supplied = hashlib.sha256(client_secret.encode()).hexdigest()
    if not intent or not hmac.compare_digest(intent.client_secret_hash, supplied):
        raise HTTPException(status_code=404, detail="Payment intent not found")
    order = await db.get(Order, intent.order_id)
    return PaymentStatusRead(
        id=intent.id, order_reference=order.reference, state=intent.state,
        amount=intent.amount, currency=intent.currency, failure_message=intent.failure_message,
    )


@router.post("/callbacks/mpesa/{callback_secret}", status_code=200)
async def mpesa_callback(callback_secret: str, request: Request, db: AsyncSession = Depends(session)):
    if not settings.mpesa_callback_secret or not secrets.compare_digest(callback_secret, settings.mpesa_callback_secret):
        raise HTTPException(status_code=404, detail="Callback not found")
    payload = await request.json()
    result = parse_stk_callback(payload)
    intent = await db.scalar(select(PaymentIntent).where(
        PaymentIntent.provider == "safaricom",
        PaymentIntent.provider_reference == result["checkout_request_id"],
    ).with_for_update())
    if not intent:
        return {"ResultCode": 0, "ResultDesc": "Accepted"}
    if intent.state == "paid":
        return {"ResultCode": 0, "ResultDesc": "Accepted"}
    callback_record = {**result, "amount": str(result["amount"]) if result["amount"] is not None else None}
    intent.provider_payload = {**intent.provider_payload, "callback": callback_record}
    if result["result_code"] == 0:
        if result["amount"] != intent.amount or not result["receipt"]:
            intent.state = "review_required"
            intent.failure_code = "amount_mismatch"
            intent.failure_message = "M-Pesa confirmation did not match the expected payment"
        else:
            intent.state = "paid"
            intent.paid_at = datetime.now(timezone.utc)
            order = await db.get(Order, intent.order_id)
            order.state = "paid"
            db.add(OutboxEvent(
                aggregate_type="order", aggregate_id=order.id, topic="order.payment_confirmed",
                payload={"order_id": str(order.id), "payment_intent_id": str(intent.id)},
            ))
    else:
        intent.state = "cancelled" if result["result_code"] == 1032 else "failed"
        intent.failure_code = str(result["result_code"])
        intent.failure_message = result["result_description"]
    await db.commit()
    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@router.post("/callbacks/flutterwave", status_code=200)
async def flutterwave_callback(
    request: Request,
    signature: str | None = Header(None, alias="flutterwave-signature"),
    db: AsyncSession = Depends(session),
):
    body = await request.body()
    if not verify_flutterwave_signature(body, signature, settings.flutterwave_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    payload = json.loads(body)
    event_id = str(payload.get("id") or "")
    if not event_id:
        raise HTTPException(status_code=400, detail="Webhook event ID is required")
    if await db.scalar(select(PaymentEvent.id).where(
        PaymentEvent.provider == "flutterwave", PaymentEvent.provider_event_id == event_id
    )):
        return {"received": True}
    event = PaymentEvent(provider="flutterwave", provider_event_id=event_id, payload=payload)
    db.add(event)
    await db.flush()
    db.add(OutboxEvent(
        aggregate_type="payment_event", aggregate_id=event.id, topic="payment.verify_flutterwave",
        payload={"event_id": str(event.id)},
    ))
    await db.commit()
    return {"received": True}
