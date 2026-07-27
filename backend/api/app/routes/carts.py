import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import current_customer
from ..database import session
from ..models import Cart, CartItem, Customer, Product
from ..services.loyalty import notify

router = APIRouter(prefix="/v1/cart", tags=["cart"])


class CartItemInput(BaseModel):
    product_slug: str = Field(min_length=1, max_length=220)
    quantity: int = Field(ge=1, le=20)
    configuration: dict = Field(default_factory=dict)


class CartSyncInput(BaseModel):
    items: list[CartItemInput] = Field(default_factory=list, max_length=50)


class CartLine(BaseModel):
    id: UUID
    product_slug: str
    name: str
    quantity: int
    base_price_kes: float
    configuration: dict
    description: str
    image_url: str | None
    average_rating: float


class CartRead(BaseModel):
    id: UUID
    items: list[CartLine]
    recovery_sent_at: datetime | None
    recovered_at: datetime | None


ALLOWED_ADD_ONS = {"candles", "greeting-card", "gift-wrap", "flowers"}


def safe_configuration(value: dict) -> tuple[dict, str]:
    size = value.get("size", "1kg")
    if size not in {"1kg", "1.5kg", "2kg"}:
        size = "1kg"
    message = value.get("message", "")
    message = message.strip()[:32] if isinstance(message, str) else ""
    add_ons = value.get("add_ons", value.get("addOns", []))
    add_ons = sorted({item for item in add_ons if isinstance(item, str) and item in ALLOWED_ADD_ONS}) if isinstance(add_ons, list) else []
    configuration = {"size": size, "message": message, "add_ons": add_ons}
    digest = hashlib.sha256(json.dumps(configuration, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return configuration, digest


async def active_cart(customer: Customer, db: AsyncSession) -> Cart:
    cart = await db.scalar(select(Cart).where(Cart.customer_id == customer.id, Cart.state == "active").order_by(Cart.created_at.desc()))
    if cart:
        return cart
    cart = Cart(customer_id=customer.id, expires_at=datetime.now(timezone.utc) + timedelta(days=60))
    db.add(cart)
    await db.flush()
    return cart


async def serialize_cart(cart: Cart, db: AsyncSession) -> CartRead:
    rows = (await db.execute(
        select(CartItem, Product).join(Product, Product.id == CartItem.product_id).where(CartItem.cart_id == cart.id)
    )).all()
    return CartRead(id=cart.id, recovery_sent_at=cart.recovery_sent_at, recovered_at=cart.recovered_at, items=[
        CartLine(id=item.id, product_slug=product.slug, name=product.name, quantity=item.quantity,
                 base_price_kes=float(product.price_kes), configuration=item.configuration,
                 description=product.short_description or product.description,
                 image_url=product.image_url, average_rating=float(product.average_rating))
        for item, product in rows
    ])


@router.get("", response_model=CartRead)
async def get_cart(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    return await serialize_cart(await active_cart(customer, db), db)


@router.put("", response_model=CartRead)
async def synchronize_cart(
    payload: CartSyncInput, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session),
):
    cart = await active_cart(customer, db)
    slugs = {item.product_slug for item in payload.items}
    products = list((await db.scalars(select(Product).where(
        Product.slug.in_(slugs), Product.status == "publish", Product.in_stock.is_(True),
    ))).all()) if slugs else []
    by_slug = {product.slug: product for product in products}
    if len(by_slug) != len(slugs):
        raise HTTPException(status_code=409, detail="One or more cakes are no longer available")
    combined: dict[tuple[UUID, str], tuple[Product, int, dict]] = {}
    for line in payload.items:
        product = by_slug[line.product_slug]
        configuration, config_hash = safe_configuration(line.configuration)
        key = (product.id, config_hash)
        prior = combined.get(key)
        quantity = min(20, line.quantity + (prior[1] if prior else 0))
        if product.stock_quantity is not None and product.stock_quantity < quantity:
            raise HTTPException(status_code=409, detail=f"{product.name} quantity is unavailable")
        combined[key] = (product, quantity, configuration)
    await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
    for (product_id, config_hash), (_, quantity, configuration) in combined.items():
        db.add(CartItem(
            cart_id=cart.id, product_id=product_id, quantity=quantity,
            configuration=configuration, config_hash=config_hash,
        ))
    now = datetime.now(timezone.utc)
    cart.last_activity_at = now
    cart.checkout_started_at = None
    cart.recovery_sent_at = None
    cart.recovered_at = None
    await db.commit()
    return await serialize_cart(cart, db)


@router.post("/items", response_model=CartRead)
async def put_item(payload: CartItemInput, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    product = await db.scalar(select(Product).where(
        Product.slug == payload.product_slug, Product.status == "publish", Product.in_stock.is_(True)
    ))
    if not product:
        raise HTTPException(status_code=409, detail="Product is no longer available")
    if product.stock_quantity is not None and product.stock_quantity < payload.quantity:
        raise HTTPException(status_code=409, detail="Requested quantity is unavailable")
    cart = await active_cart(customer, db)
    configuration, config_hash = safe_configuration(payload.configuration)
    item = await db.scalar(select(CartItem).where(
        CartItem.cart_id == cart.id, CartItem.product_id == product.id, CartItem.config_hash == config_hash,
    ))
    if item:
        item.quantity = payload.quantity
        item.configuration = configuration
    else:
        db.add(CartItem(
            cart_id=cart.id, product_id=product.id, quantity=payload.quantity,
            configuration=configuration, config_hash=config_hash,
        ))
    cart.last_activity_at = datetime.now(timezone.utc)
    cart.recovery_sent_at = None
    await db.commit()
    return await serialize_cart(cart, db)


@router.delete("/items/{item_id}", response_model=CartRead)
async def remove_item(item_id: UUID, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    cart = await active_cart(customer, db)
    result = await db.execute(delete(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Cart item not found")
    await db.commit()
    return await serialize_cart(cart, db)


@router.post("/checkout-started", status_code=204)
async def checkout_started(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    cart = await active_cart(customer, db)
    cart.checkout_started_at = datetime.now(timezone.utc)
    await db.commit()


@router.post("/recovered", status_code=204)
async def mark_recovered(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    cart = await active_cart(customer, db)
    if cart.recovery_sent_at:
        cart.recovered_at = datetime.now(timezone.utc)
    await db.commit()


@router.post("/complete", status_code=204)
async def complete_cart(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    await complete_customer_cart(db, customer.id)
    await db.commit()


async def complete_customer_cart(db: AsyncSession, customer_id: UUID) -> None:
    cart = await db.scalar(select(Cart).where(
        Cart.customer_id == customer_id, Cart.state == "active",
    ).order_by(Cart.created_at.desc()).with_for_update())
    if cart:
        cart.state = "converted"
        cart.recovered_at = cart.recovered_at or (datetime.now(timezone.utc) if cart.recovery_sent_at else None)


async def process_abandoned_carts(db: AsyncSession, now: datetime) -> int:
    carts = list((await db.scalars(select(Cart).where(
        Cart.state == "active", Cart.customer_id.is_not(None),
        Cart.recovery_sent_at.is_(None),
        Cart.last_activity_at <= now - timedelta(hours=2),
        or_(Cart.checkout_started_at.is_(None), Cart.checkout_started_at <= now - timedelta(hours=24)),
        exists(select(CartItem.id).where(CartItem.cart_id == Cart.id)),
    ).order_by(Cart.last_activity_at).with_for_update(skip_locked=True).limit(100))).all())
    for cart in carts:
        count = len(list((await db.scalars(select(CartItem.id).where(CartItem.cart_id == cart.id))).all()))
        cart.recovery_sent_at = now
        await notify(
            db, cart.customer_id, "cart_recovery", "Your celebration is still waiting",
            f"{count} cake{'s are' if count != 1 else ' is'} saved in your bag. Return when the moment is right.",
            {"url": "/checkout?recovered=1", "cart_id": str(cart.id)},
        )
    return len(carts)
