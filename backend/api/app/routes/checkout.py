from decimal import Decimal
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import session
from ..models import Product

router = APIRouter(prefix="/v1/checkout", tags=["checkout"])
SIZE_SURCHARGES = {"1kg": Decimal("0"), "1.5kg": Decimal("900"), "2kg": Decimal("1700")}
ADD_ON_PRICES = {
    "candles": Decimal("250"), "greeting-card": Decimal("350"),
    "gift-wrap": Decimal("300"), "flowers": Decimal("1800"),
}


def calculate_unit_price(base_price: Decimal, size: str, add_ons: list[str]) -> Decimal:
    if size not in SIZE_SURCHARGES or any(item not in ADD_ON_PRICES for item in add_ons):
        raise ValueError("Unsupported cake configuration")
    return base_price + SIZE_SURCHARGES[size] + sum(
        (ADD_ON_PRICES[item] for item in set(add_ons)), Decimal("0")
    )


class QuoteItemInput(BaseModel):
    product_slug: str = Field(min_length=1, max_length=220)
    quantity: int = Field(ge=1, le=20)
    size: Literal["1kg", "1.5kg", "2kg"] = "1kg"
    message: str = Field(default="", max_length=32)
    add_ons: list[Literal["candles", "greeting-card", "gift-wrap", "flowers"]] = Field(default_factory=list, max_length=4)


class CheckoutQuoteInput(BaseModel):
    items: list[QuoteItemInput] = Field(min_length=1, max_length=30)
    fulfilment: Literal["delivery", "pickup"] = "delivery"
    delivery_area: str | None = Field(default=None, max_length=160)
    delivery_slot: str | None = Field(default=None, max_length=80)
    coupon_code: str | None = Field(default=None, max_length=80)


class QuoteLine(BaseModel):
    product_slug: str
    name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    available: bool


class CheckoutQuote(BaseModel):
    currency: str = "KES"
    lines: list[QuoteLine]
    subtotal: Decimal
    delivery_fee: Decimal
    discount: Decimal
    total: Decimal
    fulfilment: str
    requires_address: bool
    quote_version: str = "2026-07"


@router.post("/quote", response_model=CheckoutQuote)
async def prepare_quote(payload: CheckoutQuoteInput, db: AsyncSession = Depends(session)):
    slugs = {item.product_slug for item in payload.items}
    products = {
        product.slug: product for product in (await db.scalars(
            select(Product).where(Product.slug.in_(slugs), Product.status == "publish")
        )).all()
    }
    lines: list[QuoteLine] = []
    subtotal = Decimal("0")
    for requested in payload.items:
        product = products.get(requested.product_slug)
        if not product:
            raise HTTPException(status_code=409, detail=f"{requested.product_slug} is no longer available")
        if not product.in_stock or (product.stock_quantity is not None and product.stock_quantity < requested.quantity):
            raise HTTPException(status_code=409, detail=f"{product.name} has insufficient stock")
        unit = calculate_unit_price(Decimal(product.price_kes), requested.size, requested.add_ons)
        line_total = unit * requested.quantity
        subtotal += line_total
        lines.append(QuoteLine(
            product_slug=product.slug, name=product.name, quantity=requested.quantity,
            unit_price=unit, line_total=line_total, available=True,
        ))
    delivery_fee = Decimal("0") if payload.fulfilment == "pickup" or subtotal >= 5000 else Decimal("350")
    # Coupon validation remains at the WooCommerce authority boundary in the payment release.
    discount = Decimal("0")
    return CheckoutQuote(
        lines=lines, subtotal=subtotal, delivery_fee=delivery_fee, discount=discount,
        total=subtotal + delivery_fee - discount, fulfilment=payload.fulfilment,
        requires_address=payload.fulfilment == "delivery",
    )
