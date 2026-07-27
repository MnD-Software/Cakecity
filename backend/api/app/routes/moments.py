from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import current_customer
from ..database import session
from ..models import CelebrationMoment, Customer, Order, OrderLine, Product
from ..services.reminders import anniversary_in_year

router = APIRouter(prefix="/v1/account/moments", tags=["moments"])


class MomentInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    relationship: str = Field(min_length=1, max_length=80)
    occasion: str = Field(pattern="^(birthday|anniversary|wedding|graduation|other)$")
    event_date: date
    reminder_days: list[int] = Field(default_factory=lambda: [30, 7, 1], min_length=1, max_length=5)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("reminder_days")
    @classmethod
    def valid_reminders(cls, values: list[int]) -> list[int]:
        if any(value < 0 or value > 90 for value in values):
            raise ValueError("Reminder days must be between 0 and 90")
        return sorted(set(values), reverse=True)


def read(item: CelebrationMoment) -> dict:
    return {
        "id": str(item.id), "name": item.name, "relationship": item.relationship,
        "occasion": item.occasion, "event_date": item.event_date,
        "reminder_days": item.reminder_days, "notes": item.notes, "is_active": item.is_active,
    }


@router.get("")
async def list_moments(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    items = (await db.scalars(select(CelebrationMoment).where(
        CelebrationMoment.customer_id == customer.id, CelebrationMoment.is_active.is_(True),
    ).order_by(CelebrationMoment.event_date))).all()
    return [read(item) for item in items]


@router.get("/timeline")
async def cake_memory_timeline(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    """Owner-scoped celebration history; WooCommerce-synchronized orders remain authoritative."""
    moments = (await db.scalars(select(CelebrationMoment).where(
        CelebrationMoment.customer_id == customer.id, CelebrationMoment.is_active.is_(True),
    ))).all()
    rows = (await db.execute(
        select(Order, OrderLine, Product)
        .join(OrderLine, OrderLine.order_id == Order.id)
        .join(Product, Product.id == OrderLine.product_id)
        .where(
            Order.customer_id == customer.id,
            Order.state.notin_(("awaiting_payment", "payment_failed", "cancelled")),
        )
        .order_by(Order.created_at.desc())
        .limit(150)
    )).all()
    memories = []
    for order, line, product in rows:
        message = str(line.configuration.get("message") or "")
        matched = next((moment for moment in moments if moment.name.casefold() in message.casefold()), None)
        memories.append({
            "order_reference": order.reference,
            "ordered_at": order.created_at,
            "year": order.created_at.year,
            "title": f"{matched.name}'s {matched.occasion}" if matched else line.product_name,
            "moment_id": str(matched.id) if matched else None,
            "product_name": line.product_name,
            "product_slug": product.slug,
            "image_url": product.image_url,
            "message": message or None,
            "configuration": line.configuration,
            "reorder_url": f"/account/orders/{order.reference}",
        })
    today = date.today()
    upcoming = []
    for moment in moments:
        event = anniversary_in_year(moment.event_date, today.year)
        if event < today:
            event = anniversary_in_year(moment.event_date, today.year + 1)
        previous = next((memory for memory in memories if memory["moment_id"] == str(moment.id)), None)
        upcoming.append({
            **read(moment), "next_event_date": event, "days_until": (event - today).days,
            "last_cake": previous,
            "prompt": (
                f"{moment.name}'s {moment.occasion} is coming up in {(event - today).days} days. "
                + (f"Reorder {previous['product_name']} or create a new design?" if previous else "Would you like to choose a cake?")
            ),
        })
    upcoming.sort(key=lambda item: item["days_until"])
    return {"memories": memories, "upcoming": upcoming}


@router.post("", status_code=201)
async def create_moment(payload: MomentInput, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    values = payload.model_dump()
    values["relationship"] = payload.relationship.strip()
    if payload.occasion == "birthday" and values["relationship"].lower() == "self":
        existing = await db.scalar(select(CelebrationMoment.id).where(
            CelebrationMoment.customer_id == customer.id,
            CelebrationMoment.occasion == "birthday",
            CelebrationMoment.relationship == "self",
        ))
        if existing:
            raise HTTPException(status_code=409, detail="Your birthday is already saved")
        values["relationship"] = "self"
    item = CelebrationMoment(customer_id=customer.id, **values)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return read(item)


@router.put("/{moment_id}")
async def update_moment(moment_id: UUID, payload: MomentInput, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    item = await db.scalar(select(CelebrationMoment).where(
        CelebrationMoment.id == moment_id, CelebrationMoment.customer_id == customer.id,
    ))
    if not item:
        raise HTTPException(status_code=404, detail="Moment not found")
    values = payload.model_dump()
    values["relationship"] = payload.relationship.strip().lower() if payload.occasion == "birthday" and payload.relationship.strip().lower() == "self" else payload.relationship.strip()
    if payload.occasion == "birthday" and values["relationship"] == "self":
        existing = await db.scalar(select(CelebrationMoment.id).where(
            CelebrationMoment.customer_id == customer.id,
            CelebrationMoment.occasion == "birthday",
            CelebrationMoment.relationship == "self",
            CelebrationMoment.id != moment_id,
        ))
        if existing:
            raise HTTPException(status_code=409, detail="Your birthday is already saved")
    for key, value in values.items():
        setattr(item, key, value)
    await db.commit()
    return read(item)


@router.delete("/{moment_id}", status_code=204)
async def delete_moment(moment_id: UUID, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    item = await db.scalar(select(CelebrationMoment).where(
        CelebrationMoment.id == moment_id, CelebrationMoment.customer_id == customer.id,
    ))
    if not item:
        raise HTTPException(status_code=404, detail="Moment not found")
    item.is_active = False
    await db.commit()
