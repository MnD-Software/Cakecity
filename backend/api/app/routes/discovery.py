import hashlib
import json
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from ..auth import optional_customer
from ..database import session
from ..models import Customer, DiscoveryEvent, Order, OrderLine, Product
from ..schemas import ProductRead
from ..services.discovery import SearchIntent, parse_intent, rank_products
from ..settings import settings

router = APIRouter(prefix="/v1/discovery", tags=["discovery"])
cache = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)


class DiscoveryProduct(ProductRead):
    reason: list[str]
    relevance: float


class DiscoveryResponse(BaseModel):
    query: str
    intent: dict
    message: str
    items: list[DiscoveryProduct]


class ConciergeInput(BaseModel):
    occasion: str = Field(min_length=2, max_length=80)
    recipient: str = Field(default="", max_length=80)
    age: int | None = Field(default=None, ge=1, le=120)
    style: str = Field(default="", max_length=80)
    flavour: str = Field(default="", max_length=80)
    budget_kes: int | None = Field(default=None, ge=500, le=500000)
    servings: int | None = Field(default=None, ge=1, le=1000)


class DiscoveryEventInput(BaseModel):
    event_type: Literal["view", "search", "recommendation_click", "add_to_cart", "concierge"]
    product_slug: str | None = Field(default=None, max_length=220)
    query: str | None = Field(default=None, max_length=240)
    context: dict = Field(default_factory=dict)


async def available_products(db: AsyncSession) -> list[Product]:
    return list((await db.scalars(
        select(Product).where(Product.status == "publish", Product.in_stock.is_(True))
        .order_by(Product.average_rating.desc(), Product.review_count.desc()).limit(500)
    )).all())


def response_item(product: Product, score: float, reasons: list[str]) -> DiscoveryProduct:
    return DiscoveryProduct.model_validate(product).model_copy(update={
        "reason": reasons, "relevance": round(score, 3),
    })


async def cached_response(key: str) -> DiscoveryResponse | None:
    try:
        value = await cache.get(key)
        return DiscoveryResponse.model_validate_json(value) if value else None
    except Exception:
        return None


async def store_response(key: str, response: DiscoveryResponse) -> None:
    try:
        await cache.setex(key, 300, response.model_dump_json())
    except Exception:
        pass


@router.get("/search", response_model=DiscoveryResponse)
async def natural_search(
    q: str = Query(min_length=2, max_length=240),
    limit: int = Query(default=12, ge=1, le=24),
    db: AsyncSession = Depends(session),
):
    cache_key = f"discovery:search:{hashlib.sha256(f'{q}:{limit}'.encode()).hexdigest()}"
    cached = await cached_response(cache_key)
    if cached:
        return cached
    intent = parse_intent(q)
    ranked = rank_products(await available_products(db), intent, limit)
    response = DiscoveryResponse(
        query=q, intent=intent.public(),
        message=f"We found {len(ranked)} Cake City creations for your moment.",
        items=[response_item(product, score, reasons) for score, reasons, product in ranked],
    )
    await store_response(cache_key, response)
    return response


@router.get("/recommendations", response_model=DiscoveryResponse)
async def recommendations(
    limit: int = Query(default=8, ge=1, le=16),
    customer: Customer | None = Depends(optional_customer),
    db: AsyncSession = Depends(session),
):
    cache_key = f"discovery:recommendations:guest:{limit}"
    if not customer:
        cached = await cached_response(cache_key)
        if cached:
            return cached
    preference_terms: set[str] = set()
    if customer:
        history = (await db.execute(
            select(Product.categories, Product.attributes).join(OrderLine, OrderLine.product_id == Product.id)
            .join(Order, Order.id == OrderLine.order_id)
            .where(
                Order.customer_id == customer.id,
                Order.state.in_(("paid", "processing", "completed", "delivered")),
            )
            .order_by(Order.created_at.desc()).limit(30)
        )).all()
        for categories, attributes in history:
            preference_terms.update(str(item).lower() for item in (categories or []))
            for attribute in attributes or []:
                preference_terms.update(str(item).lower() for item in attribute.get("options", []))
    intent = SearchIntent(query="personalized recommendations")
    ranked = rank_products(await available_products(db), intent, limit, preference_terms)
    response = DiscoveryResponse(
        query="", intent=intent.public(),
        message="Selected from your Cake City history." if preference_terms else "Trending across Cake City right now.",
        items=[response_item(product, score, reasons) for score, reasons, product in ranked],
    )
    if not customer:
        await store_response(cache_key, response)
    return response


@router.post("/concierge", response_model=DiscoveryResponse)
async def concierge(payload: ConciergeInput, db: AsyncSession = Depends(session)):
    phrase = " ".join(filter(None, [
        payload.occasion, payload.recipient,
        f"{payload.age} year old" if payload.age else "",
        payload.style, payload.flavour,
        f"under KES {payload.budget_kes}" if payload.budget_kes else "",
        f"serves {payload.servings}" if payload.servings else "",
    ]))
    cache_key = f"discovery:concierge:{hashlib.sha256(json.dumps(payload.model_dump(), sort_keys=True).encode()).hexdigest()}"
    cached = await cached_response(cache_key)
    if cached:
        return cached
    intent = parse_intent(phrase)
    ranked = rank_products(await available_products(db), intent, 4)
    response = DiscoveryResponse(
        query=phrase, intent=intent.public(),
        message="A considered shortlist for the person, moment and budget you shared.",
        items=[response_item(product, score, reasons) for score, reasons, product in ranked],
    )
    await store_response(cache_key, response)
    return response


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def record_event(
    payload: DiscoveryEventInput,
    request: Request,
    x_discovery_session: str = Header(default="anonymous", max_length=100),
    customer: Customer | None = Depends(optional_customer),
    db: AsyncSession = Depends(session),
):
    product_id: UUID | None = None
    if payload.product_slug:
        product_id = await db.scalar(select(Product.id).where(Product.slug == payload.product_slug))
    safe_context = {
        str(key)[:60]: value for key, value in list(payload.context.items())[:12]
        if isinstance(value, (str, int, float, bool)) or value is None
    }
    db.add(DiscoveryEvent(
        customer_id=customer.id if customer else None,
        session_hash=hashlib.sha256(x_discovery_session.encode()).hexdigest(),
        event_type=payload.event_type,
        product_id=product_id,
        query=payload.query,
        context=safe_context,
    ))
    await db.commit()
    return {"accepted": True, "request_id": request.headers.get("x-request-id")}
