from datetime import date
from sqlalchemy import select
from ..models import CelebrationMoment, ReminderDelivery
from .loyalty import credit_points, notify


def anniversary_in_year(original: date, year: int) -> date:
    try:
        return original.replace(year=year)
    except ValueError:
        return date(year, 2, 28)


async def process_due_reminders(db, today: date) -> int:
    moments = (await db.scalars(select(CelebrationMoment).where(
        CelebrationMoment.is_active.is_(True),
    ).order_by(CelebrationMoment.id))).all()
    created = 0
    for moment in moments:
        event = anniversary_in_year(moment.event_date, today.year)
        if event < today:
            event = anniversary_in_year(moment.event_date, today.year + 1)
        days_before = (event - today).days
        if days_before not in moment.reminder_days:
            continue
        exists = await db.scalar(select(ReminderDelivery.id).where(
            ReminderDelivery.moment_id == moment.id,
            ReminderDelivery.event_year == event.year,
            ReminderDelivery.days_before == days_before,
        ))
        if exists:
            continue
        when = "today" if days_before == 0 else f"in {days_before} day{'s' if days_before != 1 else ''}"
        previous_order_url = f"/account/moments?moment={moment.id}"
        notification = await notify(
            db, moment.customer_id, "moment_reminder",
            f"{moment.name}'s {moment.occasion} is {when}",
            "Reorder a cake from your memory timeline or create a new design.",
            {"url": previous_order_url, "moment_id": str(moment.id), "occasion": moment.occasion},
        )
        db.add(ReminderDelivery(
            moment_id=moment.id, event_year=event.year, days_before=days_before,
            notification_id=notification.id,
        ))
        if days_before == 0 and moment.occasion == "birthday" and moment.relationship.strip().lower() == "self":
            await credit_points(
                db, moment.customer_id, 250, f"birthday:{moment.id}:{event.year}",
                "Annual Cake City birthday reward",
            )
        created += 1
    return created
