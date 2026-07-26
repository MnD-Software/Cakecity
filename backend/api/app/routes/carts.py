from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import current_customer
from ..database import session
from ..models import Cart, CartItem, Customer, Product

router = APIRouter(prefix="/v1/cart", tags=["cart"])


class CartItemInput(BaseModel):
    product_slug: str = Field(min_length=1, max_length=220)
    quantity: int = Field(ge=1, le=20)
    configuration: dict = Field(default_factory=dict)


class CartLine(BaseModel):
    id: UUID
    product_slug: str
    name: str
    quantity: int
    base_price_kes: float
    configuration: dict


class CartRead(BaseModel):
    id: UUID
    items: list[CartLine]


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
    return CartRead(id=cart.id, items=[
        CartLine(id=item.id, product_slug=product.slug, name=product.name, quantity=item.quantity,
                 base_price_kes=float(product.price_kes), configuration=item.configuration)
        for item, product in rows
    ])


@router.get("", response_model=CartRead)
async def get_cart(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    return await serialize_cart(await active_cart(customer, db), db)


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
    item = await db.scalar(select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product.id))
    if item:
        item.quantity = payload.quantity
        item.configuration = payload.configuration
    else:
        db.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=payload.quantity, configuration=payload.configuration))
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
