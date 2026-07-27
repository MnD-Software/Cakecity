from calendar import monthrange
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_customer
from ..database import session
from ..models import (
    Address, ConsumerSubscription, ConsumerSubscriptionRun, Customer, Product,
)
from ..services.loyalty import notify

router = APIRouter(prefix="/v1/account/subscriptions", tags=["account"])


class PlanConfiguration(BaseModel):
    size: Literal["1kg", "1.5kg", "2kg"] = "1kg"
    message: str = Field(default="", max_length=32)
    add_ons: list[Literal["candles", "greeting-card", "gift-wrap", "flowers"]] = Field(default_factory=list, max_length=4)
    quantity: int = Field(default=1, ge=1, le=20)


class SubscriptionInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    product_slug: str = Field(min_length=1, max_length=220)
    cadence: Literal["once", "weekly", "monthly", "quarterly", "yearly"]
    configuration: PlanConfiguration = Field(default_factory=PlanConfiguration)
    fulfilment: Literal["delivery", "pickup"] = "delivery"
    address_id: UUID | None = None
    delivery_slot: str = Field(min_length=3, max_length=120)
    next_run_at: datetime


class StateInput(BaseModel):
    state: Literal["active", "paused", "cancelled"]
    next_run_at: datetime | None = None


async def plan_read(db: AsyncSession, plan: ConsumerSubscription) -> dict:
    product = await db.get(Product, plan.product_id)
    address = await db.get(Address, plan.address_id) if plan.address_id else None
    runs = list((await db.scalars(
        select(ConsumerSubscriptionRun).where(
            ConsumerSubscriptionRun.subscription_id == plan.id,
        ).order_by(ConsumerSubscriptionRun.scheduled_for.desc()).limit(6)
    )).all())
    return {
        "id": str(plan.id), "name": plan.name, "cadence": plan.cadence,
        "configuration": plan.configuration, "fulfilment": plan.fulfilment,
        "delivery_slot": plan.delivery_slot, "state": plan.state,
        "next_run_at": plan.next_run_at, "last_run_at": plan.last_run_at,
        "product": {
            "slug": product.slug, "name": product.name, "price_kes": f"{product.price_kes:.2f}",
            "image_url": product.image_url, "in_stock": product.in_stock and product.status == "publish",
        } if product else None,
        "address": {
            "id": str(address.id), "label": address.label, "line1": address.line1,
            "area": address.area, "city": address.city,
        } if address else None,
        "runs": [{"id": str(run.id), "scheduled_for": run.scheduled_for, "state": run.state} for run in runs],
    }


