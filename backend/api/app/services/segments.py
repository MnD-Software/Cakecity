from datetime import date, datetime, timedelta, timezone
from sqlalchemy import func, select
from ..models import CelebrationMoment, Customer, LoyaltyAccount, Order

SEGMENTS = ("all", "new", "repeat", "vip", "lapsed", "birthday_upcoming")


async def customer_ids_for_segment(db, segment: str, now: datetime | None = None) -> list:
    if segment not in SEGMENTS:
        raise ValueError("Unknown customer segment")
    now = now or datetime.now(timezone.utc)
    base = select(Customer.id).where(Customer.is_active.is_(True), Customer.role == "customer")
    if segment == "new":
        base = base.where(Customer.created_at >= now - timedelta(days=30))
    elif segment == "vip":
        base = base.join(LoyaltyAccount, LoyaltyAccount.customer_id == Customer.id).where(
            LoyaltyAccount.tier.in_(("diamond", "platinum")),
        )
    elif segment == "repeat":
        repeats = select(Order.customer_id).where(
            Order.customer_id.is_not(None), Order.state == "delivered",
        ).group_by(Order.customer_id).having(func.count(Order.id) >= 2)
        base = base.where(Customer.id.in_(repeats))
    elif segment == "lapsed":
        last_order = select(Order.customer_id).where(
            Order.customer_id.is_not(None),
        ).group_by(Order.customer_id).having(func.max(Order.created_at) < now - timedelta(days=90))
        base = base.where(Customer.id.in_(last_order))
    elif segment == "birthday_upcoming":
        moments = (await db.execute(select(
            CelebrationMoment.customer_id, CelebrationMoment.event_date,
        ).where(
            CelebrationMoment.is_active.is_(True),
            CelebrationMoment.occasion == "birthday",
        ))).all()
        upcoming = []
        today = now.date()
        for customer_id, event_date in moments:
            try:
                event = event_date.replace(year=today.year)
            except ValueError:
                event = date(today.year, 2, 28)
            if event < today:
                event = event.replace(year=today.year + 1)
            if 0 <= (event - today).days <= 30:
                upcoming.append(customer_id)
        return list(dict.fromkeys(upcoming))
    return list((await db.scalars(base.order_by(Customer.id))).all())
