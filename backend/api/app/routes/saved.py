from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_customer
from ..database import session
from ..models import Customer, Product, SavedCake, SavedMessage

router = APIRouter(prefix="/v1/account/saved", tags=["account"])


class SavedCakeRead(BaseModel):
    id: UUID
    product_id: UUID
    slug: str
    name: str
    image_url: str | None
    price_kes: float
    in_stock: bool
    created_at: datetime


class SavedMessageInput(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=160)


class SavedMessageRead(SavedMessageInput):
    id: UUID
    created_at: datetime


@router.get("/cakes", response_model=list[SavedCakeRead])
async def list_saved_cakes(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    rows = (await db.execute(
        select(SavedCake, Product)
        .join(Product, Product.id == SavedCake.product_id)
        .where(SavedCake.customer_id == customer.id)
        .order_by(SavedCake.created_at.desc())
    )).all()
    return [
        SavedCakeRead(
            id=saved.id, product_id=product.id, slug=product.slug, name=product.name,
            image_url=product.image_url, price_kes=float(product.price_kes),
            in_stock=product.in_stock and product.status == "publish", created_at=saved.created_at,
        )
        for saved, product in rows
    ]


@router.put("/cakes/{slug}", response_model=SavedCakeRead)
async def save_cake(slug: str, response: Response, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    product = await db.scalar(select(Product).where(Product.slug == slug, Product.status == "publish"))
    if not product:
        raise HTTPException(status_code=404, detail="Cake not found")
    saved = await db.scalar(select(SavedCake).where(
        SavedCake.customer_id == customer.id, SavedCake.product_id == product.id,
    ))
    if not saved:
        if (await db.scalar(select(func.count(SavedCake.id)).where(SavedCake.customer_id == customer.id))) >= 100:
            raise HTTPException(status_code=409, detail="Saved cake limit reached")
        saved = SavedCake(customer_id=customer.id, product_id=product.id)
        db.add(saved)
        await db.commit()
        await db.refresh(saved)
        response.status_code = 201
    return SavedCakeRead(
        id=saved.id, product_id=product.id, slug=product.slug, name=product.name,
        image_url=product.image_url, price_kes=float(product.price_kes),
        in_stock=product.in_stock, created_at=saved.created_at,
    )


@router.delete("/cakes/{slug}", status_code=204)
async def remove_saved_cake(slug: str, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    saved = await db.scalar(
        select(SavedCake).join(Product, Product.id == SavedCake.product_id)
        .where(SavedCake.customer_id == customer.id, Product.slug == slug)
    )
    if saved:
        await db.delete(saved)
        await db.commit()


@router.get("/messages", response_model=list[SavedMessageRead])
async def list_saved_messages(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    return list((await db.scalars(
        select(SavedMessage).where(SavedMessage.customer_id == customer.id).order_by(SavedMessage.created_at.desc())
    )).all())


@router.post("/messages", response_model=SavedMessageRead, status_code=201)
async def create_saved_message(payload: SavedMessageInput, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    if (await db.scalar(select(func.count(SavedMessage.id)).where(SavedMessage.customer_id == customer.id))) >= 30:
        raise HTTPException(status_code=409, detail="Saved message limit reached")
    saved = SavedMessage(
        customer_id=customer.id, label=payload.label.strip(), message=payload.message.strip(),
    )
    db.add(saved)
    await db.commit()
    await db.refresh(saved)
    return saved


@router.delete("/messages/{message_id}", status_code=204)
async def delete_saved_message(message_id: UUID, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    saved = await db.scalar(select(SavedMessage).where(
        SavedMessage.id == message_id, SavedMessage.customer_id == customer.id,
    ))
    if not saved:
        raise HTTPException(status_code=404, detail="Saved message not found")
    await db.delete(saved)
    await db.commit()