@router.get("")
async def list_subscriptions(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    plans = list((await db.scalars(
        select(ConsumerSubscription).where(
            ConsumerSubscription.customer_id == customer.id,
        ).order_by(ConsumerSubscription.created_at.desc()).limit(20)
    )).all())
    return [await plan_read(db, plan) for plan in plans]


@router.post("", status_code=201)
async def create_subscription(
    payload: SubscriptionInput, customer: Customer = Depends(current_customer),
    db: AsyncSession = Depends(session),
):
    now = datetime.now(timezone.utc)
    scheduled = payload.next_run_at
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=timezone.utc)
    if scheduled <= now + timedelta(hours=2):
        raise HTTPException(status_code=422, detail="First delivery must be at least two hours in the future")
    if (await db.scalar(select(func.count(ConsumerSubscription.id)).where(
        ConsumerSubscription.customer_id == customer.id,
        ConsumerSubscription.state.in_(("active", "paused")),
    ))) >= 20:
        raise HTTPException(status_code=409, detail="Subscription plan limit reached")
    product = await db.scalar(select(Product).where(
        Product.slug == payload.product_slug, Product.status == "publish", Product.in_stock.is_(True),
    ))
    if not product:
        raise HTTPException(status_code=404, detail="Cake is not available")
    if payload.fulfilment == "delivery":
        if not payload.address_id:
            raise HTTPException(status_code=422, detail="Choose a saved delivery address")
        address = await db.scalar(select(Address).where(
            Address.id == payload.address_id, Address.customer_id == customer.id,
        ))
        if not address:
            raise HTTPException(status_code=404, detail="Saved address not found")
    plan = ConsumerSubscription(
        customer_id=customer.id, product_id=product.id, address_id=payload.address_id,
        name=payload.name.strip(), cadence=payload.cadence,
        configuration=payload.configuration.model_dump(), fulfilment=payload.fulfilment,
        delivery_slot=payload.delivery_slot.strip(), next_run_at=scheduled,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return await plan_read(db, plan)


@router.patch("/{plan_id}")
async def update_subscription_state(
    plan_id: UUID, payload: StateInput, customer: Customer = Depends(current_customer),
    db: AsyncSession = Depends(session),
):
    plan = await db.scalar(select(ConsumerSubscription).where(
        ConsumerSubscription.id == plan_id, ConsumerSubscription.customer_id == customer.id,
    ).with_for_update())
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")
    if plan.state in ("completed", "cancelled") and payload.state != "cancelled":
        raise HTTPException(status_code=409, detail="Completed plans cannot be resumed")
    if payload.state == "active" and plan.next_run_at <= datetime.now(timezone.utc):
        resumed_at = payload.next_run_at
        if resumed_at and resumed_at.tzinfo is None:
            resumed_at = resumed_at.replace(tzinfo=timezone.utc)
        if not resumed_at or resumed_at <= datetime.now(timezone.utc) + timedelta(hours=2):
            raise HTTPException(status_code=422, detail="Choose a future renewal date")
        plan.next_run_at = resumed_at
    plan.state = payload.state
    await db.commit()
    await db.refresh(plan)
    return await plan_read(db, plan)


@router.post("/runs/{run_id}/ordered")
async def mark_run_ordered(
    run_id: UUID, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session),
):
    run = await db.scalar(
        select(ConsumerSubscriptionRun).join(
            ConsumerSubscription, ConsumerSubscription.id == ConsumerSubscriptionRun.subscription_id,
        ).where(ConsumerSubscriptionRun.id == run_id, ConsumerSubscription.customer_id == customer.id)
    )
    if not run:
        raise HTTPException(status_code=404, detail="Renewal not found")
    if run.state == "ready":
        run.state = "ordered"
        await db.commit()
    return {"id": str(run.id), "state": run.state}


async def process_due_subscriptions(db: AsyncSession, now: datetime) -> int:
    plans = list((await db.scalars(select(ConsumerSubscription).where(
        ConsumerSubscription.state == "active", ConsumerSubscription.next_run_at <= now,
    ).order_by(ConsumerSubscription.next_run_at).with_for_update(skip_locked=True).limit(100))).all())
    created = 0
    for plan in plans:
        scheduled = plan.next_run_at
        exists = await db.scalar(select(ConsumerSubscriptionRun.id).where(
            ConsumerSubscriptionRun.subscription_id == plan.id,
            ConsumerSubscriptionRun.scheduled_for == scheduled,
        ))
        if not exists:
            run = ConsumerSubscriptionRun(subscription_id=plan.id, scheduled_for=scheduled)
            db.add(run)
            await db.flush()
            product = await db.get(Product, plan.product_id)
            await notify(
                db, plan.customer_id, "subscription",
                f"{plan.name} is ready to confirm",
                f"Your {product.name if product else 'Cake City cake'} is scheduled. Review and confirm secure payment.",
                {"href": f"/account/subscriptions?renewal={run.id}", "subscription_id": str(plan.id)},
            )
            created += 1
        plan.last_run_at = now
        if plan.cadence == "once":
            plan.state = "completed"
        else:
            plan.next_run_at = next_subscription_run(max(scheduled, now), plan.cadence)
    return created


def next_subscription_run(scheduled: datetime, cadence: str) -> datetime:
    if cadence == "weekly":
        return scheduled + timedelta(days=7)
    months = {"monthly": 1, "quarterly": 3, "yearly": 12}[cadence]
    month_index = scheduled.month - 1 + months
    year = scheduled.year + month_index // 12
    month = month_index % 12 + 1
    return scheduled.replace(year=year, month=month, day=min(scheduled.day, monthrange(year, month)[1]))
