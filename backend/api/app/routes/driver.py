import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import current_customer, require_roles
from ..database import session
from ..models import (
    Customer, DeliveryAssignment, DeliveryMessage, DriverLocation, DriverProfile, Order,
)
from ..services.audit import record_audit
from ..services.fulfilment import create_stage_command, hash_delivery_otp, new_delivery_otp, verify_delivery_otp
from ..services.loyalty import notify
from ..settings import settings

router = APIRouter(prefix="/v1/driver", tags=["driver"])
driver_user = require_roles("driver")
dispatch_staff = require_roles("admin", "manager")


class AssignmentInput(BaseModel):
    order_reference: str = Field(min_length=3, max_length=40)
    driver_id: UUID
    estimated_arrival_at: datetime | None = None


class LocationInput(BaseModel):
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)
    accuracy_meters: Decimal | None = Field(default=None, ge=0, le=5000)


class ProofInput(BaseModel):
    otp: str = Field(pattern="^[0-9]{6}$")
    proof_photo_url: HttpUrl
    signature_url: HttpUrl
    recipient_name: str = Field(min_length=2, max_length=180)


class MessageInput(BaseModel):
    body: str = Field(min_length=1, max_length=500)


def assignment_read(item: DeliveryAssignment, order: Order) -> dict:
    return {
        "id": str(item.id), "reference": order.reference, "state": item.state,
        "customer_name": order.customer_name, "customer_phone": order.customer_phone,
        "delivery_address": order.delivery_address, "delivery_slot": order.delivery_slot,
        "estimated_arrival_at": item.estimated_arrival_at,
        "accepted_at": item.accepted_at, "picked_up_at": item.picked_up_at,
        "delivered_at": item.delivered_at,
    }


async def owned_assignment(db: AsyncSession, assignment_id: UUID, driver_id: UUID) -> tuple[DeliveryAssignment, Order]:
    item = await db.scalar(select(DeliveryAssignment).where(
        DeliveryAssignment.id == assignment_id, DeliveryAssignment.driver_id == driver_id,
    ))
    if not item:
        raise HTTPException(status_code=404, detail="Delivery assignment not found")
    return item, await db.get(Order, item.order_id)


@router.get("/dispatch/overview")
async def dispatch_overview(actor: Customer = Depends(dispatch_staff), db: AsyncSession = Depends(session)):
    drivers = (await db.execute(select(Customer, DriverProfile).join(
        DriverProfile, DriverProfile.customer_id == Customer.id,
    ).where(Customer.is_active.is_(True), Customer.role == "driver").order_by(Customer.first_name))).all()
    ready = (await db.scalars(select(Order).where(
        Order.fulfilment == "delivery", Order.state == "packaging",
    ).order_by(Order.delivery_slot, Order.created_at))).all()
    return {
        "drivers": [{"id": str(user.id), "name": f"{user.first_name} {user.last_name}".strip(),
                     "phone": user.phone, "vehicle": f"{profile.vehicle_type} · {profile.vehicle_registration}",
                     "available": profile.is_available, "last_seen_at": profile.last_seen_at}
                    for user, profile in drivers],
        "ready_orders": [{"reference": order.reference, "customer_name": order.customer_name,
                          "delivery_address": order.delivery_address, "delivery_slot": order.delivery_slot}
                         for order in ready],
    }


