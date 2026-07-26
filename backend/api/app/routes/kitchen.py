from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import require_roles
from ..database import session
from ..models import (
    Customer, Ingredient, InventoryConsumption, Order, OrderLine, ProductionTicket,
    Product, Recipe, RecipeIngredient,
)
from ..services.audit import record_audit
from ..services.fulfilment import KITCHEN_STAGES, create_stage_command

router = APIRouter(prefix="/v1/kitchen", tags=["kitchen"])
kitchen_staff = require_roles("admin", "manager", "kitchen")
kitchen_manager = require_roles("admin", "manager")


class ChecklistInput(BaseModel):
    design_checked: bool
    message_checked: bool
    allergens_checked: bool
    packaging_checked: bool


class TransitionInput(BaseModel):
    stage: str = Field(pattern="^(baking|decorating|quality_check|packaging)$")


class IngredientInput(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    unit: str = Field(min_length=1, max_length=30)
    stock_on_hand: Decimal = Field(default=0, ge=0)
    reorder_level: Decimal = Field(default=0, ge=0)


class StockAdjustment(BaseModel):
    delta: Decimal
    reason: str = Field(min_length=2, max_length=300)


class RecipePart(BaseModel):
    ingredient_id: UUID
    quantity: Decimal = Field(gt=0)


class RecipeInput(BaseModel):
    product_id: UUID
    name: str = Field(min_length=2, max_length=220)
    yield_description: str = Field(min_length=1, max_length=120)
    preparation_minutes: int = Field(default=60, ge=1, le=1440)
    instructions: list[str] = Field(min_length=1, max_length=30)
    allergens: list[str] = Field(default_factory=list, max_length=30)
    ingredients: list[RecipePart] = Field(default_factory=list, max_length=50)


class ConsumptionInput(BaseModel):
    ingredient_id: UUID
    quantity: Decimal = Field(gt=0)


async def ticket_payload(db: AsyncSession, ticket: ProductionTicket) -> dict:
    order = await db.get(Order, ticket.order_id)
    lines = (await db.scalars(select(OrderLine).where(OrderLine.order_id == order.id))).all()
    return {
        "id": str(ticket.id), "reference": order.reference, "state": ticket.state,
        "priority": ticket.priority, "fulfilment": order.fulfilment, "delivery_slot": order.delivery_slot,
        "customer_name": order.customer_name, "created_at": ticket.created_at,
        "assigned_to": str(ticket.assigned_to) if ticket.assigned_to else None,
        "checklist": ticket.checklist, "recipe_snapshot": ticket.recipe_snapshot,
        "lines": [{"name": line.product_name, "quantity": line.quantity, "configuration": line.configuration} for line in lines],
    }


@router.get("/queue")
async def production_queue(actor: Customer = Depends(kitchen_staff), db: AsyncSession = Depends(session)):
    tickets = (await db.scalars(select(ProductionTicket).where(
        ProductionTicket.state.in_(KITCHEN_STAGES),
    ).order_by(ProductionTicket.priority, ProductionTicket.created_at).limit(200))).all()
    return [await ticket_payload(db, ticket) for ticket in tickets]


@router.get("/tickets/{ticket_id}")
async def ticket_detail(ticket_id: UUID, actor: Customer = Depends(kitchen_staff), db: AsyncSession = Depends(session)):
    ticket = await db.get(ProductionTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Production ticket not found")
    return await ticket_payload(db, ticket)


@router.post("/tickets/{ticket_id}/claim")
async def claim_ticket(ticket_id: UUID, request: Request, actor: Customer = Depends(kitchen_staff), db: AsyncSession = Depends(session)):
    ticket = await db.get(ProductionTicket, ticket_id, with_for_update=True)
    if not ticket:
        raise HTTPException(status_code=404, detail="Production ticket not found")
    if ticket.assigned_to and ticket.assigned_to != actor.id:
        raise HTTPException(status_code=409, detail="Ticket is already assigned")
    ticket.assigned_to = actor.id
    record_audit(db, actor, request, "kitchen.ticket.claimed", "production_ticket", ticket.id)
    await db.commit()
    return await ticket_payload(db, ticket)


@router.put("/tickets/{ticket_id}/checklist")
async def update_checklist(ticket_id: UUID, payload: ChecklistInput, request: Request, actor: Customer = Depends(kitchen_staff), db: AsyncSession = Depends(session)):
    ticket = await db.get(ProductionTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Production ticket not found")
    ticket.checklist = payload.model_dump()
    record_audit(db, actor, request, "kitchen.checklist.updated", "production_ticket", ticket.id, payload.model_dump())
    await db.commit()
    return {"checklist": ticket.checklist}


@router.post("/tickets/{ticket_id}/transition", status_code=202)
async def transition_ticket(
    ticket_id: UUID, payload: TransitionInput, request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=16, max_length=180),
    actor: Customer = Depends(kitchen_staff), db: AsyncSession = Depends(session),
):
    ticket = await db.get(ProductionTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Production ticket not found")
    order = await db.get(Order, ticket.order_id, with_for_update=True)
    if payload.stage == "packaging" and not all(ticket.checklist.values()):
        raise HTTPException(status_code=409, detail="Complete every quality checklist item before packaging")
    try:
        command = await create_stage_command(db, order, payload.stage, "kitchen", actor.id, idempotency_key, {"ticket_id": str(ticket.id)})
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    record_audit(db, actor, request, "kitchen.stage.requested", "order", order.id, {"stage": payload.stage, "command_id": str(command.id)})
    await db.commit()
    return {"command_id": str(command.id), "state": command.state, "requested_stage": command.requested_stage}


@router.get("/inventory")
async def inventory(actor: Customer = Depends(kitchen_staff), db: AsyncSession = Depends(session)):
    items = (await db.scalars(select(Ingredient).where(Ingredient.is_active.is_(True)).order_by(Ingredient.name))).all()
    return [{
        "id": str(item.id), "name": item.name, "unit": item.unit,
        "stock_on_hand": f"{item.stock_on_hand:.3f}", "reorder_level": f"{item.reorder_level:.3f}",
        "low_stock": item.stock_on_hand <= item.reorder_level,
    } for item in items]


@router.post("/inventory", status_code=201)
async def create_ingredient(payload: IngredientInput, request: Request, actor: Customer = Depends(kitchen_manager), db: AsyncSession = Depends(session)):
    if await db.scalar(select(Ingredient.id).where(Ingredient.name == payload.name.strip())):
        raise HTTPException(status_code=409, detail="Ingredient already exists")
    item = Ingredient(**payload.model_dump())
    db.add(item)
    await db.flush()
    record_audit(db, actor, request, "inventory.ingredient.created", "ingredient", item.id, payload.model_dump(mode="json"))
    await db.commit()
    return {"id": str(item.id), "created": True}


@router.post("/inventory/{ingredient_id}/adjust")
async def adjust_stock(ingredient_id: UUID, payload: StockAdjustment, request: Request, actor: Customer = Depends(kitchen_manager), db: AsyncSession = Depends(session)):
    item = await db.get(Ingredient, ingredient_id, with_for_update=True)
    if not item:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    updated = item.stock_on_hand + payload.delta
    if updated < 0:
        raise HTTPException(status_code=409, detail="Adjustment would make stock negative")
    before = item.stock_on_hand
    item.stock_on_hand = updated
    record_audit(db, actor, request, "inventory.stock.adjusted", "ingredient", item.id, {
        "before": str(before), "delta": str(payload.delta), "after": str(updated), "reason": payload.reason,
    })
    await db.commit()
    return {"stock_on_hand": f"{item.stock_on_hand:.3f}", "low_stock": item.stock_on_hand <= item.reorder_level}


@router.post("/tickets/{ticket_id}/consumption", status_code=201)
async def record_consumption(
    ticket_id: UUID, payload: ConsumptionInput, request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=16, max_length=180),
    actor: Customer = Depends(kitchen_staff), db: AsyncSession = Depends(session),
):
    existing = await db.scalar(select(InventoryConsumption).where(InventoryConsumption.idempotency_key == idempotency_key))
    if existing:
        return {"id": str(existing.id), "duplicate": True}
    if not await db.get(ProductionTicket, ticket_id):
        raise HTTPException(status_code=404, detail="Production ticket not found")
    ingredient = await db.get(Ingredient, payload.ingredient_id, with_for_update=True)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    if ingredient.stock_on_hand < payload.quantity:
        raise HTTPException(status_code=409, detail=f"Insufficient {ingredient.name} stock")
    ingredient.stock_on_hand -= payload.quantity
    consumption = InventoryConsumption(
        ticket_id=ticket_id, ingredient_id=ingredient.id, quantity=payload.quantity,
        recorded_by=actor.id, idempotency_key=idempotency_key,
    )
    db.add(consumption)
    await db.flush()
    record_audit(db, actor, request, "inventory.consumed", "production_ticket", ticket_id, {
        "ingredient_id": str(ingredient.id), "quantity": str(payload.quantity), "remaining": str(ingredient.stock_on_hand),
    })
    await db.commit()
    return {"id": str(consumption.id), "duplicate": False, "remaining": f"{ingredient.stock_on_hand:.3f}"}


@router.post("/recipes", status_code=201)
async def create_recipe(payload: RecipeInput, request: Request, actor: Customer = Depends(kitchen_manager), db: AsyncSession = Depends(session)):
    if not await db.get(Product, payload.product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    if await db.scalar(select(Recipe.id).where(Recipe.product_id == payload.product_id)):
        raise HTTPException(status_code=409, detail="Product already has a recipe")
    recipe = Recipe(**payload.model_dump(exclude={"ingredients"}))
    db.add(recipe)
    await db.flush()
    for part in payload.ingredients:
        if not await db.get(Ingredient, part.ingredient_id):
            await db.rollback()
            raise HTTPException(status_code=404, detail=f"Ingredient {part.ingredient_id} not found")
        db.add(RecipeIngredient(recipe_id=recipe.id, **part.model_dump()))
    record_audit(db, actor, request, "recipe.created", "recipe", recipe.id, {"product_id": str(payload.product_id), "version": 1})
    await db.commit()
    return {"id": str(recipe.id), "created": True}
