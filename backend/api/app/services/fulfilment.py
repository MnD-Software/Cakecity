import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from sqlalchemy import select
from ..models import (
    DeliveryAssignment, DriverLocation, DriverProfile, Order, OrderLine, OrderStageCommand,
    OutboxEvent, ProductionTicket, Recipe, RecipeIngredient, Ingredient,
)
from ..services.order_tracking import STAGES, append_stage
from ..services.woocommerce import WooCommerceClient
from ..settings import settings

KITCHEN_STAGES = ("confirmed", "baking", "decorating", "quality_check", "packaging")
DRIVER_STAGES = ("driver_assigned", "out_for_delivery", "delivered")
NEXT_STAGE = {
    "confirmed": "baking", "baking": "decorating", "decorating": "quality_check",
    "quality_check": "packaging", "packaging": "driver_assigned",
    "driver_assigned": "out_for_delivery", "out_for_delivery": "delivered",
}


def hash_delivery_otp(assignment_id, otp: str) -> str:
    return hmac.new(settings.jwt_secret.encode(), f"delivery:{assignment_id}:{otp}".encode(), hashlib.sha256).hexdigest()


def verify_delivery_otp(assignment: DeliveryAssignment, otp: str) -> bool:
    return hmac.compare_digest(assignment.delivery_otp_hash, hash_delivery_otp(assignment.id, otp))


async def recipe_snapshot(db, lines: list[OrderLine]) -> dict:
    snapshot = {}
    for line in lines:
        recipe = await db.scalar(select(Recipe).where(Recipe.product_id == line.product_id, Recipe.is_active.is_(True)))
        if not recipe:
            snapshot[str(line.id)] = {"product": line.product_name, "quantity": line.quantity, "recipe": None}
            continue
        ingredients = (await db.execute(select(
            Ingredient.name, RecipeIngredient.quantity, Ingredient.unit,
        ).join(RecipeIngredient, RecipeIngredient.ingredient_id == Ingredient.id).where(
            RecipeIngredient.recipe_id == recipe.id,
        ))).all()
        snapshot[str(line.id)] = {
            "product": line.product_name, "quantity": line.quantity,
            "recipe": {
                "id": str(recipe.id), "name": recipe.name, "version": recipe.version,
                "yield": recipe.yield_description, "preparation_minutes": recipe.preparation_minutes,
                "instructions": recipe.instructions, "allergens": recipe.allergens,
                "ingredients": [{"name": name, "quantity": str(quantity * line.quantity), "unit": unit} for name, quantity, unit in ingredients],
            },
            "configuration": line.configuration,
        }
    return snapshot


async def ensure_production_ticket(db, order: Order) -> ProductionTicket:
    existing = await db.scalar(select(ProductionTicket).where(ProductionTicket.order_id == order.id))
    if existing:
        return existing
    lines = list((await db.scalars(select(OrderLine).where(OrderLine.order_id == order.id))).all())
    ticket = ProductionTicket(
        order_id=order.id, state="confirmed",
        recipe_snapshot=await recipe_snapshot(db, lines),
        checklist={"design_checked": False, "message_checked": False, "allergens_checked": False, "packaging_checked": False},
    )
    db.add(ticket)
    await db.flush()
    return ticket


async def create_stage_command(db, order: Order, stage: str, source: str, actor_id, idempotency_key: str, metadata: dict | None = None) -> OrderStageCommand:
    existing = await db.scalar(select(OrderStageCommand).where(OrderStageCommand.idempotency_key == idempotency_key))
    if existing:
        return existing
    if not order.woo_id:
        raise ValueError("Order is not yet synchronized to WooCommerce")
    if stage not in STAGES or NEXT_STAGE.get(order.state) != stage:
        raise ValueError(f"Order cannot move from {order.state} to {stage}")
    pending = await db.scalar(select(OrderStageCommand.id).where(
        OrderStageCommand.order_id == order.id, OrderStageCommand.state.in_(("pending", "processing")),
    ))
    if pending:
        raise ValueError("An order stage update is already in progress")
    command = OrderStageCommand(
        order_id=order.id, requested_stage=stage, source=source, actor_id=actor_id,
        idempotency_key=idempotency_key, command_metadata=metadata or {},
    )
    db.add(command)
    await db.flush()
    db.add(OutboxEvent(
        aggregate_type="stage_command", aggregate_id=command.id, topic="woocommerce.order_stage_update",
        payload={"command_id": str(command.id)},
    ))
    return command


async def synchronize_operational_state(db, order: Order, stage: str) -> None:
    ticket = await db.scalar(select(ProductionTicket).where(ProductionTicket.order_id == order.id))
    if stage in KITCHEN_STAGES:
        ticket = ticket or await ensure_production_ticket(db, order)
        ticket.state = stage
        if stage == "baking" and not ticket.started_at:
            ticket.started_at = datetime.now(timezone.utc)
        if stage == "packaging":
            ticket.completed_at = datetime.now(timezone.utc)
    assignment = await db.scalar(select(DeliveryAssignment).where(DeliveryAssignment.order_id == order.id))
    if assignment and stage in DRIVER_STAGES:
        assignment.state = stage
        if stage == "out_for_delivery" and not assignment.picked_up_at:
            assignment.picked_up_at = datetime.now(timezone.utc)
        if stage == "delivered":
            assignment.delivered_at = datetime.now(timezone.utc)
            profile = await db.scalar(select(DriverProfile).where(DriverProfile.customer_id == assignment.driver_id))
            if profile:
                profile.is_available = True


async def process_stage_command(db, command: OrderStageCommand) -> None:
    if command.state == "processed":
        return
    order = await db.get(Order, command.order_id)
    command.state = "processing"
    client = WooCommerceClient(settings.woocommerce_url, settings.woocommerce_consumer_key, settings.woocommerce_consumer_secret)
    await client.update_order_stage(order.woo_id, command.requested_stage)
    await append_stage(
        db, order, command.requested_stage, f"command:{command.id}",
        command.source, metadata={"actor_id": str(command.actor_id), **command.command_metadata},
    )
    await synchronize_operational_state(db, order, command.requested_stage)
    command.state = "processed"
    command.processed_at = datetime.now(timezone.utc)
    command.failure_message = None


def new_delivery_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"