@router.post("/dispatch/assignments", status_code=201)
async def assign_delivery(
    payload: AssignmentInput, request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=16, max_length=180),
    actor: Customer = Depends(dispatch_staff), db: AsyncSession = Depends(session),
):
    order = await db.scalar(select(Order).where(Order.reference == payload.order_reference).with_for_update())
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.fulfilment != "delivery":
        raise HTTPException(status_code=409, detail="Pickup orders do not need a driver")
    driver = await db.scalar(select(Customer).where(
        Customer.id == payload.driver_id, Customer.role == "driver", Customer.is_active.is_(True),
    ))
    profile = await db.get(DriverProfile, payload.driver_id)
    if not driver or not profile or not profile.is_available:
        raise HTTPException(status_code=409, detail="Driver is not available")
    existing = await db.scalar(select(DeliveryAssignment).where(DeliveryAssignment.order_id == order.id))
    if existing:
        return {"id": str(existing.id), "duplicate": True}
    otp = new_delivery_otp()
    assignment = DeliveryAssignment(
        order_id=order.id, driver_id=driver.id, delivery_otp_hash="pending",
        otp_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        estimated_arrival_at=payload.estimated_arrival_at,
    )
    db.add(assignment)
    await db.flush()
    assignment.delivery_otp_hash = hash_delivery_otp(assignment.id, otp)
    try:
        command = await create_stage_command(
            db, order, "driver_assigned", "dispatch", actor.id, idempotency_key,
            {"assignment_id": str(assignment.id), "driver_id": str(driver.id)},
        )
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if order.customer_id:
        await notify(
            db, order.customer_id, "delivery_otp", "Your Cake City delivery code",
            f"Share {otp} with your driver only after your cake arrives.",
            {"url": f"/account/orders/{order.reference}", "reference": order.reference},
        )
    profile.is_available = False
    record_audit(db, actor, request, "delivery.assigned", "delivery_assignment", assignment.id, {
        "order_id": str(order.id), "driver_id": str(driver.id), "command_id": str(command.id),
    })
    await db.commit()
    return {"id": str(assignment.id), "duplicate": False, "command_id": str(command.id)}


@router.get("/assignments")
async def assignments(actor: Customer = Depends(driver_user), db: AsyncSession = Depends(session)):
    items = (await db.scalars(select(DeliveryAssignment).where(
        DeliveryAssignment.driver_id == actor.id,
        DeliveryAssignment.state.not_in(("delivered", "cancelled")),
    ).order_by(DeliveryAssignment.created_at))).all()
    return [assignment_read(item, await db.get(Order, item.order_id)) for item in items]


@router.get("/assignments/{assignment_id}")
async def assignment_detail(assignment_id: UUID, actor: Customer = Depends(driver_user), db: AsyncSession = Depends(session)):
    item, order = await owned_assignment(db, assignment_id, actor.id)
    return assignment_read(item, order)


@router.post("/assignments/{assignment_id}/accept")
async def accept_assignment(assignment_id: UUID, request: Request, actor: Customer = Depends(driver_user), db: AsyncSession = Depends(session)):
    item, order = await owned_assignment(db, assignment_id, actor.id)
    if item.state not in ("assigned", "driver_assigned"):
        raise HTTPException(status_code=409, detail="Assignment can no longer be accepted")
    item.accepted_at = item.accepted_at or datetime.now(timezone.utc)
    profile = await db.get(DriverProfile, actor.id)
    profile.last_seen_at = datetime.now(timezone.utc)
    record_audit(db, actor, request, "delivery.accepted", "delivery_assignment", item.id)
    await db.commit()
    return assignment_read(item, order)


@router.post("/assignments/{assignment_id}/location", status_code=202)
async def update_location(assignment_id: UUID, payload: LocationInput, actor: Customer = Depends(driver_user), db: AsyncSession = Depends(session)):
    item, _ = await owned_assignment(db, assignment_id, actor.id)
    if item.state not in ("driver_assigned", "out_for_delivery", "assigned"):
        raise HTTPException(status_code=409, detail="Location sharing is not active")
    location = DriverLocation(assignment_id=item.id, **payload.model_dump())
    db.add(location)
    profile = await db.get(DriverProfile, actor.id)
    profile.last_seen_at = datetime.now(timezone.utc)
    await db.commit()
    return {"accepted": True, "recorded_at": location.recorded_at}


