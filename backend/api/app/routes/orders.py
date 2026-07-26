from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import current_customer
from ..database import session
from pydantic import BaseModel, Field
from ..models import (
    Customer, DeliveryAssignment, DeliveryMessage, DriverLocation, DriverProfile,
    Order, OrderLine, OrderTimelineEvent, Product,
)
from ..services.loyalty import notify
from ..services.order_tracking import STAGES

router = APIRouter(prefix="/v1/account/orders", tags=["orders"])


class DeliveryMessageInput(BaseModel):
    body: str = Field(min_length=1, max_length=500)


def money(value) -> str:
    return f"{value:.2f}"


def order_summary(order: Order) -> dict:
    return {
        "reference": order.reference, "state": order.state, "total": money(order.total),
        "currency": order.currency, "fulfilment": order.fulfilment,
        "delivery_slot": order.delivery_slot, "created_at": order.created_at,
    }


async def owned_order(db: AsyncSession, customer_id: UUID, reference: str) -> Order:
    order = await db.scalar(select(Order).where(
        Order.reference == reference, Order.customer_id == customer_id,
    ))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("")
async def list_orders(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    orders = (await db.scalars(select(Order).where(
        Order.customer_id == customer.id,
    ).order_by(Order.created_at.desc()).limit(100))).all()
    return [order_summary(order) for order in orders]


@router.get("/{reference}")
async def order_detail(reference: str, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    order = await owned_order(db, customer.id, reference)
    lines = (await db.scalars(select(OrderLine).where(OrderLine.order_id == order.id))).all()
    events = (await db.scalars(select(OrderTimelineEvent).where(
        OrderTimelineEvent.order_id == order.id,
    ).order_by(OrderTimelineEvent.occurred_at))).all()
    delivery = await db.scalar(select(DeliveryAssignment).where(DeliveryAssignment.order_id == order.id))
    driver_tracking = None
    if delivery:
        driver = await db.get(Customer, delivery.driver_id)
        profile = await db.get(DriverProfile, delivery.driver_id)
        location = await db.scalar(select(DriverLocation).where(
            DriverLocation.assignment_id == delivery.id,
        ).order_by(DriverLocation.recorded_at.desc()).limit(1))
        driver_tracking = {
            "assignment_id": str(delivery.id), "state": delivery.state,
            "driver_name": driver.first_name if driver else "Cake City driver",
            "vehicle": f"{profile.vehicle_type} · {profile.vehicle_registration}" if profile else None,
            "estimated_arrival_at": delivery.estimated_arrival_at,
            "location": ({
                "latitude": str(location.latitude), "longitude": str(location.longitude),
                "accuracy_meters": str(location.accuracy_meters) if location.accuracy_meters is not None else None,
                "recorded_at": location.recorded_at,
            } if location else None),
        }
    return {
        **order_summary(order), "customer_name": order.customer_name,
        "delivery_address": order.delivery_address, "stages": STAGES,
        "lines": [{
            "id": str(line.id), "product_name": line.product_name, "quantity": line.quantity,
            "unit_price": money(line.unit_price), "line_total": money(line.line_total),
            "configuration": line.configuration,
        } for line in lines],
        "timeline": [{
            "id": str(event.id), "stage": event.stage, "title": event.title,
            "detail": event.detail, "occurred_at": event.occurred_at,
        } for event in events],
        "driver_tracking": driver_tracking,
    }


@router.post("/{reference}/reorder")
async def reorder(reference: str, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    order = await owned_order(db, customer.id, reference)
    lines = (await db.scalars(select(OrderLine).where(OrderLine.order_id == order.id))).all()
    products = {
        product.id: product for product in (await db.scalars(select(Product).where(
            Product.id.in_([line.product_id for line in lines]),
        ))).all()
    }
    available, unavailable = [], []
    for line in lines:
        product = products.get(line.product_id)
        if not product or product.status != "publish" or not product.in_stock:
            unavailable.append({"product_name": line.product_name, "reason": "Currently unavailable"})
            continue
        quantity = min(line.quantity, product.stock_quantity or line.quantity)
        if quantity < 1:
            unavailable.append({"product_name": line.product_name, "reason": "Out of stock"})
            continue
        available.append({
            "id": str(product.id), "woo_id": product.woo_id, "slug": product.slug,
            "name": product.name, "price_kes": money(product.price_kes),
            "image_url": product.image_url, "quantity": quantity,
            "configuration": line.configuration,
        })
    return {
        "source_reference": order.reference, "available": available, "unavailable": unavailable,
        "message": "Prices and availability were refreshed from the current catalogue.",
    }


@router.get("/{reference}/delivery/messages")
async def delivery_messages(reference: str, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    order = await owned_order(db, customer.id, reference)
    assignment = await db.scalar(select(DeliveryAssignment).where(DeliveryAssignment.order_id == order.id))
    if not assignment:
        return []
    items = (await db.scalars(select(DeliveryMessage).where(
        DeliveryMessage.assignment_id == assignment.id,
    ).order_by(DeliveryMessage.created_at).limit(200))).all()
    return [{"id": str(item.id), "sender_role": item.sender_role, "body": item.body, "created_at": item.created_at} for item in items]


@router.post("/{reference}/delivery/messages", status_code=201)
async def send_delivery_message(reference: str, payload: DeliveryMessageInput, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    order = await owned_order(db, customer.id, reference)
    assignment = await db.scalar(select(DeliveryAssignment).where(DeliveryAssignment.order_id == order.id))
    if not assignment or assignment.state == "delivered":
        raise HTTPException(status_code=409, detail="Live driver chat is not available")
    message = DeliveryMessage(
        assignment_id=assignment.id, sender_id=customer.id,
        sender_role="customer", body=payload.body.strip(),
    )
    db.add(message)
    await notify(db, assignment.driver_id, "customer_message", f"Message for {order.reference}", message.body)
    await db.commit()
    return {"id": str(message.id), "created": True}
