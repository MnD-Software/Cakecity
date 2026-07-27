from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import current_customer
from ..database import session
from ..models import Address, Customer

router = APIRouter(prefix="/v1/account/addresses", tags=["account"])


class AddressInput(BaseModel):
    label: str = Field(default="Home", min_length=1, max_length=80)
    recipient_name: str = Field(min_length=2, max_length=240)
    phone: str = Field(min_length=9, max_length=32)
    line1: str = Field(min_length=3, max_length=260)
    line2: str | None = Field(default=None, max_length=260)
    area: str = Field(min_length=2, max_length=160)
    city: str = Field(default="Nairobi", min_length=2, max_length=120)
    delivery_notes: str | None = Field(default=None, max_length=500)
    is_default: bool = False


class AddressRead(AddressInput):
    id: UUID


@router.get("", response_model=list[AddressRead])
async def list_addresses(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    return list((await db.scalars(
        select(Address).where(Address.customer_id == customer.id).order_by(Address.is_default.desc(), Address.created_at.desc())
    )).all())


@router.post("", response_model=AddressRead, status_code=201)
async def create_address(payload: AddressInput, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    count = await db.scalar(select(func.count(Address.id)).where(Address.customer_id == customer.id))
    if (count or 0) >= 20:
        raise HTTPException(status_code=409, detail="Saved address limit reached")
    make_default = payload.is_default or (count or 0) == 0
    if make_default:
        await db.execute(update(Address).where(Address.customer_id == customer.id).values(is_default=False))
    address = Address(customer_id=customer.id, **payload.model_dump(exclude={"is_default"}), is_default=make_default)
    db.add(address)
    await db.commit()
    await db.refresh(address)
    return address


@router.put("/{address_id}", response_model=AddressRead)
async def update_address(
    address_id: UUID, payload: AddressInput,
    customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session),
):
    address = await db.scalar(select(Address).where(Address.id == address_id, Address.customer_id == customer.id))
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    if payload.is_default:
        await db.execute(update(Address).where(Address.customer_id == customer.id).values(is_default=False))
    for field, value in payload.model_dump(exclude={"is_default"}).items():
        setattr(address, field, value)
    address.is_default = payload.is_default or address.is_default
    await db.commit()
    await db.refresh(address)
    return address


@router.put("/{address_id}/default", response_model=AddressRead)
async def make_default_address(
    address_id: UUID, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session),
):
    address = await db.scalar(select(Address).where(Address.id == address_id, Address.customer_id == customer.id))
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    await db.execute(update(Address).where(Address.customer_id == customer.id).values(is_default=False))
    address.is_default = True
    await db.commit()
    await db.refresh(address)
    return address


@router.delete("/{address_id}", status_code=204)
async def delete_address(address_id: UUID, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    address = await db.scalar(select(Address).where(Address.id == address_id, Address.customer_id == customer.id))
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    was_default = address.is_default
    await db.delete(address)
    await db.flush()
    if was_default:
        replacement = await db.scalar(
            select(Address).where(Address.customer_id == customer.id).order_by(Address.created_at.desc()).limit(1)
        )
        if replacement:
            replacement.is_default = True
    await db.commit()