@router.post("/assignments/{assignment_id}/pickup", status_code=202)
async def pickup(
    assignment_id: UUID, request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=16, max_length=180),
    actor: Customer = Depends(driver_user), db: AsyncSession = Depends(session),
):
    item, order = await owned_assignment(db, assignment_id, actor.id)
    try:
        command = await create_stage_command(db, order, "out_for_delivery", "driver", actor.id, idempotency_key, {"assignment_id": str(item.id)})
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    record_audit(db, actor, request, "delivery.pickup.requested", "delivery_assignment", item.id, {"command_id": str(command.id)})
    await db.commit()
    return {"command_id": str(command.id), "state": command.state}


@router.post("/assignments/{assignment_id}/proof", status_code=202)
async def deliver(
    assignment_id: UUID, payload: ProofInput, request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=16, max_length=180),
    actor: Customer = Depends(driver_user), db: AsyncSession = Depends(session),
):
    item, order = await owned_assignment(db, assignment_id, actor.id)
    if item.state != "out_for_delivery":
        raise HTTPException(status_code=409, detail="Order is not out for delivery")
    if item.otp_expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="Delivery code expired; contact dispatch")
    if item.otp_attempts >= 5:
        raise HTTPException(status_code=429, detail="Too many delivery-code attempts; contact dispatch")
    item.otp_attempts += 1
    if not verify_delivery_otp(item, payload.otp):
        await db.commit()
        raise HTTPException(status_code=422, detail="Delivery code is incorrect")
    item.proof_photo_url = str(payload.proof_photo_url)
    item.signature_url = str(payload.signature_url)
    item.recipient_name = payload.recipient_name
    try:
        command = await create_stage_command(db, order, "delivered", "driver", actor.id, idempotency_key, {"assignment_id": str(item.id)})
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    record_audit(db, actor, request, "delivery.proof.submitted", "delivery_assignment", item.id, {
        "recipient_name": payload.recipient_name, "proof_photo_url": str(payload.proof_photo_url),
        "signature_url": str(payload.signature_url), "command_id": str(command.id),
    })
    await db.commit()
    return {"command_id": str(command.id), "state": command.state}


@router.get("/assignments/{assignment_id}/messages")
async def messages(assignment_id: UUID, actor: Customer = Depends(driver_user), db: AsyncSession = Depends(session)):
    item, _ = await owned_assignment(db, assignment_id, actor.id)
    rows = (await db.scalars(select(DeliveryMessage).where(
        DeliveryMessage.assignment_id == item.id,
    ).order_by(DeliveryMessage.created_at).limit(200))).all()
    return [{"id": str(row.id), "sender_role": row.sender_role, "body": row.body, "created_at": row.created_at} for row in rows]


@router.post("/assignments/{assignment_id}/messages", status_code=201)
async def send_message(assignment_id: UUID, payload: MessageInput, actor: Customer = Depends(driver_user), db: AsyncSession = Depends(session)):
    item, order = await owned_assignment(db, assignment_id, actor.id)
    message = DeliveryMessage(assignment_id=item.id, sender_id=actor.id, sender_role="driver", body=payload.body.strip())
    db.add(message)
    if order.customer_id:
        await notify(db, order.customer_id, "driver_message", "Message from your Cake City driver", message.body, {"url": f"/account/orders/{order.reference}"})
    await db.commit()
    return {"id": str(message.id), "created": True}


@router.get("/uploads/signature")
async def cloudinary_signature(actor: Customer = Depends(driver_user)):
    if not all((settings.cloudinary_cloud_name, settings.cloudinary_api_key, settings.cloudinary_api_secret)):
        raise HTTPException(status_code=503, detail="Delivery proof uploads are not configured")
    timestamp = int(datetime.now(timezone.utc).timestamp())
    folder = "cakecity/delivery-proof"
    signature = hashlib.sha1(f"folder={folder}&timestamp={timestamp}{settings.cloudinary_api_secret}".encode()).hexdigest()
    return {
        "cloud_name": settings.cloudinary_cloud_name, "api_key": settings.cloudinary_api_key,
        "timestamp": timestamp, "folder": folder, "signature": signature,
        "upload_url": f"https://api.cloudinary.com/v1_1/{settings.cloudinary_cloud_name}/image/upload",
    }
