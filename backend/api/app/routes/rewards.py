from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import current_customer
from ..database import session
from ..models import (
    Customer, LoyaltyLedgerEntry, Order, Referral, ReferralCode, WalletLedgerEntry,
)
from ..services.loyalty import (
    TIER_BENEFITS, loyalty_account, redeem_to_wallet, referral_code, wallet_account,
)

router = APIRouter(prefix="/v1/account/rewards", tags=["rewards"])


class RedeemInput(BaseModel):
    points: int = Field(ge=500, le=100000)


class ReferralInput(BaseModel):
    code: str = Field(min_length=5, max_length=20)


@router.get("")
async def overview(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    loyalty = await loyalty_account(db, customer.id)
    wallet = await wallet_account(db, customer.id)
    code = await referral_code(db, customer)
    referrals = await db.scalar(select(func.count()).select_from(Referral).where(
        Referral.referrer_id == customer.id, Referral.state == "completed",
    ))
    next_tiers = {"silver": ("gold", 25000), "gold": ("diamond", 75000), "diamond": ("platinum", 150000)}
    next_tier = next_tiers.get(loyalty.tier)
    await db.commit()
    return {
        "points_balance": loyalty.points_balance, "lifetime_points": loyalty.lifetime_points,
        "lifetime_spend": f"{loyalty.lifetime_spend:.2f}", "tier": loyalty.tier,
        "benefits": TIER_BENEFITS[loyalty.tier],
        "next_tier": ({"name": next_tier[0], "spend_required": f"{max(0, next_tier[1] - loyalty.lifetime_spend):.2f}"} if next_tier else None),
        "wallet": {"balance": f"{wallet.balance:.2f}", "currency": wallet.currency},
        "referral": {"code": code.code, "completed": referrals, "reward_points": 500},
    }


@router.get("/activity")
async def activity(
    limit: int = Query(default=30, ge=1, le=100),
    customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session),
):
    points = (await db.scalars(select(LoyaltyLedgerEntry).where(
        LoyaltyLedgerEntry.customer_id == customer.id,
    ).order_by(LoyaltyLedgerEntry.created_at.desc()).limit(limit))).all()
    wallet = (await db.scalars(select(WalletLedgerEntry).where(
        WalletLedgerEntry.customer_id == customer.id,
    ).order_by(WalletLedgerEntry.created_at.desc()).limit(limit))).all()
    return {
        "points": [{"id": str(item.id), "points": item.points, "description": item.description, "balance_after": item.balance_after, "created_at": item.created_at} for item in points],
        "wallet": [{"id": str(item.id), "amount": f"{item.amount:.2f}", "description": item.description, "balance_after": f"{item.balance_after:.2f}", "created_at": item.created_at} for item in wallet],
    }


@router.post("/redeem")
async def redeem(
    payload: RedeemInput,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=16, max_length=100),
    customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session),
):
    try:
        amount = await redeem_to_wallet(db, customer.id, payload.points, idempotency_key)
        await db.commit()
        return {"redeemed_points": payload.points, "wallet_credit": f"{amount:.2f}", "currency": "KES"}
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/referrals/apply", status_code=201)
async def apply_referral(payload: ReferralInput, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    normalized = payload.code.strip().upper()
    code = await db.scalar(select(ReferralCode).where(ReferralCode.code == normalized))
    if not code:
        raise HTTPException(status_code=404, detail="Referral code not found")
    if code.customer_id == customer.id:
        raise HTTPException(status_code=409, detail="You cannot use your own referral code")
    if await db.scalar(select(Referral.id).where(Referral.referred_id == customer.id)):
        raise HTTPException(status_code=409, detail="A referral is already attached to this account")
    if await db.scalar(select(Order.id).where(Order.customer_id == customer.id).limit(1)):
        raise HTTPException(status_code=409, detail="Referral codes must be applied before your first order")
    db.add(Referral(referrer_id=code.customer_id, referred_id=customer.id, code=code.code))
    await db.commit()
    return {"applied": True, "message": "Your welcome reward unlocks after your first delivered order."}
