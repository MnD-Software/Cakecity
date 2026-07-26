import secrets
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from ..models import (
    Customer, LoyaltyAccount, LoyaltyLedgerEntry, Notification, Order, OutboxEvent,
    Referral, ReferralCode, WalletAccount, WalletLedgerEntry,
)

TIER_THRESHOLDS = (("platinum", Decimal("150000")), ("diamond", Decimal("75000")), ("gold", Decimal("25000")), ("silver", Decimal("0")))
TIER_BENEFITS = {
    "silver": ["Earn 1 point per KES 100", "Member-only offers"],
    "gold": ["Earn 1 point per KES 100", "Birthday reward", "Early seasonal access"],
    "diamond": ["All Gold benefits", "Priority production windows", "Exclusive tastings"],
    "platinum": ["All Diamond benefits", "Concierge ordering", "Complimentary Nairobi delivery"],
}


def tier_for(spend: Decimal) -> str:
    return next(tier for tier, threshold in TIER_THRESHOLDS if spend >= threshold)


async def loyalty_account(db, customer_id, lock: bool = False) -> LoyaltyAccount:
    statement = select(LoyaltyAccount).where(LoyaltyAccount.customer_id == customer_id)
    account = await db.scalar(statement.with_for_update() if lock else statement)
    if not account:
        account = LoyaltyAccount(customer_id=customer_id)
        db.add(account)
        await db.flush()
    return account


async def wallet_account(db, customer_id, lock: bool = False) -> WalletAccount:
    statement = select(WalletAccount).where(WalletAccount.customer_id == customer_id)
    account = await db.scalar(statement.with_for_update() if lock else statement)
    if not account:
        account = WalletAccount(customer_id=customer_id)
        db.add(account)
        await db.flush()
    return account


async def notify(db, customer_id, kind: str, title: str, body: str, data: dict | None = None) -> Notification:
    notification = Notification(customer_id=customer_id, kind=kind, title=title, body=body, data=data or {})
    db.add(notification)
    await db.flush()
    db.add(OutboxEvent(
        aggregate_type="notification", aggregate_id=notification.id, topic="notification.dispatch",
        payload={"notification_id": str(notification.id)},
    ))
    return notification


async def credit_points(db, customer_id, points: int, source_key: str, description: str, order_id=None) -> bool:
    if points <= 0 or await db.scalar(select(LoyaltyLedgerEntry.id).where(LoyaltyLedgerEntry.source_key == source_key)):
        return False
    account = await loyalty_account(db, customer_id, lock=True)
    account.points_balance += points
    account.lifetime_points += points
    db.add(LoyaltyLedgerEntry(
        customer_id=customer_id, order_id=order_id, entry_type="credit", points=points,
        balance_after=account.points_balance, source_key=source_key, description=description,
    ))
    return True


async def redeem_to_wallet(db, customer_id, points: int, redemption_key: str) -> Decimal:
    if points < 500 or points % 100:
        raise ValueError("Redeem at least 500 points in increments of 100")
    if await db.scalar(select(LoyaltyLedgerEntry.id).where(LoyaltyLedgerEntry.source_key == f"redeem:{redemption_key}")):
        raise ValueError("This redemption has already been processed")
    loyalty = await loyalty_account(db, customer_id, lock=True)
    if loyalty.points_balance < points:
        raise ValueError("Not enough points for this redemption")
    wallet = await wallet_account(db, customer_id, lock=True)
    amount = Decimal(points)
    loyalty.points_balance -= points
    wallet.balance += amount
    db.add(LoyaltyLedgerEntry(
        customer_id=customer_id, entry_type="redemption", points=-points,
        balance_after=loyalty.points_balance, source_key=f"redeem:{redemption_key}",
        description=f"Converted {points} points to Cake City credit",
    ))
    db.add(WalletLedgerEntry(
        customer_id=customer_id, entry_type="loyalty_redemption", amount=amount,
        balance_after=wallet.balance, source_key=f"loyalty:{redemption_key}",
        description=f"Store credit from {points} reward points",
    ))
    await notify(db, customer_id, "reward", "Cake City credit added", f"KES {amount:,.0f} is ready in your wallet.")
    return amount


async def referral_code(db, customer: Customer) -> ReferralCode:
    existing = await db.get(ReferralCode, customer.id)
    if existing:
        return existing
    prefix = "".join(character for character in customer.first_name.upper() if character.isalnum())[:6] or "CAKE"
    for _ in range(8):
        code = f"{prefix}{secrets.token_hex(2).upper()}"
        if not await db.scalar(select(ReferralCode.customer_id).where(ReferralCode.code == code)):
            item = ReferralCode(customer_id=customer.id, code=code)
            db.add(item)
            await db.flush()
            return item
    raise RuntimeError("Could not allocate a referral code")


async def settle_order_rewards(db, order: Order) -> None:
    if not order.customer_id:
        return
    points = max(1, int(Decimal(order.total) // Decimal("100")))
    credited = await credit_points(
        db, order.customer_id, points, f"order:{order.id}", f"Points earned on {order.reference}", order.id,
    )
    account = await loyalty_account(db, order.customer_id, lock=True)
    if credited:
        previous_tier = account.tier
        account.lifetime_spend += Decimal(order.total)
        account.tier = tier_for(account.lifetime_spend)
        await notify(db, order.customer_id, "reward", f"+{points} Cake City points", f"Your {order.reference} reward is now available.", {"url": "/account/rewards"})
        if account.tier != previous_tier:
            await notify(db, order.customer_id, "tier_upgrade", f"Welcome to {account.tier.title()}", "Your new Cake City membership benefits are active.", {"url": "/account/rewards"})
    referral = await db.scalar(select(Referral).where(
        Referral.referred_id == order.customer_id, Referral.state == "pending",
    ).with_for_update())
    if referral and credited:
        referral.state, referral.qualifying_order_id = "completed", order.id
        referral.completed_at = datetime.now(timezone.utc)
        code = await db.get(ReferralCode, referral.referrer_id)
        if code:
            code.uses += 1
        await credit_points(db, referral.referrer_id, 500, f"referrer:{referral.id}", "Friend completed their first Cake City order")
        await credit_points(db, referral.referred_id, 250, f"referred:{referral.id}", "Welcome referral reward")
        await notify(db, referral.referrer_id, "referral", "Your friend just celebrated", "500 referral points are now in your account.", {"url": "/account/rewards"})
