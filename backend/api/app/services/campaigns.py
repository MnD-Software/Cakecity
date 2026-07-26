from datetime import datetime, timezone
from sqlalchemy import func, select
from ..models import CampaignDelivery, MarketingCampaign, Notification, OutboxEvent
from .segments import customer_ids_for_segment


async def claim_due_campaign(db) -> MarketingCampaign | None:
    now = datetime.now(timezone.utc)
    campaign = await db.scalar(select(MarketingCampaign).where(
        MarketingCampaign.state == "scheduled",
        MarketingCampaign.scheduled_at <= now,
    ).order_by(MarketingCampaign.scheduled_at).with_for_update(skip_locked=True).limit(1))
    if not campaign:
        return None
    campaign.state = "launching"
    campaign.launched_at = now
    await db.commit()
    return campaign


async def launch_campaign(db, campaign_id) -> int:
    campaign = await db.get(MarketingCampaign, campaign_id, with_for_update=True)
    if not campaign or campaign.state not in ("launching", "running"):
        return 0
    campaign.state = "running"
    customer_ids = await customer_ids_for_segment(db, campaign.audience_segment)
    created = 0
    for customer_id in customer_ids:
        existing = await db.scalar(select(CampaignDelivery.id).where(
            CampaignDelivery.campaign_id == campaign.id,
            CampaignDelivery.customer_id == customer_id,
        ))
        if existing:
            continue
        delivery = CampaignDelivery(campaign_id=campaign.id, customer_id=customer_id)
        db.add(delivery)
        await db.flush()
        notification = Notification(
            customer_id=customer_id, kind="campaign", title=campaign.subject, body=campaign.message,
            data={
                "url": campaign.call_to_action_url, "channel": campaign.channel,
                "campaign_id": str(campaign.id), "campaign_delivery_id": str(delivery.id),
            },
        )
        db.add(notification)
        await db.flush()
        delivery.notification_id = notification.id
        db.add(OutboxEvent(
            aggregate_type="notification", aggregate_id=notification.id, topic="notification.dispatch",
            payload={"notification_id": str(notification.id)},
        ))
        created += 1
    if not customer_ids:
        campaign.state = "completed"
        campaign.completed_at = datetime.now(timezone.utc)
    await db.commit()
    return created


async def complete_campaign_delivery(db, notification: Notification) -> None:
    delivery_id = notification.data.get("campaign_delivery_id")
    if not delivery_id:
        return
    from uuid import UUID
    delivery = await db.get(CampaignDelivery, UUID(delivery_id))
    if not delivery or delivery.delivered_at:
        return
    delivery.state = "dispatched"
    delivery.delivered_at = datetime.now(timezone.utc)
    pending = await db.scalar(select(func.count(CampaignDelivery.id)).where(
        CampaignDelivery.campaign_id == delivery.campaign_id,
        CampaignDelivery.delivered_at.is_(None),
    ))
    if pending == 0:
        campaign = await db.get(MarketingCampaign, delivery.campaign_id)
        campaign.state = "completed"
        campaign.completed_at = datetime.now(timezone.utc)
